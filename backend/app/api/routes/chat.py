"""
Chat API Routes.
Main endpoint for chatbot interactions.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.core.rate_limit import CHAT_RATE_LIMIT, limiter
from app.models.schemas import ChatRequest, ChatResponse
from app.services.chatbot_engine import get_chatbot_engine
from app.services.translation import get_translation_service

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/", response_model=ChatResponse)
@limiter.limit(CHAT_RATE_LIMIT)
async def send_message(
    request: Request,
    chat_request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message to the chatbot.

    - **message**: User's message (required)
    - **session_id**: Session ID for context continuity (optional)
    - **language**: Preferred response language code (optional)
    - **platform**: Source platform - web, telegram, whatsapp (default: web)
    - **user_id**: External user identifier (optional)

    Returns:
    - Bot's response with detected language, confidence, and sources
    """
    del request
    try:
        engine = get_chatbot_engine()
        response = await engine.process_message(chat_request, db)
        return response

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing your message. Please try again.",
        )


@router.get("/welcome")
async def get_welcome(language: str = "en"):
    """
    Get welcome message in specified language.

    - **language**: Language code (en, hi, gu, mr, pa, ta, etc.)
    """
    try:
        engine = get_chatbot_engine()
        message = await engine.get_welcome_message(language)
        return {"message": message, "language": language}

    except Exception as e:
        logger.error(f"Welcome message error: {e}")
        return {
            "message": "Welcome! How can I help you today?",
            "language": "en",
        }


@router.get("/languages")
async def get_supported_languages():
    """
    Get list of supported languages.
    """
    translation_service = get_translation_service()
    return {
        "languages": translation_service.get_supported_languages(),
        "default": "en",
    }


@router.post("/detect-language")
async def detect_language(text: str):
    """
    Detect language of given text.
    """
    translation_service = get_translation_service()
    lang_code = await translation_service.detect_language(text)
    lang_name = translation_service.get_language_name(lang_code)

    return {
        "code": lang_code,
        "name": lang_name,
    }
