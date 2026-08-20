"""
Vector Database Service.
Uses ChromaDB for storing and retrieving document embeddings.
"""

import asyncio
from typing import List, Optional, Dict, Any
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document as LangchainDocument
from loguru import logger

from app.core.config import Settings, get_settings

settings = get_settings()


class VectorStore:
    """
    Vector database for semantic search over documents.
    Uses ChromaDB with multilingual sentence transformers.
    """

    def __init__(self, settings_obj: Settings | None = None):
        self.settings = settings_obj or settings
        self.persist_directory = Path(self.settings.chroma_persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)

        self.collection_name = "campus_assistant"
        self._embeddings = None
        self._vectorstore = None
        self._client = None

    def _get_embeddings(self) -> HuggingFaceEmbeddings:
        """Get or create embeddings model."""
        if self._embeddings is None:
            logger.info(f"Loading embedding model: {self.settings.embedding_model}")
            self._embeddings = HuggingFaceEmbeddings(
                model_name=self.settings.embedding_model,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        return self._embeddings

    def _get_client(self) -> chromadb.PersistentClient:
        """Get or create ChromaDB client."""
        if self._client is None:
            self._client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
        return self._client

    def _get_vectorstore(self) -> Chroma:
        """Get or create vector store."""
        if self._vectorstore is None:
            # Use the shared client instance to avoid "different settings" conflict
            self._vectorstore = Chroma(
                collection_name=self.collection_name,
                embedding_function=self._get_embeddings(),
                client=self._get_client(),  # Use client instead of persist_directory
            )
        return self._vectorstore

    async def add_documents(
        self,
        documents: List[LangchainDocument],
        batch_size: int = 100,
    ) -> int:
        """
        Add documents to vector store.
        Returns number of documents added.
        """
        if not documents:
            return 0

        loop = asyncio.get_event_loop()
        vectorstore = self._get_vectorstore()

        # Process in batches
        total_added = 0
        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            await loop.run_in_executor(
                None,
                lambda b=batch: vectorstore.add_documents(b),
            )
            total_added += len(batch)
            logger.debug(f"Added batch of {len(batch)} documents")

        logger.info(f"Added {total_added} documents to vector store")
        return total_added

    async def search(
        self,
        query: str,
        k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None,
        score_threshold: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar documents.
        Returns list of documents with scores.
        """
        loop = asyncio.get_event_loop()
        vectorstore = self._get_vectorstore()

        # Perform similarity search with scores
        results = await loop.run_in_executor(
            None,
            lambda: vectorstore.similarity_search_with_relevance_scores(
                query, k=k, filter=filter_dict
            ),
        )

        # Filter by score threshold and format results
        formatted_results = []
        for doc, score in results:
            if score >= score_threshold:
                formatted_results.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": score,
                })

        logger.debug(f"Search for '{query[:50]}...' returned {len(formatted_results)} results")
        return formatted_results

    async def search_with_context(
        self,
        query: str,
        conversation_context: Optional[str] = None,
        k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search with conversation context for better results.
        """
        # Combine query with context for better retrieval
        if conversation_context:
            enhanced_query = f"{conversation_context}\n\nCurrent question: {query}"
        else:
            enhanced_query = query

        return await self.search(enhanced_query, k=k)

    async def delete_by_metadata(
        self,
        filter_dict: Dict[str, Any],
    ) -> bool:
        """
        Delete documents matching metadata filter.
        """
        try:
            client = self._get_client()
            collection = client.get_collection(self.collection_name)

            # Build where clause
            collection.delete(where=filter_dict)
            logger.info(f"Deleted documents with filter: {filter_dict}")
            return True

        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return False

    async def delete_by_source(self, source_file: str) -> bool:
        """Delete all documents from a specific source file."""
        return await self.delete_by_metadata({"source_file": source_file})

    async def delete_faq(self, faq_id: int) -> bool:
        """Delete FAQ documents by ID."""
        return await self.delete_by_metadata({"faq_id": faq_id})

    async def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        try:
            client = self._get_client()
            collection = client.get_collection(self.collection_name)
            count = collection.count()

            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "persist_directory": str(self.persist_directory),
                "embedding_model": self.settings.embedding_model,
            }

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                "total_documents": 0,
                "error": str(e),
            }

    async def reset(self) -> bool:
        """
        Reset vector store (delete all data).
        Use with caution!
        """
        try:
            client = self._get_client()
            client.reset()
            self._vectorstore = None
            logger.warning("Vector store reset completed")
            return True
        except Exception as e:
            logger.error(f"Error resetting vector store: {e}")
            return False


# Singleton instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
