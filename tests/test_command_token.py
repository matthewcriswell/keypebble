from datetime import datetime, timezone
from unittest.mock import patch

import jwt

from keypebble import cli
from keypebble.core.command import build_command_claims

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


def _now():
    return datetime.now(timezone.utc)


def _base_config():
    return {"issuer": "https://test-issuer.example.com"}


def _post(client, **overrides):
    body = {
        "user": "operator",
        "target": "edge-node-07",
        "command": "echo hello",
    }
    body.update(overrides)
    return client.post(
        "/command/token",
        json=body,
        content_type="application/json",
    )


# ---------------------------------------------------------------------------
# Layer 1 — Pure function tests for build_command_claims
# ---------------------------------------------------------------------------


def test_build_command_claims_has_all_expected_keys():
    claims = build_command_claims(
        user="alice",
        command="deploy",
        target="edge-01",
        config=_base_config(),
        now=_now(),
        ttl=3600,
    )
    expected = {"iss", "aud", "iat", "nbf", "exp", "jti", "sub", "command"}
    assert set(claims.keys()) == expected


def test_build_command_claims_aud_from_target():
    claims = build_command_claims(
        user="alice",
        command="deploy",
        target="edge-42",
        config={"issuer": "test", "audience": "should-be-ignored"},
        now=_now(),
        ttl=3600,
    )
    assert claims["aud"] == "edge-42"


def test_build_command_claims_sub_from_user():
    claims = build_command_claims(
        user="operator",
        command="deploy",
        target="edge-01",
        config=_base_config(),
        now=_now(),
        ttl=3600,
    )
    assert claims["sub"] == "operator"


def test_build_command_claims_command_verbatim():
    cmd = "apt update && apt upgrade -y"
    claims = build_command_claims(
        user="alice",
        command=cmd,
        target="edge-01",
        config=_base_config(),
        now=_now(),
        ttl=3600,
    )
    assert claims["command"] == cmd


def test_build_command_claims_exp_math():
    fixed_now = datetime(2025, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
    claims = build_command_claims(
        user="alice",
        command="ls",
        target="edge-01",
        config=_base_config(),
        now=fixed_now,
        ttl=900,
    )
    assert claims["exp"] - claims["iat"] == 900


def test_build_command_claims_iss_from_config():
    claims = build_command_claims(
        user="alice",
        command="ls",
        target="edge-01",
        config={"issuer": "https://custom.example.com"},
        now=_now(),
        ttl=3600,
    )
    assert claims["iss"] == "https://custom.example.com"


def test_build_command_claims_iss_default():
    claims = build_command_claims(
        user="alice",
        command="ls",
        target="edge-01",
        config={},
        now=_now(),
        ttl=3600,
    )
    assert claims["iss"] == "https://keypebble.local"


def test_build_command_claims_jti_injectable():
    claims = build_command_claims(
        user="alice",
        command="ls",
        target="edge-01",
        config=_base_config(),
        now=_now(),
        ttl=3600,
        jti_factory=lambda: "fixed-nonce-123",
    )
    assert claims["jti"] == "fixed-nonce-123"


def test_build_command_claims_jti_unique_by_default():
    kwargs = dict(
        user="alice",
        command="ls",
        target="edge-01",
        config=_base_config(),
        now=_now(),
        ttl=3600,
    )
    a = build_command_claims(**kwargs)
    b = build_command_claims(**kwargs)
    assert a["jti"] != b["jti"]


# ---------------------------------------------------------------------------
# Layer 2 — Flask client tests for POST /command/token
# ---------------------------------------------------------------------------


def test_command_token_returns_200(client):
    resp = _post(client)
    assert resp.status_code == 200
    data = resp.get_json()
    assert "token" in data
    assert "jti" in data
    assert "expires_in" in data
    assert "issued_at" in data


def test_command_token_claims_match_request(client, app):
    resp = _post(client, user="operator", target="edge-42", command="whoami")
    assert resp.status_code == 200
    payload = _decode(resp.get_json()["token"], app)
    assert payload["sub"] == "operator"
    assert payload["aud"] == "edge-42"
    assert payload["command"] == "whoami"


def test_command_token_jti_matches_token(client, app):
    resp = _post(client)
    data = resp.get_json()
    payload = _decode(data["token"], app)
    assert data["jti"] == payload["jti"]


def test_command_token_missing_target_returns_400(client):
    resp = client.post(
        "/command/token",
        json={"user": "operator", "command": "echo hi"},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "target" in resp.get_json()["error"]


def test_command_token_missing_command_returns_400(client):
    resp = client.post(
        "/command/token",
        json={"user": "operator", "target": "edge-01"},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "command" in resp.get_json()["error"]


def test_command_token_invalid_body_returns_400(client):
    resp = client.post(
        "/command/token",
        data="not-json",
        content_type="text/plain",
    )
    assert resp.status_code == 400


def test_command_token_user_defaults_to_anonymous(client, app):
    resp = client.post(
        "/command/token",
        json={"target": "edge-01", "command": "echo hi"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    payload = _decode(resp.get_json()["token"], app)
    assert payload["sub"] == "anonymous"


# ---------------------------------------------------------------------------
# Layer 3 — CLI tests for keypebble command
# ---------------------------------------------------------------------------


def test_cli_command_invokes_build_and_issue(tmp_path, capsys):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("issuer: test-issuer\nhs256_secret: s3cret")

    with patch("keypebble.cli.issue_token", return_value="signed-token") as mock_issue:
        args = cli.build_parser().parse_args(
            [
                "command",
                "--config",
                str(cfg_file),
                "--target",
                "edge-07",
                "--command",
                "echo hello",
                "--user",
                "operator",
            ]
        )
        args.func(args)

    mock_issue.assert_called_once()
    claims = mock_issue.call_args[0][1]
    assert claims["aud"] == "edge-07"
    assert claims["command"] == "echo hello"
    assert claims["sub"] == "operator"
    assert "jti" in claims

    captured = capsys.readouterr()
    assert "signed-token" in captured.out


def test_cli_command_user_defaults_to_issuer(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("issuer: my-control-plane\nhs256_secret: s3cret")

    with patch("keypebble.cli.issue_token", return_value="tok"):
        args = cli.build_parser().parse_args(
            [
                "command",
                "--config",
                str(cfg_file),
                "--target",
                "edge-01",
                "--command",
                "ls",
            ]
        )
        args.func(args)

    # build_command_claims was called inside cmd_command; verify via issue_token args
    with patch("keypebble.cli.issue_token", return_value="tok") as mock_issue:
        args.func(args)
    claims = mock_issue.call_args[0][1]
    assert claims["sub"] == "my-control-plane"


def test_cli_command_requires_target(tmp_path):
    """argparse should reject missing --target."""
    import pytest

    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("foo: bar")

    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(
            ["command", "--config", str(cfg_file), "--command", "echo hi"]
        )


def test_cli_command_requires_command_flag(tmp_path):
    """argparse should reject missing --command."""
    import pytest

    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("foo: bar")

    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(
            ["command", "--config", str(cfg_file), "--target", "edge-01"]
        )
