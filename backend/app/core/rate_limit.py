"""
Shared SlowAPI limiter and endpoint rate-limit policies.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

settings = get_settings()


def _per_window(requests: int) -> str:
    """Build a SlowAPI rate string from configured window settings."""
    window = settings.rate_limit_window_seconds
    if window == 60:
        return f"{requests}/minute"
    return f"{requests}/{window} seconds"


limiter = Limiter(key_func=get_remote_address)

CHAT_RATE_LIMIT = _per_window(min(settings.rate_limit_requests, 20))
DOCUMENT_UPLOAD_RATE_LIMIT = _per_window(min(settings.rate_limit_requests, 5))
ADMIN_RATE_LIMIT = _per_window(min(settings.rate_limit_requests, 10))
TELEGRAM_WEBHOOK_RATE_LIMIT = _per_window(max(settings.rate_limit_requests, 120))
