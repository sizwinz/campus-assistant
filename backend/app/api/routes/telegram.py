"""
Telegram Bot Integration.
Handles Telegram webhook and message processing.
"""

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Request, HTTPException
from loguru import logger
import httpx

from app.api.dependencies import verify_admin
from app.core.config import get_settings
from app.core.rate_limit import TELEGRAM_WEBHOOK_RATE_LIMIT, ADMIN_RATE_LIMIT, limiter
from app.models.schemas import ChatRequest

router = APIRouter(prefix="/telegram", tags=["Telegram"])
settings = get_settings()


@router.post("/webhook")
@limiter.limit(TELEGRAM_WEBHOOK_RATE_LIMIT)
async def telegram_webhook(request: Request):
    """
    Telegram webhook endpoint.
    Receives messages from Telegram and processes them.
    """
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=503, detail="Telegram not configured")

    try:
        data = await request.json()
        logger.debug(f"Telegram webhook data: {data}")

        # Extract message
        message = data.get("message")
        if not message:
            return {"ok": True}

        chat_id = message.get("chat", {}).get("id")
        text = message.get("text", "")
        user_id = str(message.get("from", {}).get("id", ""))
        username = message.get("from", {}).get("username", "")

        if not chat_id or not text:
            return {"ok": True}

        # Handle /start command
        if text.startswith("/start"):
            await send_telegram_message(
                chat_id,
                "🎓 *Welcome to Campus Assistant!*\n\n"
                "I can help you with:\n"
                "• Admission queries\n"
                "• Fee and scholarship info\n"
                "• Exam schedules\n"
                "• Hostel information\n"
                "• And much more!\n\n"
                "Just type your question in any language.\n\n"
                "_Supported: English, Hindi, Gujarati, Marathi, Punjabi, Tamil_",
            )
            return {"ok": True}

        # Handle /help command
        if text.startswith("/help"):
            await send_telegram_message(
                chat_id,
                "ℹ️ *How to use Campus Assistant*\n\n"
                "Simply type your question and I'll help you!\n\n"
                "*Examples:*\n"
                "• What is the fee structure?\n"
                "• Admission last date kya hai?\n"
                "• Hostel facilities ke baare mein batao\n\n"
                "*Commands:*\n"
                "/start - Start the bot\n"
                "/help - Show this help\n"
                "/language - Change language",
            )
            return {"ok": True}

        # Process message through chatbot
        from app.services.chatbot_engine import get_chatbot_engine
        from app.core.database import async_session_maker

        engine = get_chatbot_engine()

        # Create session and process
        async with async_session_maker() as db:
            chat_request = ChatRequest(
                message=text,
                session_id=f"telegram_{chat_id}",
                platform="telegram",
                user_id=user_id,
            )

            response = await engine.process_message(chat_request, db)

            # Format response for Telegram
            reply = response.response

            if response.suggested_questions:
                reply += "\n\n*Suggested questions:*"
                for q in response.suggested_questions[:3]:
                    reply += f"\n• {q}"

            if response.needs_escalation:
                reply += "\n\n_For further assistance, please contact the office._"

            await send_telegram_message(chat_id, reply)

        return {"ok": True}

    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
        return {"ok": True}  # Always return ok to prevent retries


async def send_telegram_message(chat_id: int, text: str):
    """Send message to Telegram chat."""
    if not settings.telegram_bot_token:
        return

    token = settings.telegram_bot_token.get_secret_value()
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                },
            )
    except Exception as e:
        logger.error(f"Error sending Telegram message: {e}")


@router.get("/setup")
@limiter.limit(ADMIN_RATE_LIMIT)
async def setup_webhook(
    request: Request,
    host: str | None = None,
    admin: str = Depends(verify_admin),
):
    """
    Set up Telegram webhook. Requires admin authentication.

    In production, PUBLIC_BASE_URL must be configured and HTTPS. If host is
    provided, it must match PUBLIC_BASE_URL exactly.
    """
    del request, admin
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=503, detail="Telegram not configured")

    base_url = _validate_webhook_base_url(host)
    webhook_url = f"{base_url}/api/v1/telegram/webhook"

    token = settings.telegram_bot_token.get_secret_value()
    url = f"https://api.telegram.org/bot{token}/setWebhook"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={"url": webhook_url},
            )
            data = response.json()

            if data.get("ok"):
                return {
                    "message": "Webhook set successfully",
                    "webhook_url": webhook_url,
                }
            else:
                return {"error": data.get("description")}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info")
async def get_bot_info():
    """Get Telegram bot information."""
    if not settings.telegram_bot_token:
        raise HTTPException(status_code=503, detail="Telegram not configured")

    token = settings.telegram_bot_token.get_secret_value()
    url = f"https://api.telegram.org/bot{token}/getMe"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            data = response.json()

            if data.get("ok"):
                return data.get("result")
            else:
                return {"error": data.get("description")}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _validate_webhook_base_url(host: str | None) -> str:
    configured = settings.public_base_url.rstrip("/") if settings.public_base_url else None
    requested = host.rstrip("/") if host else None

    if configured:
        base_url = configured
        if requested and requested != configured:
            raise HTTPException(status_code=400, detail="host must match configured PUBLIC_BASE_URL")
    elif settings.is_production:
        raise HTTPException(status_code=400, detail="PUBLIC_BASE_URL must be configured in production")
    elif requested:
        base_url = requested
    else:
        raise HTTPException(status_code=400, detail="host or PUBLIC_BASE_URL is required")

    parsed = urlparse(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail="Webhook base URL must be an absolute URL")
    if settings.is_production and parsed.scheme != "https":
        raise HTTPException(status_code=400, detail="Telegram webhook must use HTTPS in production")

    return base_url
