"""
Document Ingestion Service.
Handles PDF, DOCX, and TXT file processing and indexing into vector database.
"""

import os
import uuid
from typing import List, Optional, Dict, Any
from pathlib import Path
import asyncio

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
)
from langchain_core.documents import Document as LangchainDocument
from loguru import logger

from app.core.config import Settings, get_settings

settings = get_settings()


class DocumentProcessor:
    """
    Processes and chunks documents for vector storage.
    Supports: PDF, DOCX, TXT files.
    """

    def __init__(self, settings_obj: Settings | None = None, documents_dir: Path | None = None):
        self.settings = settings_obj or settings
        self.documents_dir = documents_dir or Path("./documents")
        self.documents_dir.mkdir(exist_ok=True)

        # Text splitter for chunking
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        # Supported file types
        self.supported_types = {
            ".pdf": self._load_pdf,
            ".docx": self._load_docx,
            ".doc": self._load_docx,
            ".txt": self._load_txt,
        }

    async def save_uploaded_file(
        self, file_content: bytes, filename: str
    ) -> tuple[str, str]:
        """
        Save uploaded file to documents directory.
        Returns: (saved_path, unique_filename)
        """
        # Generate unique filename
        file_ext = Path(filename).suffix.lower()
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = self.documents_dir / unique_filename

        # Save file
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None, lambda: file_path.write_bytes(file_content)
        )

        logger.info(f"Saved file: {filename} -> {unique_filename}")
        return str(file_path), unique_filename

    async def process_file(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[LangchainDocument]:
        """
        Process a file and return chunked documents.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        file_ext = path.suffix.lower()
        if file_ext not in self.supported_types:
            raise ValueError(f"Unsupported file type: {file_ext}")

        # Load document
        loader_func = self.supported_types[file_ext]
        documents = await loader_func(file_path)

        # Add metadata
        base_metadata = metadata or {}
        base_metadata["source_file"] = path.name
        base_metadata["file_type"] = file_ext

        for doc in documents:
            doc.metadata.update(base_metadata)

        # Split into chunks
        chunks = self.text_splitter.split_documents(documents)
        logger.info(f"Processed {path.name}: {len(chunks)} chunks")

        return chunks

    async def _load_pdf(self, file_path: str) -> List[LangchainDocument]:
        """Load PDF file."""
        loop = asyncio.get_event_loop()
        loader = PyPDFLoader(file_path)
        return await loop.run_in_executor(None, loader.load)

    async def _load_docx(self, file_path: str) -> List[LangchainDocument]:
        """Load DOCX file."""
        loop = asyncio.get_event_loop()
        loader = Docx2txtLoader(file_path)
        return await loop.run_in_executor(None, loader.load)

    async def _load_txt(self, file_path: str) -> List[LangchainDocument]:
        """Load TXT file."""
        loop = asyncio.get_event_loop()
        loader = TextLoader(file_path, encoding="utf-8")
        return await loop.run_in_executor(None, loader.load)

    async def process_text_content(
        self,
        content: str,
        source_name: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[LangchainDocument]:
        """
        Process raw text content (e.g., FAQs, manual entries).
        """
        base_metadata = metadata or {}
        base_metadata["source"] = source_name
        base_metadata["type"] = "text"

        doc = LangchainDocument(page_content=content, metadata=base_metadata)
        chunks = self.text_splitter.split_documents([doc])

        logger.info(f"Processed text content '{source_name}': {len(chunks)} chunks")
        return chunks

    async def process_faq(
        self,
        question: str,
        answer: str,
        category: Optional[str] = None,
        faq_id: Optional[int] = None,
    ) -> List[LangchainDocument]:
        """
        Process FAQ entry for vector storage.
        Combines question and answer for better retrieval.
        """
        content = f"Question: {question}\n\nAnswer: {answer}"

        metadata = {
            "type": "faq",
            "category": category or "general",
            "question": question,
        }
        if faq_id:
            metadata["faq_id"] = faq_id

        doc = LangchainDocument(page_content=content, metadata=metadata)

        # FAQs are usually short, so we might not need to split
        if len(content) > 1500:
            return self.text_splitter.split_documents([doc])
        return [doc]

    def delete_file(self, file_path: str) -> bool:
        """Delete a document file."""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info(f"Deleted file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False


# Singleton instance
_document_processor: Optional[DocumentProcessor] = None


def get_document_processor() -> DocumentProcessor:
    """Get or create document processor instance."""
    global _document_processor
    if _document_processor is None:
        _document_processor = DocumentProcessor()
    return _document_processor
