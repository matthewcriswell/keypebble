from pathlib import Path

import jwt
import pytest

from keypebble.core import issue_token


def test_issue_token_basic():
    """A valid config issues a verifiable token."""
    cfg = {
        "issuer": "test-issuer",
        "audience": "test-audience",
        "hs256_secret": "abc123",
        "default_ttl_seconds": 60,
    }
    token = issue_token(cfg, {"sub": "foo"})
    decoded = jwt.decode(
        token, "abc123", algorithms=["HS256"], audience="test-audience"
    )
    assert decoded["sub"] == "foo"
    assert decoded["iss"] == "test-issuer"


def test_missing_secret_raises_valueerror():
    """Config missing secret should raise ValueError."""
    cfg = {"issuer": "x", "audience": "y"}
    with pytest.raises(ValueError):
        issue_token(cfg)


def test_hs256_secret_path_loading(tmp_path: Path):
    """Secret can be loaded from a file instead of inline config."""
    key_file = tmp_path / "secret.key"
    key_file.write_text("abc123")

    cfg = {
        "issuer": "test-issuer",
        "audience": "test-audience",
        "hs256_secret_path": str(key_file),
        "default_ttl_seconds": 60,
    }

    token = issue_token(cfg, {"sub": "bar"})
    decoded = jwt.decode(
        token, "abc123", algorithms=["HS256"], audience="test-audience"
    )
    assert decoded["sub"] == "bar"
    assert decoded["aud"] == "test-audience"


def test_empty_claims_does_not_break():
    """Empty claims should still issue a valid token."""
    cfg = {
        "issuer": "test-issuer",
        "audience": "test-audience",
        "hs256_secret": "abc123",
    }
    token = issue_token(cfg)
    decoded = jwt.decode(
        token, "abc123", algorithms=["HS256"], audience="test-audience"
    )
    assert decoded["iss"] == "test-issuer"


def test_issue_token_registered_claims(config):
    """Verify that issue_token emits RFC 7519-compliant standard claims."""
    # Arrange
    config.update(
        {
            "issuer": "https://keypebble.test",
            "default_ttl_seconds": 120,
            "audience": "example-audience",
        }
    )
    custom_claims = {"sub": "tester"}

    # Act
    token = issue_token(config, custom_claims)
    payload = jwt.decode(
        token, config["_secret"], algorithms=["HS256"], options={"verify_aud": False}
    )  # disable PyJWT audience validation

    # Assert
    # --- Required standard claims ---
    for claim in ["iss", "iat", "exp", "aud"]:
        assert claim in payload

    # --- Correct issuer and TTL math ---
    assert payload["iss"] == "https://keypebble.test"
    assert payload["exp"] - payload["iat"] == 120

    # --- Audience claim should appear if configured ---
    assert payload["aud"] == "example-audience"

    # --- Custom claim should override correctly ---
    assert payload["sub"] == "tester"


def test_allowed_custom_claims_filters_disallowed_keys():
    """Disallowed keys are stripped; allowed keys pass through."""
    cfg = {
        "issuer": "test-issuer",
        "audience": "test-audience",
        "hs256_secret": "abc123",
        "allowed_custom_claims": ["sub", "edge_id"],
    }
    token = issue_token(cfg, {"sub": "alice", "evil": "payload"})
    decoded = jwt.decode(
        token, "abc123", algorithms=["HS256"], audience="test-audience"
    )
    assert decoded["sub"] == "alice"
    assert "evil" not in decoded


def test_allowed_custom_claims_empty_list_strips_all():
    """An empty allowlist removes all custom claims."""
    cfg = {
        "issuer": "test-issuer",
        "audience": "test-audience",
        "hs256_secret": "abc123",
        "allowed_custom_claims": [],
    }
    token = issue_token(cfg, {"sub": "alice", "extra": "value"})
    decoded = jwt.decode(
        token, "abc123", algorithms=["HS256"], audience="test-audience"
    )
    assert "sub" not in decoded
    assert "extra" not in decoded


def test_no_allowed_custom_claims_key_passes_all_through():
    """When allowed_custom_claims is absent, all custom claims are kept."""
    cfg = {
        "issuer": "test-issuer",
        "audience": "test-audience",
        "hs256_secret": "abc123",
    }
    token = issue_token(cfg, {"sub": "alice", "extra": "value"})
    decoded = jwt.decode(
        token, "abc123", algorithms=["HS256"], audience="test-audience"
    )
    assert decoded["sub"] == "alice"
    assert decoded["extra"] == "value"


def test_allowed_custom_claims_with_none_custom_claims():
    """No error when custom_claims is None and an allowlist is configured."""
    cfg = {
        "issuer": "test-issuer",
        "audience": "test-audience",
        "hs256_secret": "abc123",
        "allowed_custom_claims": ["sub"],
    }
    token = issue_token(cfg, None)
    decoded = jwt.decode(
        token, "abc123", algorithms=["HS256"], audience="test-audience"
    )
    assert decoded["iss"] == "test-issuer"
