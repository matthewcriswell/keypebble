"""Unit tests for keypebble.core.claims.ClaimBuilder"""

from types import SimpleNamespace

from keypebble.core.claims import ClaimBuilder


def make_request(query=None, body=None, method="GET"):
    """Return a minimal dummy request-like object."""
    return SimpleNamespace(
        args=query or {},
        method=method,
        get_json=lambda silent=True: body or {},
    )


def test_static_and_literal_values():
    builder = ClaimBuilder()
    mapping = {"service": "docker-registry", "count": 3}
    claims = builder.build(make_request(), mapping)
    assert claims == {"service": "docker-registry", "count": 3}


def test_query_parameter_resolution():
    builder = ClaimBuilder()
    mapping = {"user": "$.query.account"}
    req = make_request(query={"account": "tester"})
    claims = builder.build(req, mapping)
    assert claims == {"user": "tester"}


def test_body_field_resolution():
    builder = ClaimBuilder()
    mapping = {"sub": "$.body.username"}
    req = make_request(body={"username": "alice"})
    claims = builder.build(req, mapping)
    assert claims == {"sub": "alice"}


def test_callable_resolution():
    builder = ClaimBuilder()
    mapping = {"custom": lambda req: f"method:{req.method.lower()}"}
    claims = builder.build(make_request(method="POST"), mapping)
    assert claims["custom"] == "method:post"


def test_mixed_types_together():
    builder = ClaimBuilder()
    mapping = {
        "service": "docker-registry",
        "sub": "$.query.account",
        "body_field": "$.body.value",
        "computed": lambda req: req.args.get("x", "missing"),
    }
    req = make_request(
        query={"account": "user123", "x": "42"}, body={"value": "from-body"}
    )
    claims = builder.build(req, mapping)
    assert claims == {
        "service": "docker-registry",
        "sub": "user123",
        "body_field": "from-body",
        "computed": "42",
    }


def test_literal_structures_preserved():
    builder = ClaimBuilder()
    mapping = {
        "access": [{"type": "repository", "name": "demo", "actions": ["pull"]}],
    }
    claims = builder.build(make_request(), mapping)
    assert isinstance(claims["access"], list)
    assert claims["access"][0]["name"] == "demo"


def test_unmatched_prefix_is_treated_as_literal():
    builder = ClaimBuilder()
    mapping = {"foo": "$.unknown.value"}
    claims = builder.build(make_request(), mapping)
    # no prefix handler matched → treated literally
    assert claims["foo"] == "$.unknown.value"
