import io
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_settings
from app.core.rate_limit import reset_rate_limits


@pytest.fixture
def client():
    """Returns a fresh TestClient for each test."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Configures test environment credentials and resets rate limits before each test."""
    reset_rate_limits()
    settings = get_settings()
    monkeypatch.setattr(settings, "jwt_secret_key", "test-secret-key-1234567890-test-32bytes-long!!")
    monkeypatch.setattr(settings, "demo_user_username", "testuser@novaretail.com")
    monkeypatch.setattr(settings, "demo_user_password", "UserPass123!")
    monkeypatch.setattr(settings, "demo_admin_username", "testadmin@novaretail.com")
    monkeypatch.setattr(settings, "demo_admin_password", "AdminPass123!")
    monkeypatch.setattr(settings, "chat_rate_limit", 20)
    monkeypatch.setattr(settings, "chat_rate_window_seconds", 3600)
    monkeypatch.setattr(settings, "ingest_rate_limit", 5)
    monkeypatch.setattr(settings, "ingest_rate_window_seconds", 60)


def test_health_public(client):
    """Verify that /api/health is public and unauthenticated."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "service" in data


def test_login_success_user(client):
    """Verify login success for regular user and cookie generation."""
    response = client.post(
        "/api/login",
        json={"username": "testuser@novaretail.com", "password": "UserPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["user"]["username"] == "testuser@novaretail.com"
    assert data["user"]["role"] == "user"
    assert "access_token" in response.cookies


def test_login_success_admin(client):
    """Verify login success for admin user and cookie generation."""
    response = client.post(
        "/api/login",
        json={"username": "testadmin@novaretail.com", "password": "AdminPass123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["user"]["username"] == "testadmin@novaretail.com"
    assert data["user"]["role"] == "admin"
    assert "access_token" in response.cookies


def test_login_failure_invalid_credentials(client):
    """Verify that invalid credentials return 401 Unauthorized."""
    response = client.post(
        "/api/login",
        json={"username": "testuser@novaretail.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]


def test_api_me_unauthenticated(client):
    """Verify that /api/me returns 401 when no auth cookie is present."""
    response = client.get("/api/me")
    assert response.status_code == 401


def test_api_me_authenticated(client):
    """Verify that /api/me returns user profile when logged in."""
    login_resp = client.post(
        "/api/login",
        json={"username": "testuser@novaretail.com", "password": "UserPass123!"},
    )
    assert login_resp.status_code == 200

    me_resp = client.get("/api/me")
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["username"] == "testuser@novaretail.com"
    assert me_data["role"] == "user"


def test_chat_unauthenticated_returns_401(client):
    """Verify that /api/chat requires authentication."""
    response = client.post("/api/chat", json={"question": "What is the leave policy?"})
    assert response.status_code == 401


def test_chat_authenticated_success(client):
    """Verify that /api/chat succeeds for an authenticated user."""
    login_resp = client.post(
        "/api/login",
        json={"username": "testuser@novaretail.com", "password": "UserPass123!"},
    )
    assert login_resp.status_code == 200

    mock_rag_result = {
        "answer": "Full-time employees receive 20 days of annual leave.",
        "source_used": "private_kb",
        "trace": ["Router → KB", "Private KB retrieval → 4 chunks", "KB evidence grade → GOOD", "Answer generation → PRIVATE KB"],
        "citations": [{"title": "company_hr_handbook.md", "url": "", "type": "private_kb"}],
        "current_query": "What is the leave policy?",
    }

    with patch("app.api.routes.ask", return_value=mock_rag_result):
        with patch("app.api.routes.write_audit"):
            chat_resp = client.post(
                "/api/chat",
                json={"question": "What is the leave policy?"},
            )
            assert chat_resp.status_code == 200
            data = chat_resp.json()
            assert data["answer"] == mock_rag_result["answer"]
            assert data["source_used"] == "private_kb"
            assert len(data["trace"]) == 4
            assert data["citations"][0]["title"] == "company_hr_handbook.md"



def test_ingest_unauthenticated_returns_401(client):
    """Verify that /api/ingest returns 401 when called without credentials."""
    file_content = b"# Sample HR Document\nContent here."
    files = {"file": ("test.md", io.BytesIO(file_content), "text/markdown")}
    response = client.post("/api/ingest", files=files)
    assert response.status_code == 401


def test_ingest_forbidden_for_regular_user(client):
    """Verify that /api/ingest returns 403 Forbidden for a non-admin user."""
    login_resp = client.post(
        "/api/login",
        json={"username": "testuser@novaretail.com", "password": "UserPass123!"},
    )
    assert login_resp.status_code == 200

    file_content = b"# Sample HR Document\nContent here."
    files = {"file": ("test.md", io.BytesIO(file_content), "text/markdown")}
    response = client.post("/api/ingest", files=files)
    assert response.status_code == 403
    assert "Admin access required" in response.json()["detail"]


def test_ingest_success_for_admin(client):
    """Verify that /api/ingest succeeds for an admin user."""
    login_resp = client.post(
        "/api/login",
        json={"username": "testadmin@novaretail.com", "password": "AdminPass123!"},
    )
    assert login_resp.status_code == 200

    file_content = b"# Sample Policy\nThis is a new test policy document for testing."
    files = {"file": ("test_policy.md", io.BytesIO(file_content), "text/markdown")}

    with patch("app.api.routes.add_documents", return_value=["vec-id-1", "vec-id-2"]):
        response = client.post("/api/ingest", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Document indexed"
        assert data["file"] == "test_policy.md"
        assert data["ids_created"] == 2


def test_chat_rate_limiting_for_user(client):
    """Verify that normal users are rate-limited to 20 requests/hr on /api/chat."""
    login_resp = client.post(
        "/api/login",
        json={"username": "testuser@novaretail.com", "password": "UserPass123!"},
    )
    assert login_resp.status_code == 200

    mock_rag_result = {
        "answer": "Test answer",
        "source_used": "direct",
        "trace": ["Direct response"],
        "citations": [],
        "current_query": "hello",
    }

    with patch("app.api.routes.ask", return_value=mock_rag_result):
        with patch("app.api.routes.write_audit"):
            # First 20 requests should succeed
            for i in range(20):
                res = client.post(
                    "/api/chat",
                    json={"question": f"Question {i}"},
                )
                assert res.status_code == 200, f"Request {i+1} failed"

            # 21st request must trigger HTTP 429 Too Many Requests
            res_exceeded = client.post(
                "/api/chat",
                json={"question": "Exceeded question"},
            )
            assert res_exceeded.status_code == 429
            assert "Rate limit exceeded" in res_exceeded.json()["detail"]
            assert "Retry-After" in res_exceeded.headers


def test_admin_exempt_from_chat_rate_limiting(client):
    """Verify that admin users are exempt from the 20 requests/hr chat rate limit."""
    login_resp = client.post(
        "/api/login",
        json={"username": "testadmin@novaretail.com", "password": "AdminPass123!"},
    )
    assert login_resp.status_code == 200

    mock_rag_result = {
        "answer": "Admin answer",
        "source_used": "direct",
        "trace": ["Direct response"],
        "citations": [],
        "current_query": "hello",
    }

    with patch("app.api.routes.ask", return_value=mock_rag_result):
        with patch("app.api.routes.write_audit"):
            # Admin can execute 25 requests without hitting a 429
            for i in range(25):
                res = client.post(
                    "/api/chat",
                    json={"question": f"Admin Question {i}"},
                )
                assert res.status_code == 200


def test_ingest_rate_limiting_for_admin(client):
    """Verify that admin users are rate-limited to 5 ingest requests per minute."""
    login_resp = client.post(
        "/api/login",
        json={"username": "testadmin@novaretail.com", "password": "AdminPass123!"},
    )
    assert login_resp.status_code == 200

    file_content = b"# Policy\nContent."
    files = {"file": ("test_ingest.md", io.BytesIO(file_content), "text/markdown")}

    with patch("app.api.routes.add_documents", return_value=["vec-id-1"]):
        # First 5 ingest calls should succeed
        for i in range(5):
            files = {"file": (f"test_{i}.md", io.BytesIO(file_content), "text/markdown")}
            res = client.post("/api/ingest", files=files)
            assert res.status_code == 200

        # 6th ingest call must trigger HTTP 429
        files = {"file": ("test_exceeded.md", io.BytesIO(file_content), "text/markdown")}
        res_exceeded = client.post("/api/ingest", files=files)
        assert res_exceeded.status_code == 429
        assert "Rate limit exceeded" in res_exceeded.json()["detail"]


def test_logout_clears_session(client):
    """Verify that logging out clears the cookie and subsequent requests return 401."""
    login_resp = client.post(
        "/api/login",
        json={"username": "testuser@novaretail.com", "password": "UserPass123!"},
    )
    assert login_resp.status_code == 200

    logout_resp = client.post("/api/logout")
    assert logout_resp.status_code == 200
    assert logout_resp.json()["status"] == "ok"

    me_resp = client.get("/api/me")
    assert me_resp.status_code == 401




def test_root_login_and_logout_endpoints(client):
    """Verify that root /login and /logout endpoints work identical to /api/login and /api/logout."""
    # Test root /login
    login_resp = client.post(
        "/login",
        json={"username": "testuser@novaretail.com", "password": "UserPass123!"},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["status"] == "ok"

    # Verify session via /api/me
    me_resp = client.get("/api/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "testuser@novaretail.com"

    # Test root /logout
    logout_resp = client.post("/logout")
    assert logout_resp.status_code == 200

    # Verify session cleared
    me_after = client.get("/api/me")
    assert me_after.status_code == 401


def test_ingest_unsupported_file_extension(client):
    """Verify that uploading an unsupported file type returns 400 Bad Request."""
    login_resp = client.post(
        "/api/login",
        json={"username": "testadmin@novaretail.com", "password": "AdminPass123!"},
    )
    assert login_resp.status_code == 200

    file_content = b"Binary or invalid content"
    files = {"file": ("malicious_script.exe", io.BytesIO(file_content), "application/octet-stream")}
    response = client.post("/api/ingest", files=files)
    assert response.status_code == 400
    assert "Supported:" in response.json()["detail"]


def test_rag_ingestion_and_chunking():
    """Verify that document loading and text splitting work on sample documents."""
    from pathlib import Path
    from app.services.ingestion import load_file, chunk_documents

    handbook_path = Path("data/sample_kb/company_hr_handbook.md")
    if handbook_path.exists():
        docs = load_file(handbook_path)
        assert len(docs) > 0
        chunks = chunk_documents(docs)
        assert len(chunks) > 0
        for chunk in chunks:
            assert hasattr(chunk, "page_content")
            assert len(chunk.page_content) > 0


def test_settings_quote_sanitization():
    """Verify that Settings strips surrounding double or single quotes from env vars."""
    from app.core.config import Settings
    custom_settings = Settings(
        demo_user_username='"quoted_user@novaretail.com"',
        demo_user_password="'QuotedPass123!'",
        jwt_secret_key='"quoted-jwt-secret-key-12345678901234567890"',
    )
    assert custom_settings.demo_user_username == "quoted_user@novaretail.com"
    assert custom_settings.demo_user_password == "QuotedPass123!"
    assert custom_settings.jwt_secret_key == "quoted-jwt-secret-key-12345678901234567890"

