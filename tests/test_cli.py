# tests/test_cli.py
import json
from unittest.mock import MagicMock, patch

from keypebble import cli


def test_issue_command_invokes_issue_token(tmp_path):
    """Ensure basic issue command calls issue_token with given claims."""
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("foo: bar")

    mock_token = "abc123"
    with patch("keypebble.cli.issue_token", return_value=mock_token) as mock_issue:
        args = cli.build_parser().parse_args(
            [
                "issue",
                "--config",
                str(cfg_file),
                "--claims",
                json.dumps({"sub": "testuser"}),
            ]
        )
        args.func(args)

    mock_issue.assert_called_once()
    assert mock_issue.call_args[0][1]["sub"] == "testuser"


def test_issue_command_applies_policy_if_provided(tmp_path):
    """Ensure that --policy triggers Policy.allowed_access."""
    cfg_file = tmp_path / "config.yaml"
    policy_file = tmp_path / "policy.yaml"
    cfg_file.write_text("foo: bar")
    policy_file.write_text("users: {}")

    mock_token = "token123"
    mock_policy = MagicMock()
    mock_policy.allowed_access.return_value = [
        {"type": "repository", "name": "demo", "actions": ["pull"]}
    ]

    with (
        patch("keypebble.cli.issue_token", return_value=mock_token) as mock_issue,
        patch("keypebble.cli.Policy") as mock_policy_class,
    ):
        mock_policy_class.from_file.return_value = mock_policy
        args = cli.build_parser().parse_args(
            [
                "issue",
                "--config",
                str(cfg_file),
                "--policy",
                str(policy_file),
                "--claims",
                json.dumps(
                    {
                        "sub": "alice",
                        "scope": "repository:registry.example.com/alice-space/app-api:pull,push",
                    }
                ),
            ]
        )
        args.func(args)

    mock_policy_class.from_file.assert_called_once_with(str(policy_file))
    mock_policy.allowed_access.assert_called_once()
    passed_claims = mock_issue.call_args[0][1]
    assert "access" in passed_claims
    assert passed_claims["access"][0]["actions"] == ["pull"]


def test_issue_command_generates_claims_from_policy(tmp_path):
    """Ensure that --generate uses Policy.generate_for."""
    cfg_file = tmp_path / "config.yaml"
    policy_file = tmp_path / "policy.yaml"
    cfg_file.write_text("foo: bar")
    policy_file.write_text("users: {}")

    mock_token = "t123"
    mock_policy = MagicMock()
    mock_policy.generate_for.return_value = {
        "sub": "bob",
        "scope": "repository:bob-space/app-api:pull,push",
        "access": [
            {
                "type": "repository",
                "name": "bob-space/app-api",
                "actions": ["pull", "push"],
            }
        ],
    }

    with (
        patch("keypebble.cli.issue_token", return_value=mock_token) as mock_issue,
        patch("keypebble.cli.Policy") as mock_policy_class,
    ):
        mock_policy_class.from_file.return_value = mock_policy
        args = cli.build_parser().parse_args(
            [
                "issue",
                "--config",
                str(cfg_file),
                "--policy",
                str(policy_file),
                "--claims",
                json.dumps({"sub": "bob"}),
                "--generate",
            ]
        )
        args.func(args)

    mock_policy.generate_for.assert_called_once_with("bob")
    passed_claims = mock_issue.call_args[0][1]
    assert passed_claims["sub"] == "bob"
    assert "access" in passed_claims
    assert "scope" in passed_claims


def test_serve_command_calls_create_app_with_policy(tmp_path):
    """Ensure serve command passes --policy to create_app and starts Flask."""
    cfg_file = tmp_path / "config.yaml"
    policy_file = tmp_path / "policy.yaml"
    cfg_file.write_text("foo: bar")
    policy_file.write_text("users: {}")

    mock_app = MagicMock()
    with patch("keypebble.cli.create_app", return_value=mock_app) as mock_create:
        args = cli.build_parser().parse_args(
            ["serve", "--config", str(cfg_file), "--policy", str(policy_file)]
        )
        args.func(args)

    mock_create.assert_called_once()
    kwargs = mock_create.call_args.kwargs
    assert kwargs["policy_path"] == str(policy_file)
    mock_app.run.assert_called_once()
