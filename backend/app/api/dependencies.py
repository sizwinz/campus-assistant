"""
Shared FastAPI dependencies for API routes.
"""

import secrets

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from loguru import logger

from app.core.config import get_settings
from app.core.security import verify_password

security = HTTPBasic()
settings = get_settings()

# Development-only default hash for password: dev-password-change-me
DEV_PASSWORD_HASH = "$2b$12$.8rTB.T6wG/8iv5ma1BTkOPTXDcrbjwcKl1s2vCUVdP5zPnp59nWW"


def verify_admin(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """
    Verify admin Basic Auth credentials for management endpoints.

    Production deployments must set ADMIN_PASSWORD_HASH. The development fallback
    keeps local setup easy but is rejected when ENVIRONMENT=production.
    """
    correct_username = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        settings.admin_username.encode("utf-8"),
    )

    password_hash = settings.admin_password_hash
    if not password_hash:
        if settings.is_production:
            logger.error("ADMIN_PASSWORD_HASH not set in production environment")
            raise HTTPException(status_code=500, detail="Server configuration error")
        password_hash = DEV_PASSWORD_HASH
        logger.warning("Using development default admin password hash.")

    correct_password = verify_password(credentials.password, password_hash)

    if not (correct_username and correct_password):
        logger.warning(f"Failed admin login attempt for user: {credentials.username}")
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
