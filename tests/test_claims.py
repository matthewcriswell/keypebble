import pytest
from flask import Flask, request, jsonify
from keypebble.core.claims import ClaimBuilder


@pytest.fixture
def app():
    app = Flask(__name__)

    @app.route("/test", methods=["GET", "POST"])
    def test_endpoint():
        # A richer mapping that exercises multiple branches.
        mapping = {
            "a": "$.query.foo",
            "b": "$.body.bar",
            "c": "static",
            "d": lambda req: f"method:{req.method.lower()}",
        }
        claims = ClaimBuilder().build(request, mapping)
        return jsonify(claims)

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_claimbuilder_query_and_body(client):
    """Tests extraction from query and body plus static values."""
    resp = client.post("/test?foo=1", json={"bar": 2})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data == {"a": "1", "b": 2, "c": "static", "d": "method:post"}


def test_query_only(client):
    """GET request should still resolve query parameters."""
    resp = client.get("/test?foo=hello")
    data = resp.get_json()
    assert data["a"] == "hello"
    assert data["c"] == "static"
    assert data["d"] == "method:get"
    # body field should be missing (None)
    assert data["b"] is None


def test_body_only(client):
    """POST request with JSON body only."""
    resp = client.post("/test", json={"bar": 99})
    data = resp.get_json()
    assert data["b"] == 99
    assert data["a"] is None


def test_invalid_prefix_is_literal(client):
    """Unknown $.foo. prefix should be passed through as-is."""
    # temporarily override app route for this test
    app = client.application

    @app.route("/invalid", methods=["GET"])
    def invalid():
        mapping = {"x": "$.foo.bar"}
        return jsonify(ClaimBuilder().build(request, mapping))

    resp = client.get("/invalid")
    assert resp.get_json() == {"x": "$.foo.bar"}

