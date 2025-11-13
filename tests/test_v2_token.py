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


def test_token_with_multiple_query_scopes(client):
    """Supports multiple ?scope= query params."""
    headers = {"X-Authenticated-User": "tester"}
    resp = client.get(
        "/v2/token?service=test-registry"
        "&scope=repository:foo/bar:pull"
        "&scope=repository:foo/baz:pull,push",
        headers=headers,
    )
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["claims"]["access"] == [
        {"type": "repository", "name": "foo/bar", "actions": ["pull"]},
        {"type": "repository", "name": "foo/baz", "actions": ["pull", "push"]},
    ]


def test_token_with_header_scope(client):
    """Supports X-Scopes header (space-delimited)."""
    resp = client.get(
        "/v2/token?service=test-registry",
        headers={
            "X-Authenticated-User": "tester",
            "X-Scopes": "repository:foo/baz:pull,push",
        },
    )
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["claims"]["access"] == [
        {"type": "repository", "name": "foo/baz", "actions": ["pull", "push"]},
    ]


def test_token_with_header_scopes(client):
    """Supports X-Scopes header (space-delimited)."""
    resp = client.get(
        "/v2/token?service=test-registry",
        headers={
            "X-Authenticated-User": "tester",
            "X-Scopes": ("repository:foo/bar:pull " "repository:foo/baz:pull,push"),
        },
    )
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["claims"]["access"] == [
        {"type": "repository", "name": "foo/bar", "actions": ["pull"]},
        {"type": "repository", "name": "foo/baz", "actions": ["pull", "push"]},
    ]


def test_token_with_query_and_header_scopes(client):
    """Merges query and header scopes."""
    resp = client.get(
        "/v2/token?service=test-registry&scope=repository:foo/bar:pull,push",
        headers={
            "X-Authenticated-User": "tester",
            "X-Scopes": "repository:foo/baz:pull",
        },
    )
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["claims"]["access"] == [
        {"type": "repository", "name": "foo/bar", "actions": ["pull", "push"]},
        {"type": "repository", "name": "foo/baz", "actions": ["pull"]},
    ]


def test_token_with_no_scopes(client):
    """Handles missing scope parameters gracefully."""
    headers = {"X-Authenticated-User": "tester"}
    resp = client.get("/v2/token?service=test-registry", headers=headers)
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["claims"]["access"] == []


def test_token_with_multiple_query_scopes_str(client):
    """Ensures multiple ?scope= query params are flattened into a spec-compliant space-delimited string."""
    headers = {"X-Authenticated-User": "tester"}
    resp = client.get(
        "/v2/token?service=test-registry"
        "&scope=repository:foo/bar:pull"
        "&scope=repository:foo/baz:pull,push",
        headers=headers,
    )
    assert resp.status_code == 200

    data = resp.get_json()
    scope_str = data["claims"]["scope"]

    # Verify it's a single string, not a list
    assert isinstance(scope_str, str)

    # Verify both scopes appear correctly in order and separated by a space
    expected = "repository:foo/bar:pull repository:foo/baz:pull,push"
    assert scope_str == expected, f"Unexpected scope string: {scope_str!r}"


def test_v2_token_with_policy_enforcement(client, tmp_path, app):
    """If a policy file is configured, enforce allowed access (mocked)."""
    # Create a mock policy file and attach to app
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text("users: {}")

    # Inject a fake handler into the app for testing
    from keypebble.core.policy import PolicyHandler

    handler = PolicyHandler(policy_path)
    app.policy_handler = handler

    # Patch handler.allowed_access to return a known value
    def fake_allowed_access(user, scopes):
        return [{"type": "repository", "name": "secure/app", "actions": ["pull"]}]

    app.policy_handler.allowed_access = fake_allowed_access

    resp = client.get(
        "/v2/token?service=test-registry&scope=repository:secure/app:pull,push",
        headers={"X-Authenticated-User": "alice"},
    )
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["claims"]["access"] == [
        {"type": "repository", "name": "secure/app", "actions": ["pull"]}
    ]
    # Ensure original scopes were preserved in string
    assert "repository:secure/app:pull,push" in data["claims"]["scope"]


def test_v2_token_policy_generate_mode(client, app):
    """When X-Policy-Generate header is true, access is generated from scopes."""
    headers = {
        "X-Authenticated-User": "bob",
        "X-Policy-Generate": "true",
        "X-Scopes": "repository:demo/app:pull repository:demo/api:pull,push",
    }
    resp = client.get("/v2/token?service=test-registry", headers=headers)
    data = resp.get_json()
    assert resp.status_code == 200
    # Both scopes should appear
    assert data["claims"]["access"] == [
        {"type": "repository", "name": "demo/app", "actions": ["pull"]},
        {"type": "repository", "name": "demo/api", "actions": ["pull", "push"]},
    ]
    assert "repository:demo/app:pull" in data["claims"]["scope"]


def test_v2_token_policy_but_no_scopes(client, tmp_path, app):
    """If a policy exists but no scopes are provided, access should be empty."""
    from keypebble.core.policy import PolicyHandler

    policy_file = tmp_path / "empty_policy.yaml"
    policy_file.write_text("users: {}")
    app.policy_handler = PolicyHandler(policy_file)
    headers = {"X-Authenticated-User": "tester"}
    resp = client.get("/v2/token?service=test-registry", headers=headers)
    data = resp.get_json()
    assert resp.status_code == 200
    assert data["claims"]["access"] == []
    assert data["claims"]["scope"] == ""


def test_v2_token_unknown_user_returns_403(client, tmp_path, app):
    """If the user is not found in the policy, return 403 with an error message."""
    # Create a minimal valid policy file
    policy_path = tmp_path / "policy.yaml"
    policy_path.write_text(
        """
    users:
      alice:
        namespace: "alice-space"
        repos: ["app-api"]
        actions: ["pull"]
    """
    )

    # Attach handler so the app thinks policy is active
    from keypebble.core.policy import PolicyHandler

    app.policy_handler = PolicyHandler(policy_path)
    app.config["POLICY_PATH"] = str(policy_path)

    # Call with an unknown user
    resp = client.get(
        "/v2/token?service=test-registry",
        headers={
            "X-Authenticated-User": "bob",  # not in policy
            "X-Policy-Generate": "true",
        },
    )

    data = resp.get_json()
    assert resp.status_code == 403
    assert data["error"] == "unauthorized"
    assert "not found" in data["message"]
    assert "bob" in data["message"]
