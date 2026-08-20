"""
Admin API Routes.
Dashboard, analytics, and administration endpoints.

SECURITY: Uses bcrypt for password verification.
Admin password hash must be set via ADMIN_PASSWORD_HASH environment variable.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import verify_admin
from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import ADMIN_RATE_LIMIT, limiter
from app.models.database import (
    Escalation,
    EscalationStatus,
    Feedback,
    Message,
    Session,
)
from app.models.schemas import (
    EscalationUpdate,
)
from app.services.admin_service import AdminService
from app.services.session_manager import get_session_manager
from app.services.vector_store import get_vector_store

router = APIRouter(prefix="/admin", tags=["Admin"])
settings = get_settings()


# ==================== Dashboard ====================


@router.get("/dashboard")
@limiter.limit(ADMIN_RATE_LIMIT)
async def get_dashboard(
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """
    Get dashboard summary with key metrics.
    """
    del request, admin
    return await AdminService(db).get_dashboard()


# ==================== Analytics ====================


@router.get("/analytics")
@limiter.limit(ADMIN_RATE_LIMIT)
async def get_analytics(
    request: Request,
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """
    Get detailed analytics for the specified period.
    """
    del request, admin
    return await AdminService(db).get_analytics(days)


# ==================== Conversation Logs ====================


@router.get("/conversations")
async def list_conversations(
    date: Optional[str] = None,
    platform: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """
    List conversation sessions with messages.
    """
    query = select(Session).order_by(Session.updated_at.desc())

    if platform:
        query = query.where(Session.platform == platform)

    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d")
            query = query.where(
                Session.created_at >= target_date,
                Session.created_at < target_date + timedelta(days=1),
            )
        except ValueError:
            pass

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    sessions = result.scalars().all()

    conversations = []
    for session in sessions:
        # Get messages for this session
        msg_result = await db.execute(
            select(Message)
            .where(Message.session_id == session.id)
            .order_by(Message.created_at)
        )
        messages = msg_result.scalars().all()

        conversations.append(
            {
                "session_id": session.session_id,
                "platform": session.platform,
                "language": session.language,
                "is_active": session.is_active,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "message_count": len(messages),
                "messages": [
                    {
                        "role": msg.role.value,
                        "content": msg.content,
                        "original_content": msg.original_content,
                        "intent": msg.intent,
                        "confidence": msg.confidence,
                        "created_at": msg.created_at.isoformat(),
                    }
                    for msg in messages
                ],
            }
        )

    return {"conversations": conversations, "total": len(conversations)}


@router.get("/conversations/export")
async def export_conversations(
    date: str = Query(..., description="Date in YYYY-MM-DD format"),
    format: str = Query("json", description="Export format: json or csv"),
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """
    Export conversations for a specific date.
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    # Get all sessions for the date
    result = await db.execute(
        select(Session).where(
            Session.created_at >= target_date,
            Session.created_at < target_date + timedelta(days=1),
        )
    )
    sessions = result.scalars().all()

    export_data = []
    for session in sessions:
        msg_result = await db.execute(
            select(Message)
            .where(Message.session_id == session.id)
            .order_by(Message.created_at)
        )
        messages = msg_result.scalars().all()

        for msg in messages:
            export_data.append(
                {
                    "session_id": session.session_id,
                    "platform": session.platform,
                    "language": session.language,
                    "role": msg.role.value,
                    "content": msg.content,
                    "original_language": msg.original_language,
                    "intent": msg.intent,
                    "confidence": msg.confidence,
                    "timestamp": msg.created_at.isoformat(),
                }
            )

    return {
        "date": date,
        "total_messages": len(export_data),
        "data": export_data,
    }


# ==================== Escalations ====================


@router.get("/escalations")
async def list_escalations(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """
    List escalation requests.
    """
    query = select(Escalation).order_by(Escalation.created_at.desc())

    if status:
        try:
            status_enum = EscalationStatus(status)
            query = query.where(Escalation.status == status_enum)
        except ValueError:
            pass

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    escalations = result.scalars().all()

    return [
        {
            "id": esc.id,
            "session_id": esc.session_id,
            "reason": esc.reason,
            "status": esc.status.value,
            "assigned_to": esc.assigned_to,
            "resolution_notes": esc.resolution_notes,
            "created_at": esc.created_at.isoformat(),
            "resolved_at": esc.resolved_at.isoformat() if esc.resolved_at else None,
        }
        for esc in escalations
    ]


@router.put("/escalations/{escalation_id}")
async def update_escalation(
    escalation_id: int,
    update_data: EscalationUpdate,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """
    Update escalation status.
    """
    result = await db.execute(
        select(Escalation).where(Escalation.id == escalation_id)
    )
    escalation = result.scalar_one_or_none()

    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")

    try:
        escalation.status = EscalationStatus(update_data.status)
        if update_data.assigned_to:
            escalation.assigned_to = update_data.assigned_to
        if update_data.resolution_notes:
            escalation.resolution_notes = update_data.resolution_notes

        if update_data.status in ["resolved", "closed"]:
            escalation.resolved_at = datetime.utcnow()

        await db.commit()
        return {"message": "Escalation updated successfully"}

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Feedback ====================


@router.get("/feedback")
async def list_feedback(
    min_rating: Optional[int] = None,
    max_rating: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """
    List user feedback.
    """
    query = select(Feedback).order_by(Feedback.created_at.desc())

    if min_rating:
        query = query.where(Feedback.rating >= min_rating)
    if max_rating:
        query = query.where(Feedback.rating <= max_rating)

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    feedback_list = result.scalars().all()

    return [
        {
            "id": fb.id,
            "message_id": fb.message_id,
            "rating": fb.rating,
            "comment": fb.comment,
            "created_at": fb.created_at.isoformat(),
        }
        for fb in feedback_list
    ]


# ==================== System ====================


@router.post("/cleanup")
async def cleanup_expired_sessions(
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """
    Clean up expired sessions.
    """
    session_manager = get_session_manager()
    count = await session_manager.cleanup_expired_sessions(db)

    return {"cleaned_sessions": count}


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    System health check (no auth required).
    """
    # Check database
    try:
        await db.execute(select(1))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    # Check vector store
    try:
        vector_store = get_vector_store()
        await vector_store.get_stats()
        vector_status = "healthy"
    except Exception:
        vector_status = "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "version": settings.app_version,
        "database": db_status,
        "vector_db": vector_status,
        "llm_provider": settings.llm_provider,
    }
