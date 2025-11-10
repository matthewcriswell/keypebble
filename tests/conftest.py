# tests/conftest.py
import pytest

from keypebble.service.app import create_app


@pytest.fixture
def app():
    config = {
        "hs256_secret": "test-secret",
        "issuer": "keypebble-test",
        "audience": "keypebble-edge",
    }
    return create_app(config)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def config(app):
    """Expose app.config as a mutable dict for core tests."""
    c = dict(app.config)
    # add a predictable key for _load_secret()
    c["_secret"] = c.get("hs256_secret", "test-secret")
    return c
