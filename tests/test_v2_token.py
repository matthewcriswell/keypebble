import time

import jwt


def _decode(token, app):
    return jwt.decode(
        token,
        app.config["hs256_secret"],
        algorithms=["HS256"],
        options={"verify_aud": False, "verify_sub": False},
    )


def test_v2_token_endpoint(client):
    resp = client.get("/v2/token")
    assert resp.status_code == 401


def test_v2_token_authenticated_user_sets_sub(client, app):
    """When nginx authenticates and sends X-Authenticated-User, sub should match."""
    headers = {"X-Authenticated-User": "tester"}
    resp = client.get("/v2/token?scope=repository:demo/payload:pull", headers=headers)
    assert resp.status_code == 200
    body = resp.get_json()

    payload = _decode(body["token"], app)
    assert payload["sub"] == "tester"
    assert payload["aud"] == app.config.get("audience", "docker-registry")
    assert "repository:demo/payload:pull" in body["claims"]["scope"]


def test_v2_token_missing_user_is_rejected(client):
    """If no authenticated user header is provided, return 401."""
    resp = client.get("/v2/token?scope=repository:demo/payload:pull")
    assert resp.status_code == 401
    data = resp.get_json()
    assert data["error"] == "unauthenticated"
    assert "WWW-Authenticate" in resp.headers


def test_v2_token_includes_registered_claims(client, app):
    """Tokens must include standard registered JWT claims."""
    headers = {"X-Authenticated-User": "tester"}
    resp = client.get("/v2/token?scope=repository:demo/payload:pull", headers=headers)
    assert resp.status_code == 200

    payload = _decode(resp.get_json()["token"], app)
    for claim in ("iss", "aud", "iat", "exp"):
        assert claim in payload
        assert payload[claim] is not None


def test_v2_token_ttl_math(client, app):
    """exp − iat must equal the configured TTL (±1 s)."""
    ttl = app.config.get("default_ttl_seconds", 3600)
    headers = {"X-Authenticated-User": "tester"}

    start = int(time.time())
    token = client.get("/v2/token", headers=headers).get_json()["token"]
    payload = _decode(token, app)

    diff = payload["exp"] - payload["iat"]
    assert abs(diff - ttl) <= 1
    assert abs(payload["iat"] - start) < 5
