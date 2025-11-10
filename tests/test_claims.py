import pytest
from flask import Flask, request

from keypebble.core.claims import ClaimBuilder


@pytest.fixture
def app():
    app = Flask(__name__)

    @app.route("/test", methods=["GET", "POST"])
    def test_endpoint():
        mapping = {
            "a": "$.query.foo",
            "b": "$.body.bar",
            "c": "static",
        }
        return ClaimBuilder().build(request, mapping)

    return app


def test_claimbuilder_query_and_body(app):
    client = app.test_client()
    resp = client.post("/test?foo=1", json={"bar": 2})
    assert resp.json == {"a": "1", "b": 2, "c": "static"}
