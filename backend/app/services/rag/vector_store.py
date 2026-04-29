import logging
from typing import List, Dict, Any, Optional, Tuple

from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from pinecone import Pinecone
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from app.core.config import settings

logger = logging.getLogger(__name__)

# Namespaces — mỗi pipeline có namespace riêng để bảo mật dữ liệu
NAMESPACE_ADVISORY  = "internal-advisory"   # chỉ advisory pipeline dùng
NAMESPACE_KNOWLEDGE = "public-knowledge"    # knowledge pipeline
NAMESPACE_FAQ       = "faq-complaint"       # complaint pipeline
NAMESPACE_LEGACY    = "stock-rag-prod"      # namespace cũ, giữ tương thích

# Ngưỡng similarity cho multilingual-e5-small (384-dim)
# e5-small sinh ra scores thấp hơn BGE-M3 (~0.4-0.6 cho match tốt vs 0.7-0.9 BGE)
SIMILARITY_THRESHOLD_ADVISORY  = 0.45
SIMILARITY_THRESHOLD_KNOWLEDGE = 0.40
SIMILARITY_THRESHOLD_DEFAULT   = 0.35

# Cross-encoder models — thử theo thứ tự: multilingual tốt nhất → fallback English
# BAAI/bge-reranker-v2-m3: cùng họ BGE-M3, multilingual, Vietnamese tốt
# mmarco-mMiniLMv2: multilingual, nhẹ hơn
# ms-marco-MiniLM-L-6-v2: English-only, dự phòng cuối
_CROSS_ENCODER_MODELS = [
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
    "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
    "BAAI/bge-reranker-v2-m3",
]


