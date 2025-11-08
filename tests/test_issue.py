import jwt
from keypebble.core import issue_token


def test_issue_token_basic():
    cfg = {
        "issuer": "test-issuer",
        "audience": "test-audience",
        "hs256_secret": "abc123",
        "default_ttl_seconds": 60,
    }
    token = issue_token(cfg, {"sub": "foo"})
    decoded = jwt.decode(token, "abc123", algorithms=["HS256"], audience="test-audience")
    assert decoded["sub"] == "foo"
    assert decoded["iss"] == "test-issuer"
