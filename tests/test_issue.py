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
