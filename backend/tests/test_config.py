"""
Tests for configuration settings.
"""

import os
import pytest
import warnings


class TestSettings:
    """Tests for application settings."""

    def test_settings_loads_defaults(self, monkeypatch):
        """Test that settings load with defaults."""
        from app.core.config import Settings

        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("DEBUG", raising=False)
        settings = Settings(_env_file=None)

        assert settings.app_name == "Campus Assistant"
        assert settings.environment == "development"
        assert settings.debug is False

    def test_settings_from_env_vars(self, monkeypatch):
        """Test that settings read from environment variables."""
        monkeypatch.setenv("APP_NAME", "Test App")
        monkeypatch.setenv("ENVIRONMENT", "test")
        monkeypatch.setenv("DEBUG", "true")

        # Clear cache to get fresh settings
        from app.core.config import Settings
        settings = Settings()

        assert settings.app_name == "Test App"
        assert settings.environment == "test"
        assert settings.debug is True

    def test_cors_origins_parsing(self):
        """Test CORS origins string is parsed correctly."""
        from app.core.config import Settings

        settings = Settings(cors_origins="http://a.com,http://b.com,http://c.com")

        assert settings.cors_origins_list == [
            "http://a.com",
            "http://b.com",
            "http://c.com",
        ]

    def test_cors_origins_handles_whitespace(self):
        """Test CORS origins handles whitespace correctly."""
        from app.core.config import Settings

        settings = Settings(cors_origins="http://a.com , http://b.com , ")

        assert "http://a.com" in settings.cors_origins_list
        assert "http://b.com" in settings.cors_origins_list
        assert "" not in settings.cors_origins_list

    def test_is_production_check(self):
        """Test is_production property."""
        from app.core.config import Settings

        dev_settings = Settings(environment="development")
        prod_settings = Settings(environment="production")

        assert dev_settings.is_production is False
        assert dev_settings.is_development is True
        assert prod_settings.is_production is True
        assert prod_settings.is_development is False

    def test_default_secret_key_warning(self, monkeypatch):
        """Test that default secret key triggers a warning."""
        from app.core.config import Settings

        monkeypatch.delenv("SECRET_KEY", raising=False)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            Settings(_env_file=None)

            # Check if warning was raised
            warning_messages = [str(warning.message) for warning in w]
            assert any("SECRET_KEY" in msg for msg in warning_messages)

    def test_llm_settings_validation(self):
        """Test LLM settings have valid ranges."""
        from app.core.config import Settings

        settings = Settings()

        assert 0.0 <= settings.llm_temperature <= 2.0
        assert 1 <= settings.llm_max_tokens <= 8192

    def test_rate_limit_settings(self):
        """Test rate limiting settings exist."""
        from app.core.config import Settings

        settings = Settings()

        assert settings.rate_limit_requests >= 1
        assert settings.rate_limit_window_seconds >= 1


class TestLanguageConstants:
    """Tests for language-related constants."""

    def test_language_names_exist(self):
        """Test language names dictionary exists."""
        from app.core.config import LANGUAGE_NAMES

        assert "en" in LANGUAGE_NAMES
        assert "hi" in LANGUAGE_NAMES
        assert LANGUAGE_NAMES["en"] == "English"
        assert LANGUAGE_NAMES["hi"] == "Hindi"

    def test_bhashini_lang_codes_exist(self):
        """Test Bhashini language codes exist."""
        from app.core.config import BHASHINI_LANG_CODES

        assert "en" in BHASHINI_LANG_CODES
        assert "raj" in BHASHINI_LANG_CODES
        # Rajasthani falls back to Hindi
        assert BHASHINI_LANG_CODES["raj"] == "hi"
