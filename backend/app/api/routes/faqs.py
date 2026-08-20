"""
FAQ Management API Routes.
Admin endpoints for managing FAQ entries.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import verify_admin
from app.core.database import get_db
from app.models.schemas import FAQCreate, FAQUpdate, FAQResponse
from app.services.exceptions import ServiceError
from app.services.faq_service import FAQService

router = APIRouter(prefix="/faqs", tags=["FAQs"])


@router.get("/", response_model=List[FAQResponse])
async def list_faqs(
    category: Optional[str] = None,
    language: Optional[str] = None,
    active_only: bool = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """
    List all FAQs with optional filtering.
    """
    return await FAQService(db).list_faqs(category, language, active_only, skip, limit)


@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    """
    Get list of all FAQ categories.
    """
    return {"categories": await FAQService(db).list_categories()}


@router.get("/{faq_id}", response_model=FAQResponse)
async def get_faq(faq_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get a specific FAQ by ID.
    """
    try:
        return await FAQService(db).get_faq(faq_id)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/", response_model=FAQResponse)
async def create_faq(
    faq_data: FAQCreate,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """
    Create a new FAQ entry. Requires admin authentication.
    """
    try:
        return await FAQService(db).create_faq(faq_data, admin)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.put("/{faq_id}", response_model=FAQResponse)
async def update_faq(
    faq_id: int,
    faq_data: FAQUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: str = Depends(verify_admin),
):
    """
    Update an existing FAQ. Requires admin authentication.
    """
    try:
        return await FAQService(db).update_faq(faq_id, faq_data)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.delete("/{faq_id}")
async def delete_faq(
    faq_id: int,
    db: AsyncSession = Depends(get_db),
    _admin: str = Depends(verify_admin),
):
    """
    Delete an FAQ entry. Requires admin authentication.
    """
    try:
        return await FAQService(db).delete_faq(faq_id)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/bulk-import")
async def bulk_import_faqs(
    faqs: List[FAQCreate],
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """
    Bulk import multiple FAQs. Requires admin authentication.
    """
    return await FAQService(db).bulk_import_faqs(faqs, admin)


@router.post("/reindex")
async def reindex_all_faqs(
    db: AsyncSession = Depends(get_db),
    _admin: str = Depends(verify_admin),
):
    """
    Reindex all active FAQs in vector store. Requires admin authentication.
    """
    try:
        return await FAQService(db).reindex_all_faqs()
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
