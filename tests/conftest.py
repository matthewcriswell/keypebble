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
