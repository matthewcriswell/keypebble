from pathlib import Path

import yaml

from keypebble.core.policy import Policy


def make_policy(tmp_path: Path, data: dict) -> Path:
    """Helper: write YAML policy file and return its path."""
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(data))
    return path


def test_allowed_access_for_valid_namespace_and_repo(tmp_path):
    """User is allowed pull on repos in their own namespace."""
    policy_data = {
        "users": {
            "alice": {
                "namespace": "alice-space",
                "repos": ["app-api", "app-ui"],
                "actions": ["pull"],
            }
        }
    }
    policy_path = make_policy(tmp_path, policy_data)
    handler = Policy.from_file(str(policy_path))

    scopes = ["repository:registry.example.com/alice-space/app-api:pull"]
    result = handler.allowed_access("alice", scopes)

    assert len(result) == 1
    entry = result[0]
    assert entry["type"] == "repository"
    assert entry["name"].endswith("alice-space/app-api")
    assert entry["actions"] == ["pull"]


def test_denied_if_namespace_does_not_match(tmp_path):
    """Requests outside the user namespace are denied."""
    policy_data = {
        "users": {
            "alice": {
                "namespace": "alice-space",
                "repos": ["app-api"],
                "actions": ["pull"],
            }
        }
    }
    policy_path = make_policy(tmp_path, policy_data)
    handler = Policy.from_file(str(policy_path))

    scopes = ["repository:registry.example.com/bob-space/app-api:pull"]
    result = handler.allowed_access("alice", scopes)
    assert result == []


def test_denied_if_repo_not_listed(tmp_path):
    """Requests for unlisted repositories are denied."""
    policy_data = {
        "users": {
            "alice": {
                "namespace": "alice-space",
                "repos": ["app-ui"],
                "actions": ["pull"],
            }
        }
    }
    policy_path = make_policy(tmp_path, policy_data)
    handler = Policy.from_file(str(policy_path))

    scopes = ["repository:registry.example.com/alice-space/app-api:pull"]
    result = handler.allowed_access("alice", scopes)
    assert result == []


def test_action_is_filtered_to_allowed_set(tmp_path):
    """Only permitted actions are preserved in access list."""
    policy_data = {
        "users": {
            "alice": {
                "namespace": "alice-space",
                "repos": ["app-api"],
                "actions": ["pull"],
            }
        }
    }
    policy_path = make_policy(tmp_path, policy_data)
    handler = Policy.from_file(str(policy_path))

    scopes = ["repository:registry.example.com/alice-space/app-api:pull,push"]
    result = handler.allowed_access("alice", scopes)

    assert len(result) == 1
    assert result[0]["actions"] == ["pull"]


def test_unknown_user_returns_empty_access_list(tmp_path):
    """Unknown users have no permitted access."""
    policy_data = {
        "users": {
            "alice": {
                "namespace": "alice-space",
                "repos": ["app-api"],
                "actions": ["pull"],
            }
        }
    }
    policy_path = make_policy(tmp_path, policy_data)
    handler = Policy.from_file(str(policy_path))

    scopes = ["repository:registry.example.com/alice-space/app-api:pull"]
    result = handler.allowed_access("unknown", scopes)
    assert result == []
