from datetime import datetime, timezone

import jwt

from keypebble.service.app import build_ksa_claims

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _decode(token, app):
    return jwt.decode(
        token,
        app.config["hs256_secret"],
        algorithms=["HS256"],
        options={"verify_aud": False},
    )


def _ksa_body(audiences=None, expiration_seconds=None):
    spec = {"audiences": audiences or ["https://kubernetes.default.svc"]}
    if expiration_seconds is not None:
        spec["expirationSeconds"] = expiration_seconds
    return {
        "apiVersion": "authentication.k8s.io/v1",
        "kind": "TokenRequest",
        "spec": spec,
    }


def _post(client, namespace="default", name="my-sa", **kwargs):
    return client.post(
        f"/apis/authentication.k8s.io/v1/namespaces/{namespace}/serviceaccounts/{name}/token",
        json=kwargs.get("body", _ksa_body()),
        content_type="application/json",
    )


# ---------------------------------------------------------------------------
# Flask client tests
# ---------------------------------------------------------------------------


def test_ksa_token_returns_200(client):
    resp = _post(client)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["apiVersion"] == "authentication.k8s.io/v1"
    assert data["kind"] == "TokenRequest"
    assert "token" in data["status"]
    assert "expirationTimestamp" in data["status"]


def test_ksa_token_sub_format(client, app):
    resp = _post(client, namespace="prod", name="worker")
    assert resp.status_code == 200
    payload = _decode(resp.get_json()["status"]["token"], app)
    assert payload["sub"] == "system:serviceaccount:prod:worker"


def test_ksa_token_aud_is_list(client, app):
    body = _ksa_body(
        audiences=["https://kubernetes.default.svc", "https://my-api.example.com"]
    )
    resp = _post(client, body=body)
    assert resp.status_code == 200
    payload = _decode(resp.get_json()["status"]["token"], app)
    assert isinstance(payload["aud"], list)
    assert payload["aud"] == [
        "https://kubernetes.default.svc",
        "https://my-api.example.com",
    ]


def test_ksa_token_expiration_seconds_respected(client, app):
    body = _ksa_body(expiration_seconds=600)
    resp = _post(client, body=body)
    assert resp.status_code == 200
    payload = _decode(resp.get_json()["status"]["token"], app)
    assert payload["exp"] - payload["iat"] == 600


def test_ksa_token_missing_body_returns_400(client):
    resp = client.post(
        "/apis/authentication.k8s.io/v1/namespaces/default/serviceaccounts/my-sa/token",
        data="not-json",
        content_type="text/plain",
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_ksa_token_missing_audiences_returns_400(client):
    body = {
        "apiVersion": "authentication.k8s.io/v1",
        "kind": "TokenRequest",
        "spec": {},
    }
    resp = _post(client, body=body)
    assert resp.status_code == 400
    data = resp.get_json()
    assert "audiences" in data["error"]


def test_ksa_token_kubernetes_io_claim_present(client, app):
    resp = _post(client, namespace="staging", name="api-server")
    assert resp.status_code == 200
    payload = _decode(resp.get_json()["status"]["token"], app)
    k8s = payload.get("kubernetes.io")
    assert k8s is not None
    assert k8s["namespace"] == "staging"
    assert k8s["serviceaccount"]["name"] == "api-server"


def test_ksa_token_expiration_timestamp_format(client):
    resp = _post(client)
    assert resp.status_code == 200
    ts = resp.get_json()["status"]["expirationTimestamp"]
    # Must parse as ISO 8601 UTC
    datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Pure unit tests for build_ksa_claims (no Flask required)
# ---------------------------------------------------------------------------


def _now():
    return datetime.now(timezone.utc)


def _base_config():
    return {"issuer": "https://test-issuer.example.com"}


def test_build_ksa_claims_sub():
    claims = build_ksa_claims(
        namespace="default",
        service_account_name="my-sa",
        audiences=["https://kubernetes.default.svc"],
        config=_base_config(),
        now=_now(),
        ttl=3600,
    )
    assert claims["sub"] == "system:serviceaccount:default:my-sa"


def test_build_ksa_claims_aud_is_list():
    audiences = ["https://kubernetes.default.svc", "https://extra.example.com"]
    claims = build_ksa_claims(
        namespace="default",
        service_account_name="my-sa",
        audiences=audiences,
        config=_base_config(),
        now=_now(),
        ttl=3600,
    )
    assert claims["aud"] == audiences


def test_build_ksa_claims_iss_from_config():
    claims = build_ksa_claims(
        namespace="ns",
        service_account_name="sa",
        audiences=["aud"],
        config={"issuer": "https://custom-issuer.io"},
        now=_now(),
        ttl=3600,
    )
    assert claims["iss"] == "https://custom-issuer.io"


def test_build_ksa_claims_iss_default():
    claims = build_ksa_claims(
        namespace="ns",
        service_account_name="sa",
        audiences=["aud"],
        config={},
        now=_now(),
        ttl=3600,
    )
    assert claims["iss"] == "https://keypebble.local"


def test_build_ksa_claims_exp_math():
    fixed_now = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    claims = build_ksa_claims(
        namespace="ns",
        service_account_name="sa",
        audiences=["aud"],
        config=_base_config(),
        now=fixed_now,
        ttl=7200,
    )
    assert claims["exp"] - claims["iat"] == 7200


def test_build_ksa_claims_kubernetes_io_structure():
    claims = build_ksa_claims(
        namespace="prod",
        service_account_name="controller",
        audiences=["aud"],
        config=_base_config(),
        now=_now(),
        ttl=3600,
    )
    k8s = claims["kubernetes.io"]
    assert k8s["namespace"] == "prod"
    assert k8s["serviceaccount"]["name"] == "controller"


def test_build_ksa_claims_multiple_audiences():
    audiences = ["a", "b", "c"]
    claims = build_ksa_claims(
        namespace="ns",
        service_account_name="sa",
        audiences=audiences,
        config=_base_config(),
        now=_now(),
        ttl=3600,
    )
    assert claims["aud"] == ["a", "b", "c"]
