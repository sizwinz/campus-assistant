"""
Regression tests for protected management endpoints.
"""

from io import BytesIO

import pytest
from httpx import AsyncClient

from app.models.schemas import ChatResponse


@pytest.mark.asyncio
async def test_faq_mutations_require_admin_auth(
    client: AsyncClient, sample_faq_data: dict
) -> None:
    endpoints = [
        ("post", "/api/v1/faqs/", {"json": sample_faq_data}),
        ("put", "/api/v1/faqs/1", {"json": {"answer": "Updated answer"}}),
        ("delete", "/api/v1/faqs/1", {}),
        ("post", "/api/v1/faqs/bulk-import", {"json": [sample_faq_data]}),
        ("post", "/api/v1/faqs/reindex", {}),
    ]

    for method, url, kwargs in endpoints:
        response = await getattr(client, method)(url, **kwargs)
        assert response.status_code == 401, f"{method.upper()} {url} was not protected"


@pytest.mark.asyncio
async def test_document_mutations_require_admin_auth(client: AsyncClient) -> None:
    upload = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("sample.txt", BytesIO(b"hello"), "text/plain")},
    )
    assert upload.status_code == 401

    index = await client.post("/api/v1/documents/1/index")
    assert index.status_code == 401

    delete = await client.delete("/api/v1/documents/1")
    assert delete.status_code == 401


@pytest.mark.asyncio
async def test_telegram_setup_requires_admin_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/telegram/setup?host=http://attacker.example")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_endpoint_still_accepts_public_requests(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeEngine:
        async def process_message(self, request, db):
            return ChatResponse(
                response=f"Echo: {request.message}",
                session_id="test-session",
                detected_language=request.language or "en",
                response_language=request.language or "en",
                intent="general",
                confidence=80,
                sources=[],
                needs_escalation=False,
                suggested_questions=[],
            )

    monkeypatch.setattr(
        "app.api.routes.chat.get_chatbot_engine",
        lambda: FakeEngine(),
    )

    response = await client.post(
        "/api/v1/chat/",
        json={"message": "hello", "language": "en"},
    )

    assert response.status_code == 200
    assert response.json()["response"] == "Echo: hello"
