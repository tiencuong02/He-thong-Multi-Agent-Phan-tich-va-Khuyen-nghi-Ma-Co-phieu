import os
from typing import List, Dict, Any, Optional
from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from pinecone import Pinecone
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

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

            # Initialize Langchain Vector Store
            self.vector_store = PineconeVectorStore(
                index_name=self.index_name,
                embedding=self.embeddings,
                pinecone_api_key=self.pinecone_api_key
            )
            logger.info("VectorStoreService initialized successfully.")
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

        try:
            # filter_metadata example: {"ticker": "FPT"}
            docs = self.vector_store.similarity_search(
                query=query,
                k=k,
                filter=filter_metadata
            )
            return docs
        except Exception as e:
            logger.error(f"Error querying Pinecone: {e}")
            return []

    def delete_by_metadata(self, filter_metadata: Dict[str, Any]) -> bool:
        """Delete vectors from Pinecone by metadata filter (e.g. source filename)."""
        if self._pinecone_index is None:
            logger.error("Pinecone index not initialized, cannot delete vectors.")
            return False

        try:
            self._pinecone_index.delete(filter=filter_metadata)
            logger.info(f"Deleted vectors from Pinecone with filter: {filter_metadata}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete vectors from Pinecone: {e}")
            return False
