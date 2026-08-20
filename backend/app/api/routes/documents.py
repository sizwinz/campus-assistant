"""
Document Management API Routes.
Endpoints for uploading and managing documents (PDFs, DOCX, etc.).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import verify_admin
from app.core.database import get_db
from app.core.rate_limit import DOCUMENT_UPLOAD_RATE_LIMIT, limiter
from app.models.schemas import DocumentUploadResponse, DocumentInfo
from app.services.document_service import DocumentService
from app.services.exceptions import ServiceError

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("/", response_model=List[DocumentInfo])
async def list_documents(
    category: Optional[str] = None,
    indexed_only: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """
    List all uploaded documents.
    """
    return await DocumentService(db).list_documents(category, indexed_only, skip, limit)


@router.get("/stats/summary")
async def get_document_stats(db: AsyncSession = Depends(get_db)):
    """
    Get document statistics.
    """
    return await DocumentService(db).get_stats()


@router.get("/{doc_id}", response_model=DocumentInfo)
async def get_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get document information by ID.
    """
    try:
        return await DocumentService(db).get_document(doc_id)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/upload", response_model=DocumentUploadResponse)
@limiter.limit(DOCUMENT_UPLOAD_RATE_LIMIT)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    category: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    auto_index: bool = Form(True),
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """
    Upload a document for processing and indexing. Requires admin authentication.

    Supported formats: PDF, DOCX, DOC, TXT
    Max file size: 10 MB
    """
    del request
    filename = file.filename or "unknown"
    content = await file.read()
    try:
        return await DocumentService(db).upload_document(
            content=content,
            filename=filename,
            content_type=file.content_type,
            category=category,
            description=description,
            auto_index=auto_index,
            admin_username=admin,
        )
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.extra or exc.detail)


@router.post("/{doc_id}/index")
async def index_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """
    Index a document that was uploaded without auto-indexing. Requires admin authentication.
    """
    del admin
    try:
        return await DocumentService(db).index_document(doc_id)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.extra or exc.detail)


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """
    Delete a document and remove from vector store. Requires admin authentication.
    """
    del admin
    try:
        return await DocumentService(db).delete_document(doc_id)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.extra or exc.detail)
