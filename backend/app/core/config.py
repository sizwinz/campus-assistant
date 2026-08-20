"""
Configuration settings for the Campus Assistant Chatbot.
Uses pydantic-settings for secure environment variable management.

SECURITY: All secrets must be provided via environment variables.
No hardcoded credentials are used in production.
"""

import warnings
from functools import lru_cache
from typing import List, Optional

from pydantic import Field, field_validator, SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    All sensitive values use SecretStr for secure handling.
    Production deployments MUST set all required environment variables.
    """

    # ===========================================
    # Application Info
    # ===========================================
    app_name: str = "Campus Assistant"
    app_version: str = "2.0.0"
    debug: bool = Field(default=False, description="Enable debug mode (never in production)")
    environment: str = Field(default="development", description="Environment: development, staging, production")

    # ===========================================
    # Security (REQUIRED in production)
    # ===========================================
    secret_key: SecretStr = Field(
        default=SecretStr("CHANGE-THIS-IN-PRODUCTION-USE-SECURE-KEY"),
        description="Secret key for JWT signing - MUST be changed in production"
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: SecretStr) -> SecretStr:
        """Warn if using default secret key."""
        if v.get_secret_value() == "CHANGE-THIS-IN-PRODUCTION-USE-SECURE-KEY":
            warnings.warn(
                "Using default SECRET_KEY is insecure. Set a proper secret in production.",
                UserWarning
            )
        return v

    # ===========================================
    # CORS Configuration
    # ===========================================
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="Comma-separated list of allowed CORS origins"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    # ===========================================
    # Database Configuration
    # ===========================================
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/chatbot.db",
        description="Database URL. Use postgresql+asyncpg:// for production"
    )

    # ===========================================
    # LLM Configuration
    # ===========================================
    llm_provider: str = Field(
        default="gemini",
        description="LLM provider: gemini or openai"
    )
    google_api_key: Optional[SecretStr] = Field(
        default=None,
        description="Google Gemini API key"
    )
    openai_api_key: Optional[SecretStr] = Field(
        default=None,
        description="OpenAI API key"
    )
    llm_model: str = Field(
        default="gemini-2.0-flash",
        description="LLM model name"
    )
    llm_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="LLM temperature for response generation"
    )
    llm_max_tokens: int = Field(
        default=1024,
        ge=1,
        le=8192,
        description="Maximum tokens in LLM response"
    )

    # ===========================================
    # Bhashini Translation API (Optional)
    # ===========================================
    bhashini_user_id: Optional[str] = None
    bhashini_api_key: Optional[SecretStr] = None
    bhashini_pipeline_id: Optional[str] = None

    # Google Translate fallback (Optional)
    google_translate_api_key: Optional[SecretStr] = None

    # ===========================================
    # Telegram Integration (Optional)
    # ===========================================
    telegram_bot_token: Optional[SecretStr] = Field(
        default=None,
        description="Telegram bot token from @BotFather"
    )
    public_base_url: Optional[str] = Field(
        default=None,
        description="Public HTTPS base URL used for webhooks, e.g. https://example.edu",
    )

    # ===========================================
    # Twilio/WhatsApp (Optional, Future)
    # ===========================================
    twilio_account_sid: Optional[SecretStr] = None
    twilio_auth_token: Optional[SecretStr] = None
    twilio_whatsapp_number: Optional[str] = None

    # ===========================================
    # Admin Authentication
    # NOTE: Default credentials are for development only
    # Production MUST use hashed passwords set via CLI/migration
    # ===========================================
    admin_username: str = Field(
        default="admin",
        description="Admin username for basic auth"
    )
    # This is the bcrypt hash of the admin password - NOT the password itself
    # Default hash is for development only - you MUST change this in production
    admin_password_hash: Optional[str] = Field(
        default=None,
        description="Bcrypt hash of admin password. Use 'python -m app.cli hash-password' to generate"
    )

    # ===========================================
    # Logging & Observability
    # ===========================================
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: Optional[str] = Field(
        default=None,
        description="Optional log file path. Leave empty to disable file logging"
    )
    log_format: str = Field(
        default="json",
        description="Log format: json or text"
    )
    sentry_dsn: Optional[str] = Field(
        default=None,
        description="Sentry DSN for error tracking"
    )

    # ===========================================
    # Vector Database Settings
    # ===========================================
    chroma_persist_directory: str = Field(
        default="./data/chroma",
        description="Directory for ChromaDB persistence"
    )
    embedding_model: str = Field(
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        description="Sentence transformer model for embeddings"
    )
    vector_search_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of documents to retrieve in vector search"
    )
    vector_score_threshold: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum score threshold for vector search results"
    )

    # ===========================================
    # Rate Limiting
    # ===========================================
    rate_limit_requests: int = Field(
        default=60,
        ge=1,
        description="Maximum requests per rate limit window"
    )
    rate_limit_window_seconds: int = Field(
        default=60,
        ge=1,
        description="Rate limit window in seconds"
    )

    # ===========================================
    # Session Management
    # ===========================================
    session_timeout_hours: int = Field(
        default=24,
        ge=1,
        description="Session timeout in hours"
    )
    max_conversation_history: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum conversation history entries to include in context"
    )

    # ===========================================
    # Supported Languages
    # ===========================================
    supported_languages: List[str] = Field(
        default=["en", "hi", "raj", "gu", "mr", "pa", "ta"]
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        case_sensitive = False

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment.lower() == "development"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Settings are loaded once and cached for the application lifetime.
    """
    return Settings()


# ===========================================
# Language Constants
# ===========================================
LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "raj": "Rajasthani",
    "gu": "Gujarati",
    "mr": "Marathi",
    "pa": "Punjabi",
    "ta": "Tamil",
    "bn": "Bengali",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "or": "Odia",
}

# Bhashini language codes mapping
BHASHINI_LANG_CODES = {
    "en": "en",
    "hi": "hi",
    "gu": "gu",
    "mr": "mr",
    "pa": "pa",
    "ta": "ta",
    "bn": "bn",
    "te": "te",
    "kn": "kn",
    "ml": "ml",
    "or": "or",
    "raj": "hi",  # Rajasthani falls back to Hindi
}
