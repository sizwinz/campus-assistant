"""Admin analytics application service."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import Document, Escalation, EscalationStatus, FAQ, Message, Session
from app.services.vector_store import VectorStore, get_vector_store


class AdminService:
    """Owns dashboard and analytics queries for admin routes."""

    def __init__(self, db: AsyncSession, vector_store: VectorStore | None = None) -> None:
        self.db = db
        self.vector_store = vector_store or get_vector_store()

    async def get_dashboard(self) -> dict:
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)

        total_sessions = await self.db.scalar(select(func.count(Session.id)))
        active_sessions = await self.db.scalar(
            select(func.count(Session.id)).where(Session.updated_at >= now - timedelta(hours=24))
        )
        total_messages = await self.db.scalar(select(func.count(Message.id)))
        today_messages = await self.db.scalar(
            select(func.count(Message.id)).where(Message.created_at >= today_start)
        )
        pending_escalations = await self.db.scalar(
            select(func.count(Escalation.id)).where(Escalation.status == EscalationStatus.PENDING)
        )
        faq_count = await self.db.scalar(select(func.count(FAQ.id)).where(FAQ.is_active == True))
        doc_count = await self.db.scalar(select(func.count(Document.id)))
        vector_stats = await self.vector_store.get_stats()
        avg_confidence = await self.db.scalar(
            select(func.avg(Message.confidence)).where(
                Message.created_at >= week_ago,
                Message.confidence.isnot(None),
            )
        )

        return {
            "sessions": {"total": total_sessions, "active_24h": active_sessions},
            "messages": {"total": total_messages, "today": today_messages},
            "escalations": {"pending": pending_escalations},
            "knowledge_base": {
                "faqs": faq_count,
                "documents": doc_count,
                "vector_chunks": vector_stats.get("total_documents", 0),
            },
            "performance": {"avg_confidence_7d": round(avg_confidence or 0, 1)},
        }

    async def get_analytics(self, days: int) -> dict:
        now = datetime.utcnow()
        start_date = now - timedelta(days=days)

        language_rows = await self.db.execute(
            select(Message.original_language, func.count(Message.id))
            .where(Message.created_at >= start_date, Message.original_language.isnot(None))
            .group_by(Message.original_language)
        )
        intent_rows = await self.db.execute(
            select(Message.intent, func.count(Message.id))
            .where(Message.created_at >= start_date, Message.intent.isnot(None))
            .group_by(Message.intent)
            .order_by(func.count(Message.id).desc())
            .limit(10)
        )

        daily_counts = []
        for day_offset in range(days):
            day = start_date + timedelta(days=day_offset)
            day_end = day + timedelta(days=1)
            count = await self.db.scalar(
                select(func.count(Message.id)).where(
                    Message.created_at >= day,
                    Message.created_at < day_end,
                )
            )
            daily_counts.append({"date": day.strftime("%Y-%m-%d"), "count": count})

        platform_rows = await self.db.execute(
            select(Session.platform, func.count(Session.id))
            .where(Session.created_at >= start_date)
            .group_by(Session.platform)
        )

        return {
            "period_days": days,
            "languages_used": {row[0]: row[1] for row in language_rows.fetchall()},
            "top_intents": {row[0]: row[1] for row in intent_rows.fetchall()},
            "daily_messages": daily_counts,
            "platforms": {row[0]: row[1] for row in platform_rows.fetchall()},
        }
