"""
Tests for LLM service configuration.
"""

from pydantic import SecretStr

from app.core.config import Settings
from app.services import llm_service


def test_llm_service_uses_configured_gemini_settings(monkeypatch) -> None:
    captured: dict = {}

    class FakeGemini:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(llm_service, "ChatGoogleGenerativeAI", FakeGemini)
    monkeypatch.setattr(
        llm_service,
        "settings",
        Settings(
            environment="test",
            secret_key=SecretStr("test-secret"),
            llm_provider="gemini",
            google_api_key=SecretStr("test-google-key"),
            llm_model="gemini-test-model",
            llm_temperature=0.7,
            llm_max_tokens=2048,
        ),
    )

    llm_service.LLMService()

    assert captured["model"] == "gemini-test-model"
    assert captured["temperature"] == 0.7
    assert captured["max_tokens"] == 2048
