"""
Campus Assistant Chatbot - Main Application
A multilingual chatbot for educational institutions.

FEATURES:
- Structured JSON logging for production
- Prometheus metrics endpoint
- Request ID middleware for tracing
- Rate limiting middleware
- Sentry integration for error tracking
"""

import sys
import time
import uuid
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.database import init_db
from app.core.rate_limit import limiter
from app.api import (
    chat_router,
    faq_router,
    document_router,
    admin_router,
    telegram_router,
)

settings = get_settings()

# ===========================================
# Logging Configuration
# ===========================================

def json_sink(message):
    """JSON log sink for structured logging."""
    record = message.record
    log_entry = {
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "logger": record["name"],
        "message": record["message"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
    }
    if record["exception"]:
        log_entry["exception"] = str(record["exception"])
    print(__import__("json").dumps(log_entry), flush=True)


# Configure logging based on format setting
logger.remove()

if settings.log_format == "json":
    logger.add(json_sink, level=settings.log_level, serialize=False)
else:
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
    )

# File logging (optional)
if settings.log_file and settings.log_file.strip():
    try:
        import os
        log_dir = os.path.dirname(settings.log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        logger.add(
            settings.log_file,
            rotation="1 day",
            retention="30 days",
            level=settings.log_level,
            serialize=(settings.log_format == "json"),
        )
    except Exception as e:
        logger.warning(f"Could not set up file logging: {e}")

# ===========================================
# Sentry Integration (Optional)
# ===========================================

if settings.sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.1 if settings.is_production else 1.0,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
            ],
        )
        logger.info("Sentry error tracking enabled")
    except Exception as e:
        logger.warning(f"Could not initialize Sentry: {e}")

# ===========================================
# Prometheus Metrics
# ===========================================

REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"]
)

CHAT_MESSAGES = Counter(
    "chat_messages_total",
    "Total chat messages processed",
    ["language", "intent"]
)

# ===========================================
# Application Lifespan
# ===========================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down application")


# ===========================================
# FastAPI Application
# ===========================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="""
## Campus Assistant Chatbot

A multilingual conversational AI assistant for educational institutions.

### Features:
- **Multilingual Support**: Hindi, English, Gujarati, Marathi, Punjabi, Tamil, and more
- **FAQ Management**: Easy-to-manage FAQ database
- **Document Processing**: Upload and index PDFs, DOCX files
- **Context Awareness**: Multi-turn conversation support
- **Platform Integration**: Web and Telegram

### API Groups:
- **/chat**: Main chatbot interaction endpoints
- **/faqs**: FAQ management (admin auth required for writes)
- **/documents**: Document upload and indexing (admin auth required for writes)
- **/admin**: Dashboard and analytics
- **/telegram**: Telegram bot integration
    """,
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

# Add rate limiter state
app.state.limiter = limiter

# ===========================================
# Middleware
# ===========================================

@app.middleware("http")
async def request_middleware(request: Request, call_next: Callable) -> Response:
    """Add request ID, timing, and metrics to all requests."""
    # Generate request ID
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id

    # Record start time
    start_time = time.time()

    # Process request
    try:
        response = await call_next(request)
    except Exception as e:
        logger.exception(f"Request {request_id} failed: {e}")
        response = JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id}
        )

    # Calculate duration
    duration = time.time() - start_time

    # Add headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{duration:.3f}s"

    # Record metrics
    endpoint = request.url.path
    method = request.method
    status = response.status_code

    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
    REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)

    # Log request (structured)
    logger.info(
        f"{method} {endpoint} - {status} - {duration:.3f}s",
        extra={
            "request_id": request_id,
            "method": method,
            "path": endpoint,
            "status_code": status,
            "duration": duration,
        }
    )

    return response


# Rate limit error handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(_request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please try again later.",
            "retry_after": exc.detail,
        }
    )


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================================
# Routers
# ===========================================

app.include_router(chat_router, prefix="/api/v1")
app.include_router(faq_router, prefix="/api/v1")
app.include_router(document_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(telegram_router, prefix="/api/v1")

# ===========================================
# Health & Metrics Endpoints
# ===========================================

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "environment": settings.environment,
        "docs": "/docs" if not settings.is_production else None,
        "health": "/health",
        "metrics": "/metrics",
    }


@app.get("/health")
async def health():
    """
    Quick health check for load balancers and container orchestration.

    Returns:
        Health status with version information
    """
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/ready")
async def readiness():
    """
    Readiness probe for Kubernetes/container orchestration.
    Checks if the application is ready to accept traffic.
    """
    # Import here to avoid circular imports
    from app.core.database import get_db
    from sqlalchemy import text

    try:
        # Check database connection
        async for db in get_db():
            await db.execute(text("SELECT 1"))
            break
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "database_unavailable"}
        )

    return {"status": "ready", "database": db_status}


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus text format.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
