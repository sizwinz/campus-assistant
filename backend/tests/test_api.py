"""
Tests for API endpoints.
"""

import pytest
from httpx import AsyncClient


class TestHealthEndpoint:
    """Tests for health check endpoints."""

    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint returns API info."""
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "running"

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        """Test health endpoint returns healthy status."""
        response = await client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestAdminAuth:
    """Tests for admin authentication."""

    @pytest.mark.asyncio
    async def test_admin_dashboard_requires_auth(self, client: AsyncClient):
        """Test admin dashboard requires authentication."""
        response = await client.get("/api/v1/admin/dashboard")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_dashboard_with_valid_auth(
        self, client: AsyncClient, admin_auth_header: dict
    ):
        """Test admin dashboard with valid credentials."""
        response = await client.get(
            "/api/v1/admin/dashboard",
            headers=admin_auth_header,
        )

        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "messages" in data

    @pytest.mark.asyncio
    async def test_admin_dashboard_with_invalid_auth(self, client: AsyncClient):
        """Test admin dashboard rejects invalid credentials."""
        import base64
        wrong_creds = base64.b64encode(b"admin:wrong-password").decode("utf-8")
        headers = {"Authorization": f"Basic {wrong_creds}"}

        response = await client.get(
            "/api/v1/admin/dashboard",
            headers=headers,
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_health_no_auth_required(self, client: AsyncClient):
        """Test admin health check does not require auth."""
        response = await client.get("/api/v1/admin/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data


class TestChatEndpoint:
    """Tests for chat endpoints."""

    @pytest.mark.asyncio
    async def test_chat_welcome_endpoint(self, client: AsyncClient):
        """Test welcome message endpoint."""
        response = await client.get("/api/v1/chat/welcome")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_chat_languages_endpoint(self, client: AsyncClient):
        """Test supported languages endpoint."""
        response = await client.get("/api/v1/chat/languages")

        assert response.status_code == 200
        data = response.json()
        assert "languages" in data
        assert "en" in data["languages"]


class TestFAQEndpoint:
    """Tests for FAQ endpoints."""

    @pytest.mark.asyncio
    async def test_list_faqs(self, client: AsyncClient):
        """Test listing FAQs."""
        response = await client.get("/api/v1/faqs/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_create_faq(
        self,
        client: AsyncClient,
        sample_faq_data: dict,
        admin_auth_header: dict,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Test creating a new FAQ."""
        class FakeProcessor:
            async def process_faq(self, **kwargs):
                return [object()]

        class FakeVectorStore:
            async def add_documents(self, chunks):
                return len(chunks)

        monkeypatch.setattr(
            "app.services.faq_service.get_document_processor",
            lambda: FakeProcessor(),
        )
        monkeypatch.setattr(
            "app.services.faq_service.get_vector_store",
            lambda: FakeVectorStore(),
        )

        response = await client.post(
            "/api/v1/faqs/",
            json=sample_faq_data,
            headers=admin_auth_header,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["question"] == sample_faq_data["question"]
        assert data["answer"] == sample_faq_data["answer"]
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_faq_validation(self, client: AsyncClient):
        """Test FAQ creation requires admin auth before payload validation."""
        response = await client.post(
            "/api/v1/faqs/",
            json={"question": "Only question, no answer"},
        )

        assert response.status_code == 401
