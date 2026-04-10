import os
from typing import List, Dict, Any, Optional
from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from pinecone import Pinecone
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# All namespaces to search across (new uploads go to __default__, TCB legacy in stock-rag-prod)
_SEARCH_NAMESPACES = ["", "stock-rag-prod"]  # "" = __default__


class VectorStoreService:
    def __init__(self):
        self.pinecone_api_key = settings.PINECONE_API_KEY
        self.index_name = settings.PINECONE_INDEX_NAME

        if not self.pinecone_api_key:
            logger.warning("Pinecone API Key not found. RAG functionality may be limited.")
            self.vector_store = None
            self.embeddings = None
            self._pinecone_index = None
            return

        try:
            # Initialize FREE local embeddings (384 dimensions)
            self.embeddings = HuggingFaceEmbeddings(
                model_name="paraphrase-multilingual-MiniLM-L12-v2"
            )

            # Initialize Pinecone Client
            pc = Pinecone(api_key=self.pinecone_api_key)

            # Check if index exists
            existing_indexes = [idx.name for idx in pc.list_indexes()]
            if self.index_name not in existing_indexes:
                logger.warning(f"Pinecone index '{self.index_name}' not found. Please create it in the Pinecone console (dimension=384, metric=cosine).")
                self.vector_store = None
                self._pinecone_index = None
                return

            # Keep raw Pinecone index reference for delete operations
            self._pinecone_index = pc.Index(self.index_name)

            # Primary vector store (default namespace)
            self.vector_store = PineconeVectorStore(
                index_name=self.index_name,
                embedding=self.embeddings,
                pinecone_api_key=self.pinecone_api_key
            )

            # Per-namespace stores for multi-namespace search
            self._ns_stores: Dict[str, PineconeVectorStore] = {}
            for ns in _SEARCH_NAMESPACES:
                self._ns_stores[ns] = PineconeVectorStore(
                    index_name=self.index_name,
                    embedding=self.embeddings,
                    pinecone_api_key=self.pinecone_api_key,
                    namespace=ns if ns else None,
                )

            logger.info(f"VectorStoreService initialized. Searching namespaces: {_SEARCH_NAMESPACES}")
        except Exception as e:
            logger.error(f"Failed to initialize VectorStoreService: {e}")
            self.vector_store = None
            self._pinecone_index = None

    def upsert_chunks(self, chunks_with_metadata: List[Dict[str, Any]]) -> bool:
        if self.vector_store is None:
            logger.error("Vector store not initialized.")
            return False

        texts = [chunk["text"] for chunk in chunks_with_metadata]
        metadatas = [chunk["metadata"] for chunk in chunks_with_metadata]

        try:
            self.vector_store.add_texts(texts=texts, metadatas=metadatas)
            logger.info(f"Successfully upserted {len(texts)} chunks to Pinecone.")
            return True
        except Exception as e:
            logger.error(f"Error upserting to Pinecone: {e}")
            return False

    def search_similar_documents(
        self,
        query: str,
        k: int = 4,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        if self.vector_store is None:
            logger.error("Vector store not initialized.")
            return []

        all_docs: List[Any] = []
        seen_ids: set = set()

        # Fetch more candidates per namespace to ensure coverage across multiple
        # documents with the same ticker (e.g. two FPT reports). Old broken chunks
        # (content <= 5 chars) are filtered out, so we need extra headroom.
        fetch_k = max(k * 4, 20)

        for ns, store in self._ns_stores.items():
            try:
                docs = store.similarity_search(
                    query=query,
                    k=fetch_k,
                    filter=filter_metadata if filter_metadata else None,
                )
                for doc in docs:
                    # Skip broken chunks (single punctuation / whitespace)
                    if len(doc.page_content.strip()) <= 5:
                        continue
                    # Deduplicate by content prefix + page
                    doc_key = (doc.page_content[:80], doc.metadata.get("page"))
                    if doc_key not in seen_ids:
                        seen_ids.add(doc_key)
                        all_docs.append(doc)
            except Exception as e:
                logger.error(f"Error querying Pinecone namespace '{ns}': {e}")

        result = all_docs[:k]
        logger.info(f"VectorStore: found {len(result)} valid docs across {len(_SEARCH_NAMESPACES)} namespaces.")
        return result

    def delete_by_metadata(self, filter_metadata: Dict[str, Any]) -> bool:
        """Delete vectors from all namespaces by metadata filter."""
        if self._pinecone_index is None:
            logger.error("Pinecone index not initialized, cannot delete vectors.")
            return False

        success = True
        for ns in _SEARCH_NAMESPACES:
            try:
                kwargs = {"filter": filter_metadata}
                if ns:
                    kwargs["namespace"] = ns
                self._pinecone_index.delete(**kwargs)
                logger.info(f"Deleted vectors in namespace '{ns}' with filter: {filter_metadata}")
            except Exception as e:
                logger.warning(f"Failed to delete in namespace '{ns}': {e}")
                success = False
        return success