class VectorStoreService:
    def __init__(self):
        self.pinecone_api_key = settings.PINECONE_API_KEY
        self.index_name = settings.PINECONE_INDEX_NAME

        self.vector_store = None
        self.embeddings = None
        self._pinecone_index = None
        self._ns_stores: Dict[str, PineconeVectorStore] = {}
        self._cross_encoder: Optional[CrossEncoder] = None

        if not self.pinecone_api_key:
            logger.warning("Pinecone API Key not found. RAG functionality will be limited.")
            return

        self._init_embeddings()
        self._init_pinecone()
        self._init_cross_encoder()

    def _init_embeddings(self):
        try:
            # Model siêu nhẹ — 384 dims, multilingual, CPU-friendly
            from langchain_huggingface import HuggingFaceEmbeddings
            self.embeddings = HuggingFaceEmbeddings(
                model_name="paraphrase-multilingual-MiniLM-L12-v2",
                model_kwargs={"device": "cpu"},
                # CHÚ Ý: KHÔNG đặt show_progress_bar ở đây — langchain_huggingface
                # đã truyền nó nội bộ, đặt lại sẽ gây lỗi "multiple values"
                encode_kwargs={"normalize_embeddings": True, "batch_size": 256},
            )
            logger.info("Embeddings: paraphrase-multilingual-MiniLM-L12-v2 initialized (384 dims).")
        except Exception as e:
            logger.error(f"Failed to initialize HuggingFace Embeddings: {e}")
            self.embeddings = None

    def _init_pinecone(self):
        try:
            pc = Pinecone(api_key=self.pinecone_api_key)
            existing = [idx.name for idx in pc.list_indexes()]

            if self.index_name not in existing:
                logger.warning(
                    f"Pinecone index '{self.index_name}' not found. "
                    "Create it with dimension=384, metric=cosine."
                )
                return

            self._pinecone_index = pc.Index(self.index_name)

            # Primary store (default namespace — backward compat)
            self.vector_store = PineconeVectorStore(
                index_name=self.index_name,
                embedding=self.embeddings,
                pinecone_api_key=self.pinecone_api_key,
            )

            # Per-namespace stores
            all_namespaces = [
                NAMESPACE_ADVISORY,
                NAMESPACE_KNOWLEDGE,
                NAMESPACE_FAQ,
                NAMESPACE_LEGACY,
                "",  # __default__ — backward compat với docs cũ chưa migrate
            ]
            for ns in all_namespaces:
                self._ns_stores[ns] = PineconeVectorStore(
                    index_name=self.index_name,
                    embedding=self.embeddings,
                    pinecone_api_key=self.pinecone_api_key,
                    namespace=ns if ns else None,
                )

            logger.info(f"Pinecone initialized. Index: '{self.index_name}'. Namespaces: {all_namespaces}")
        except Exception as e:
            logger.error(f"Pinecone init failed: {e}")
            self.vector_store = None
            self._pinecone_index = None

    def _init_cross_encoder(self):
        for model_name in _CROSS_ENCODER_MODELS:
            try:
                self._cross_encoder = CrossEncoder(model_name)
                logger.info(f"Cross-encoder initialized: {model_name}")
                return
            except Exception as e:
                logger.warning(f"Cross-encoder '{model_name}' failed: {e}")
        logger.error("All cross-encoder models failed — reranking disabled.")
        self._cross_encoder = None

    # ─── Upsert ──────────────────────────────────────────────────────────────

    def upsert_chunks(
        self,
        chunks_with_metadata: List[Dict[str, Any]],
        namespace: str = NAMESPACE_ADVISORY,
    ) -> bool:
        """Lưu chunks vào namespace chỉ định.
        Advisory data → NAMESPACE_ADVISORY (mặc định, bảo mật).
        Public data   → NAMESPACE_KNOWLEDGE.
        """
        if self.vector_store is None:
            logger.error("Vector store not initialized.")
            return False

        store = self._ns_stores.get(namespace, self.vector_store)
        texts = [c["text"] for c in chunks_with_metadata]
        metas = [c["metadata"] for c in chunks_with_metadata]

        try:
            store.add_texts(texts=texts, metadatas=metas)
            logger.info(f"Upserted {len(texts)} chunks to namespace '{namespace}'.")
            return True
        except Exception as e:
            logger.error(f"Upsert to '{namespace}' failed: {e}")
            return False

    # ─── Search ──────────────────────────────────────────────────────────────

    def search_similar_documents(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
        namespaces: Optional[List[str]] = None,
        similarity_threshold: float = SIMILARITY_THRESHOLD_DEFAULT,
        use_reranking: bool = True,
    ) -> List[Any]:
        """
        Hybrid Search: Dense (BGE-M3) + BM25 Sparse → RRF fusion → Cross-encoder Rerank.
        Loại bỏ doc có score dưới similarity_threshold.
        """
        if self.vector_store is None:
            return []

        target_namespaces = namespaces or [NAMESPACE_ADVISORY, NAMESPACE_LEGACY, ""]
        # Có reranking: 2x candidates đủ với MiniLM reranker nhẹ
        # Không reranking: RRF đủ tốt với 1.5x
        fetch_k = max(k * 2, 10) if use_reranking else max(k + 5, 8)

        # --- Dense retrieval (với score) ---
        dense_docs_scored: List[Tuple[Any, float]] = []
        seen_keys: set = set()

        for ns in target_namespaces:
            store = self._ns_stores.get(ns)
            if store is None:
                continue
            try:
                results = store.similarity_search_with_score(
                    query=query,
                    k=fetch_k,
                    filter=filter_metadata or None,
                )
                for doc, score in results:
                    if len(doc.page_content.strip()) <= 10:
                        continue
                    key = (doc.page_content[:100], doc.metadata.get("page"))
                    if key not in seen_keys:
                        seen_keys.add(key)
                        dense_docs_scored.append((doc, float(score)))
            except Exception as e:
                logger.error(f"Dense search failed (ns='{ns}'): {e}")

        if not dense_docs_scored:
            return []

        # --- Similarity threshold filter ---
        filtered = [(doc, sc) for doc, sc in dense_docs_scored if sc >= similarity_threshold]
        if not filtered:
            logger.info(
                f"All {len(dense_docs_scored)} docs below threshold {similarity_threshold}. "
                "No results returned."
            )
            return []

        # --- BM25 Sparse re-scoring ---
        texts = [doc.page_content for doc, _ in filtered]
        bm25_scores = self._bm25_score(query, texts)

        # --- Reciprocal Rank Fusion (RRF) ---
        rrf_scores = self._rrf_fusion(
            dense_scores=[sc for _, sc in filtered],
            sparse_scores=bm25_scores,
        )

        # Sắp xếp theo RRF score
        candidates = sorted(
            zip([doc for doc, _ in filtered], rrf_scores),
            key=lambda x: x[1],
            reverse=True,
        )[:fetch_k]

        # --- Cross-encoder Reranking ---
        if use_reranking and self._cross_encoder is not None and len(candidates) > 1:
            docs_only = [doc for doc, _ in candidates]
            reranked = self._rerank(query, docs_only)
            final = reranked[:k]
        else:
            final = [doc for doc, _ in candidates[:k]]

        # Attach similarity score vào metadata để CRAG và downstream dùng
        scores_map = {id(doc): sc for doc, sc in filtered}
        for doc in final:
            doc.metadata["_similarity_score"] = scores_map.get(id(doc), similarity_threshold)

        logger.info(
            f"VectorStore: {len(dense_docs_scored)} dense → "
            f"{len(filtered)} passed threshold → "
            f"{len(final)} after rerank."
        )
        return final

    def search_advisory(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        """Advisory search — chỉ tìm trong namespace advisory (không legacy)."""
        return self.search_similar_documents(
            query=query,
            k=k,
            filter_metadata=filter_metadata,
            namespaces=[NAMESPACE_ADVISORY],
            similarity_threshold=SIMILARITY_THRESHOLD_ADVISORY,
            use_reranking=True,
        )

    def search_knowledge(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Any]:
        """Knowledge search — chỉ tìm trong namespace knowledge (không legacy)."""
        return self.search_similar_documents(
            query=query,
            k=k,
            filter_metadata=filter_metadata,
            namespaces=[NAMESPACE_KNOWLEDGE],
            similarity_threshold=SIMILARITY_THRESHOLD_KNOWLEDGE,
            use_reranking=False,
        )

    def search_faq(
        self,
        query: str,
        k: int = 3,
    ) -> List[Any]:
        """FAQ search cho complaint pipeline — threshold cao hơn."""
        return self.search_similar_documents(
            query=query,
            k=k,
            namespaces=[NAMESPACE_FAQ],
            similarity_threshold=0.72,
            use_reranking=False,
        )

    # ─── BM25 Sparse Scoring ─────────────────────────────────────────────────

    @staticmethod
    def _bm25_score(query: str, texts: List[str]) -> List[float]:
        """Tính BM25 score cho danh sách texts so với query."""
        if not texts:
            return []
        tokenized_corpus = [t.lower().split() for t in texts]
        tokenized_query = query.lower().split()
        try:
            bm25 = BM25Okapi(tokenized_corpus)
            scores = bm25.get_scores(tokenized_query).tolist()
            # Normalize về [0, 1]
            max_s = max(scores) if max(scores) > 0 else 1.0
            return [s / max_s for s in scores]
        except Exception as e:
            logger.warning(f"BM25 scoring failed: {e}")
            return [0.0] * len(texts)

    # ─── RRF Fusion ──────────────────────────────────────────────────────────

    @staticmethod
    def _rrf_fusion(
        dense_scores: List[float],
        sparse_scores: List[float],
        k: int = 60,
        dense_weight: float = 0.7,
        sparse_weight: float = 0.3,
    ) -> List[float]:
        """
        Reciprocal Rank Fusion — gộp dense và sparse scores.
        dense_weight cao hơn vì BGE-M3 đã rất tốt với ngữ nghĩa.
        """
        n = len(dense_scores)
        dense_ranks  = _rank_list(dense_scores)
        sparse_ranks = _rank_list(sparse_scores)

        fused = []
        for i in range(n):
            rrf = (
                dense_weight  * (1.0 / (k + dense_ranks[i]))
                + sparse_weight * (1.0 / (k + sparse_ranks[i]))
            )
            fused.append(rrf)
        return fused

    # ─── Cross-encoder Reranking ──────────────────────────────────────────────

    def _rerank(self, query: str, docs: List[Any]) -> List[Any]:
        """Cross-encoder rerank: chấm điểm từng cặp (query, doc) chính xác hơn."""
        try:
            pairs = [(query, doc.page_content) for doc in docs]
            scores = self._cross_encoder.predict(pairs)
            ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
            return [doc for doc, _ in ranked]
        except Exception as e:
            logger.warning(f"Reranking failed, using original order: {e}")
            return docs

    # ─── Delete ──────────────────────────────────────────────────────────────

    def delete_by_metadata(
        self,
        filter_metadata: Dict[str, Any],
        namespaces: Optional[List[str]] = None,
    ) -> bool:
        if self._pinecone_index is None:
            logger.error("Pinecone index not initialized.")
            return False

        target = namespaces or [NAMESPACE_ADVISORY, NAMESPACE_LEGACY, ""]
        success = True
        for ns in target:
            try:
                kwargs: Dict[str, Any] = {"filter": filter_metadata}
                if ns:
                    kwargs["namespace"] = ns
                self._pinecone_index.delete(**kwargs)
                logger.info(f"Deleted vectors in ns='{ns}' filter={filter_metadata}")
            except Exception as e:
                err_str = str(e)
                if "Namespace not found" in err_str or "404" in err_str:
                    # Namespace or document does not exist — treat as already deleted
                    logger.debug(f"Namespace not found, skipping ns='{ns}'")
                else:
                    logger.warning(f"Delete failed in ns='{ns}': {e}")
                    success = False
        return success


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _rank_list(scores: List[float]) -> List[int]:
    """Trả về rank (1-based) cho mỗi phần tử, score cao → rank thấp (rank 1 = tốt nhất)."""
    order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    ranks = [0] * len(scores)
    for rank, idx in enumerate(order, start=1):
        ranks[idx] = rank
    return ranks
