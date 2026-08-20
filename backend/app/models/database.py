"""
Database models for the Campus Assistant Chatbot.
Uses SQLAlchemy for async database operations.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class MessageRole(str, enum.Enum):
    """Message role in conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class EscalationStatus(str, enum.Enum):
    """Status of escalation to human agent."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    RESOLVED = "resolved"
    CLOSED = "closed"


class User(Base):
    """User model for tracking unique users."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), unique=True, index=True)  # Platform-specific ID
    platform = Column(String(50))  # web, telegram, whatsapp
    preferred_language = Column(String(10), default="en")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sessions = relationship("Session", back_populates="user")


class Session(Base):
    """Conversation session for context management."""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    platform = Column(String(50))
    language = Column(String(10), default="en")
    context = Column(JSON, default=dict)  # Stores conversation context
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session")


class Message(Base):
    """Individual message in a conversation."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), index=True)
    role = Column(Enum(MessageRole))
    content = Column(Text)
    original_content = Column(Text, nullable=True)  # Original if translated
    original_language = Column(String(10), nullable=True)
    intent = Column(String(100), nullable=True)
    confidence = Column(Integer, nullable=True)  # 0-100
    sources = Column(JSON, nullable=True)  # Source documents used
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("Session", back_populates="messages")


class FAQ(Base):
    """FAQ entries that can be managed by admin."""
    __tablename__ = "faqs"

    id = Column(Integer, primary_key=True, index=True)
    question = Column(Text)
    answer = Column(Text)
    category = Column(String(100), nullable=True)
    language = Column(String(10), default="en")
    keywords = Column(JSON, default=list)  # Keywords for matching
    priority = Column(Integer, default=0)  # Higher priority shown first
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)


class Document(Base):
    """Uploaded documents (PDFs, circulars, etc.)."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255))
    original_filename = Column(String(255))
    file_type = Column(String(50))  # pdf, docx, txt
    file_path = Column(String(500))
    category = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    is_indexed = Column(Boolean, default=False)
    indexing_status = Column(String(20), default="pending")
    indexing_error = Column(Text, nullable=True)
    chunk_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    uploaded_by = Column(String(100), nullable=True)


class Escalation(Base):
    """Escalation to human agent when bot cannot help."""
    __tablename__ = "escalations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    reason = Column(Text)
    status = Column(Enum(EscalationStatus), default=EscalationStatus.PENDING)
    assigned_to = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # Relationship
    session = relationship("Session")


class ConversationLog(Base):
    """Daily conversation logs for analysis."""
    __tablename__ = "conversation_logs"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    total_conversations = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    languages_used = Column(JSON, default=dict)
    intents_detected = Column(JSON, default=dict)
    escalation_count = Column(Integer, default=0)
    avg_confidence = Column(Integer, default=0)
    top_queries = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)


class Feedback(Base):
    """User feedback on bot responses."""
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id"))
    rating = Column(Integer)  # 1-5 stars
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    message = relationship("Message")
