"""Document application service."""

from pathlib import Path
from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document
from app.models.schemas import DocumentUploadResponse
from app.services.document_processor import DocumentProcessor, get_document_processor
from app.services.exceptions import ServiceError
from app.services.vector_store import VectorStore, get_vector_store

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt"}
ALLOWED_CONTENT_TYPES = {
    ".pdf": {"application/pdf", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    },
    ".doc": {"application/msword", "application/octet-stream"},
    ".txt": {"text/plain", "application/octet-stream"},
}
MAX_FILE_SIZE = 10 * 1024 * 1024


class DocumentService:
    """Owns document DB, file storage, parsing, and vector workflows."""

    def __init__(
        self,
        db: AsyncSession,
        vector_store: VectorStore | None = None,
        document_processor: DocumentProcessor | None = None,
    ) -> None:
        self.db = db
        self.vector_store = vector_store or get_vector_store()
        self.document_processor = document_processor or get_document_processor()

    async def list_documents(
        self,
        category: Optional[str],
        indexed_only: bool,
        skip: int,
        limit: int,
    ) -> list[Document]:
        query = select(Document)
        if category:
            query = query.where(Document.category == category)
        if indexed_only:
            query = query.where(Document.is_indexed == True)

        result = await self.db.execute(
            query.order_by(Document.uploaded_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_document(self, doc_id: int) -> Document:
        result = await self.db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            raise ServiceError(404, "Document not found")
        return doc

    async def upload_document(
        self,
        content: bytes,
        filename: str,
        content_type: str | None,
        category: Optional[str],
        description: Optional[str],
        auto_index: bool,
        admin_username: str,
    ) -> DocumentUploadResponse:
        ext = self._validate_upload(filename, content, content_type)

        try:
            file_path, unique_filename = await self.document_processor.save_uploaded_file(
                content, filename
            )
            doc = Document(
                filename=unique_filename,
                original_filename=filename,
                file_type=ext,
                file_path=file_path,
                category=category,
                description=description,
                is_indexed=False,
                indexing_status="pending",
                indexing_error=None,
                chunk_count=0,
                uploaded_by=admin_username,
            )
            self.db.add(doc)
            await self.db.commit()
            await self.db.refresh(doc)
        except Exception as exc:
            await self.db.rollback()
            logger.error(f"Error storing uploaded document: {exc}")
            raise ServiceError(500, "Error uploading document") from exc

        chunk_count = 0
        if auto_index:
            try:
                chunk_count = await self.index_document_record(doc)
            except ServiceError:
                await self.db.refresh(doc)

        message = (
            f"Document uploaded successfully. {chunk_count} chunks indexed."
            if doc.is_indexed
            else f"Document uploaded with indexing status: {doc.indexing_status}."
        )
        return DocumentUploadResponse(
            id=doc.id,
            filename=doc.filename,
            file_type=doc.file_type,
            is_indexed=doc.is_indexed,
            indexing_status=doc.indexing_status,
            indexing_error=doc.indexing_error,
            chunk_count=doc.chunk_count,
            message=message,
        )

    async def index_document(self, doc_id: int) -> dict:
        doc = await self.get_document(doc_id)
        if doc.is_indexed:
            return {
                "message": "Document already indexed",
                "chunk_count": doc.chunk_count,
                "indexing_status": doc.indexing_status,
            }

        chunk_count = await self.index_document_record(doc)
        return {
            "message": "Document indexed successfully",
            "chunk_count": chunk_count,
            "indexing_status": "indexed",
        }

    async def index_document_record(self, doc: Document) -> int:
        try:
            doc.indexing_status = "pending"
            doc.indexing_error = None
            doc.is_indexed = False
            await self.db.commit()

            chunks = await self.document_processor.process_file(
                doc.file_path,
                metadata={
                    "document_id": doc.id,
                    "category": doc.category,
                    "original_filename": doc.original_filename,
                },
            )
            await self.vector_store.add_documents(chunks)

            doc.is_indexed = True
            doc.indexing_status = "indexed"
            doc.indexing_error = None
            doc.chunk_count = len(chunks)
            await self.db.commit()
            await self.db.refresh(doc)
            logger.info(f"Indexed document: {doc.id} with {len(chunks)} chunks")
            return len(chunks)
        except Exception as exc:
            await self.db.rollback()
            doc.indexing_status = "failed"
            doc.indexing_error = str(exc)
            doc.is_indexed = False
            doc.chunk_count = 0
            await self.db.commit()
            logger.error(f"Error indexing document {doc.id}: {exc}")
            raise ServiceError(500, "Error indexing document", {"indexing_error": str(exc)})

    async def delete_document(self, doc_id: int) -> dict:
        doc = await self.get_document(doc_id)
        vector_deleted = False
        file_deleted = False
        errors = []

        try:
            vector_deleted = await self.vector_store.delete_by_source(doc.filename)
            if not vector_deleted:
                errors.append("vector_delete_failed")

            file_deleted = self.document_processor.delete_file(doc.file_path)
            if not file_deleted and Path(doc.file_path).exists():
                errors.append("file_delete_failed")

            if errors:
                detail = {
                    "message": "Document delete incomplete",
                    "vector_deleted": vector_deleted,
                    "file_deleted": file_deleted,
                    "errors": errors,
                }
                raise ServiceError(502, "Document delete incomplete", detail)

            await self.db.delete(doc)
            await self.db.commit()
            logger.info(f"Deleted document: {doc_id}")
            return {
                "message": "Document deleted successfully",
                "vector_deleted": vector_deleted,
                "file_deleted": file_deleted,
            }
        except ServiceError:
            await self.db.rollback()
            raise
        except Exception as exc:
            await self.db.rollback()
            logger.error(f"Error deleting document: {exc}")
            raise ServiceError(500, "Error deleting document") from exc

    async def get_stats(self) -> dict:
        result = await self.db.execute(select(Document))
        documents = result.scalars().all()

        by_type: dict[str, int] = {}
        by_category: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for doc in documents:
            by_type[doc.file_type] = by_type.get(doc.file_type, 0) + 1
            category = doc.category or "uncategorized"
            by_category[category] = by_category.get(category, 0) + 1
            status = doc.indexing_status or ("indexed" if doc.is_indexed else "pending")
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "total_documents": len(documents),
            "indexed_documents": sum(1 for doc in documents if doc.is_indexed),
            "total_chunks": sum(doc.chunk_count for doc in documents),
            "by_file_type": by_type,
            "by_category": by_category,
            "by_indexing_status": by_status,
        }

    def _validate_upload(
        self,
        filename: str,
        content: bytes,
        content_type: str | None,
    ) -> str:
        ext = Path(filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ServiceError(
                400,
                f"File type not allowed. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
            )
        if not content:
            raise ServiceError(400, "Uploaded file is empty")
        if len(content) > MAX_FILE_SIZE:
            raise ServiceError(400, f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)} MB")
        if content_type and content_type not in ALLOWED_CONTENT_TYPES[ext]:
            raise ServiceError(400, f"Content type {content_type} is not valid for {ext} files")
        return ext
