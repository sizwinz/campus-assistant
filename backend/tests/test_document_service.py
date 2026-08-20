"""
Tests for document service consistency behavior.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document
from app.services.document_service import DocumentService


@pytest.mark.asyncio
async def test_failed_upload_indexing_does_not_mark_document_indexed(
    db_session: AsyncSession,
) -> None:
    class FailingProcessor:
        async def save_uploaded_file(self, content: bytes, filename: str):
            return "missing.txt", "generated.txt"

        async def process_file(self, file_path: str, metadata=None):
            raise ValueError("cannot parse document")

    class FakeVectorStore:
        async def add_documents(self, chunks):
            return len(chunks)

    service = DocumentService(
        db_session,
        vector_store=FakeVectorStore(),
        document_processor=FailingProcessor(),
    )

    response = await service.upload_document(
        content=b"not empty",
        filename="sample.txt",
        content_type="text/plain",
        category=None,
        description=None,
        auto_index=True,
        admin_username="admin",
    )

    result = await db_session.execute(select(Document).where(Document.id == response.id))
    document = result.scalar_one()

    assert response.is_indexed is False
    assert response.indexing_status == "failed"
    assert document.is_indexed is False
    assert document.indexing_status == "failed"
    assert "cannot parse document" in (document.indexing_error or "")
