"""
Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ===========================================
# Chat Schemas
# ===========================================

class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""
    message: str = Field(..., min_length=1, max_length=5000, description="User's message")
    session_id: Optional[str] = Field(None, description="Session ID for context")
    language: Optional[str] = Field(None, description="Preferred response language")
    platform: str = Field(default="web", description="Source platform")
    user_id: Optional[str] = Field(None, description="External user ID")


class ChatSource(BaseModel):
    """Source document reference."""
    title: str
    content: str
    score: float
    document_id: Optional[int] = None


class ChatResponse(BaseModel):
    """Response schema for chat endpoint."""
    response: str = Field(..., description="Bot's response")
    session_id: str = Field(..., description="Session ID")
    detected_language: str = Field(..., description="Detected input language")
    response_language: str = Field(..., description="Response language")
    intent: Optional[str] = Field(None, description="Detected intent")
    confidence: int = Field(..., ge=0, le=100, description="Confidence score")
    sources: List[ChatSource] = Field(default=[], description="Source documents")
    needs_escalation: bool = Field(default=False, description="Whether human help needed")
    suggested_questions: List[str] = Field(default=[], description="Follow-up suggestions")


# ===========================================
# Session Schemas
# ===========================================

class SessionContext(BaseModel):
    """Context stored in session."""
    last_topic: Optional[str] = None
    last_intent: Optional[str] = None
    conversation_history: List[Dict[str, str]] = []
    user_preferences: Dict[str, Any] = {}


class SessionInfo(BaseModel):
    """Session information response."""
    session_id: str
    platform: str
    language: str
    is_active: bool
    created_at: datetime
    message_count: int


# ===========================================
# FAQ Schemas
# ===========================================

class FAQCreate(BaseModel):
    """Schema for creating FAQ."""
    question: str = Field(..., min_length=5)
    answer: str = Field(..., min_length=10)
    category: Optional[str] = None
    language: str = Field(default="en")
    keywords: List[str] = Field(default=[])
    priority: int = Field(default=0, ge=0, le=100)


class FAQUpdate(BaseModel):
    """Schema for updating FAQ."""
    question: Optional[str] = None
    answer: Optional[str] = None
    category: Optional[str] = None
    language: Optional[str] = None
    keywords: Optional[List[str]] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class FAQResponse(BaseModel):
    """FAQ response schema."""
    id: int
    question: str
    answer: str
    category: Optional[str]
    language: str
    keywords: List[str]
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ===========================================
# Document Schemas
# ===========================================

class DocumentUploadResponse(BaseModel):
    """Response after document upload."""
    id: int
    filename: str
    file_type: str
    is_indexed: bool
    indexing_status: str
    indexing_error: Optional[str] = None
    chunk_count: int
    message: str


class DocumentInfo(BaseModel):
    """Document information."""
    id: int
    filename: str
    original_filename: str
    file_type: str
    category: Optional[str]
    description: Optional[str]
    is_indexed: bool
    indexing_status: str
    indexing_error: Optional[str] = None
    chunk_count: int
    uploaded_at: datetime

    class Config:
        from_attributes = True


# ===========================================
# Analytics Schemas
# ===========================================

class DailyStats(BaseModel):
    """Daily statistics."""
    date: datetime
    total_conversations: int
    total_messages: int
    languages_used: Dict[str, int]
    intents_detected: Dict[str, int]
    escalation_count: int
    avg_confidence: float
    top_queries: List[Dict[str, Any]]


class AnalyticsSummary(BaseModel):
    """Analytics summary for dashboard."""
    total_conversations: int
    total_messages: int
    active_users: int
    avg_response_confidence: float
    escalation_rate: float
    most_used_language: str
    top_intents: List[Dict[str, Any]]
    daily_stats: List[DailyStats]


# ===========================================
# Escalation Schemas
# ===========================================

class EscalationCreate(BaseModel):
    """Create escalation request."""
    session_id: str
    reason: str


class EscalationUpdate(BaseModel):
    """Update escalation status."""
    status: str
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None


class EscalationResponse(BaseModel):
    """Escalation response."""
    id: int
    session_id: int
    reason: str
    status: str
    assigned_to: Optional[str]
    resolution_notes: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True


# ===========================================
# Feedback Schemas
# ===========================================

class FeedbackCreate(BaseModel):
    """Create feedback."""
    message_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Feedback response."""
    id: int
    message_id: int
    rating: int
    comment: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ===========================================
# Admin Schemas
# ===========================================

class AdminLogin(BaseModel):
    """Admin login request."""
    username: str
    password: str


class AdminToken(BaseModel):
    """Admin token response."""
    access_token: str
    token_type: str = "bearer"


class HealthCheck(BaseModel):
    """Health check response."""
    status: str
    version: str
    database: str
    vector_db: str
    llm_provider: str
