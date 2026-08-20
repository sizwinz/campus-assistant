"""FAQ application service."""

from typing import Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import FAQ
from app.models.schemas import FAQCreate, FAQUpdate
from app.services.document_processor import DocumentProcessor, get_document_processor
from app.services.exceptions import ServiceError
from app.services.vector_store import VectorStore, get_vector_store


class FAQService:
    """Owns FAQ database and vector-store workflows."""

    def __init__(
        self,
        db: AsyncSession,
        vector_store: VectorStore | None = None,
        document_processor: DocumentProcessor | None = None,
    ) -> None:
        self.db = db
        self.vector_store = vector_store or get_vector_store()
        self.document_processor = document_processor or get_document_processor()

    async def list_faqs(
        self,
        category: Optional[str],
        language: Optional[str],
        active_only: bool,
        skip: int,
        limit: int,
    ) -> list[FAQ]:
        query = select(FAQ)
        if category:
            query = query.where(FAQ.category == category)
        if language:
            query = query.where(FAQ.language == language)
        if active_only:
            query = query.where(FAQ.is_active == True)

        result = await self.db.execute(
            query.order_by(FAQ.priority.desc(), FAQ.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def list_categories(self) -> list[str]:
        result = await self.db.execute(
            select(FAQ.category).distinct().where(FAQ.category.isnot(None))
        )
        return [row[0] for row in result.fetchall()]

    async def get_faq(self, faq_id: int) -> FAQ:
        result = await self.db.execute(select(FAQ).where(FAQ.id == faq_id))
        faq = result.scalar_one_or_none()
        if not faq:
            raise ServiceError(404, "FAQ not found")
        return faq

    async def create_faq(self, faq_data: FAQCreate, admin_username: str) -> FAQ:
        faq = FAQ(
            question=faq_data.question,
            answer=faq_data.answer,
            category=faq_data.category,
            language=faq_data.language,
            keywords=faq_data.keywords,
            priority=faq_data.priority,
            created_by=admin_username,
        )
        try:
            self.db.add(faq)
            await self.db.flush()
            await self._index_faq(faq)
            await self.db.commit()
            await self.db.refresh(faq)
            logger.info(f"Created FAQ: {faq.id}")
            return faq
        except Exception as exc:
            await self.db.rollback()
            logger.error(f"Error creating FAQ: {exc}")
            raise ServiceError(500, "Error creating FAQ") from exc

    async def update_faq(self, faq_id: int, faq_data: FAQUpdate) -> FAQ:
        faq = await self.get_faq(faq_id)
        update_data = faq_data.model_dump(exclude_unset=True)

        try:
            for field, value in update_data.items():
                setattr(faq, field, value)

            await self.db.flush()
            if not await self.vector_store.delete_faq(faq_id):
                raise ServiceError(502, "FAQ vector deletion failed")
            if faq.is_active:
                await self._index_faq(faq)

            await self.db.commit()
            await self.db.refresh(faq)
            logger.info(f"Updated FAQ: {faq_id}")
            return faq
        except ServiceError:
            await self.db.rollback()
            raise
        except Exception as exc:
            await self.db.rollback()
            logger.error(f"Error updating FAQ: {exc}")
            raise ServiceError(500, "Error updating FAQ") from exc

    async def delete_faq(self, faq_id: int) -> dict:
        faq = await self.get_faq(faq_id)
        try:
            if not await self.vector_store.delete_faq(faq_id):
                raise ServiceError(502, "FAQ vector deletion failed")
            await self.db.delete(faq)
            await self.db.commit()
            logger.info(f"Deleted FAQ: {faq_id}")
            return {"message": "FAQ deleted successfully", "vector_deleted": True}
        except ServiceError:
            await self.db.rollback()
            raise
        except Exception as exc:
            await self.db.rollback()
            logger.error(f"Error deleting FAQ: {exc}")
            raise ServiceError(500, "Error deleting FAQ") from exc

    async def bulk_import_faqs(self, faqs: list[FAQCreate], admin_username: str) -> dict:
        created_count = 0
        errors = []

        for index, faq_data in enumerate(faqs):
            try:
                await self.create_faq(faq_data, admin_username)
                created_count += 1
            except ServiceError as exc:
                errors.append({"index": index, "error": exc.detail})

        return {"created": created_count, "errors": errors, "total": len(faqs)}

    async def reindex_all_faqs(self) -> dict:
        result = await self.db.execute(select(FAQ).where(FAQ.is_active == True))
        faqs = result.scalars().all()

        if not await self.vector_store.delete_by_metadata({"type": "faq"}):
            raise ServiceError(502, "Unable to clear existing FAQ vectors")

        indexed_count = 0
        errors = []
        for faq in faqs:
            try:
                await self._index_faq(faq)
                indexed_count += 1
            except Exception as exc:
                logger.error(f"Error reindexing FAQ {faq.id}: {exc}")
                errors.append({"faq_id": faq.id, "error": str(exc)})

        return {"indexed": indexed_count, "errors": errors}

    async def _index_faq(self, faq: FAQ) -> int:
        chunks = await self.document_processor.process_faq(
            question=faq.question,
            answer=faq.answer,
            category=faq.category,
            faq_id=faq.id,
        )
        return await self.vector_store.add_documents(chunks)
