import jwt
import pytest

from keypebble.service.app import create_app

# --- Fixtures ------------------------------------------------------------


@pytest.fixture
def base_config():
    """Minimal config for testing (flat schema)."""
    return {
        "issuer": "https://keypebble.local",
        "audience": "keypebble-edge",
        "default_ttl_seconds": 3600,
        "hs256_secret": "change-me",
        "static_claims": {"scope": "controller:read controller:write"},
    }


@pytest.fixture
def app(base_config):
    """Create a Flask test app."""
    app = create_app(base_config)
    app.testing = True
    return app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


# --- Tests: Health -------------------------------------------------------


def test_healthz_ok(client):
    """GET /healthz returns 200 OK and correct payload."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json == {"status": "ok"}


# --- Tests: Auth ---------------------------------------------------------


def test_auth_returns_valid_jwt(client, base_config):
    """POST /auth should return a valid JWT and claims."""
    payload = {"sub": "edge-001"}
    resp = client.post("/auth", json=payload)
    assert resp.status_code == 200

    data = resp.get_json()
    assert "token" in data
    assert data["claims"] == payload

    decoded = jwt.decode(
        data["token"],
        base_config["hs256_secret"],
        algorithms=["HS256"],
        audience=base_config["audience"],
    )
    # Core claims from your token builder
    assert decoded["sub"] == "edge-001"
    assert decoded["iss"] == base_config["issuer"]
    assert decoded["aud"] == base_config["audience"]
    assert decoded["scope"] == base_config["static_claims"]["scope"]


def test_auth_rejects_malformed_json(client):
    """POST /auth with invalid JSON should return 400."""
    resp = client.post("/auth", data="not-json", content_type="text/plain")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_auth_requires_post(client):
    """GET /auth should not be allowed (405)."""
    resp = client.get("/auth")
    assert resp.status_code == 405
