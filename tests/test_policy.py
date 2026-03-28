import pytest
import yaml

from keypebble.core.policy import Policy, _has_wildcard, _matches_repo

# ---------------------------------------------------------------------------
# _has_wildcard / _matches_repo helpers
# ---------------------------------------------------------------------------


def test_has_wildcard_star():
    assert _has_wildcard("acme/*") is True


def test_has_wildcard_question():
    assert _has_wildcard("acme/service-?") is True


def test_has_wildcard_bracket():
    assert _has_wildcard("acme/service-[ab]") is True


def test_has_wildcard_literal():
    assert _has_wildcard("acme/service-a") is False


def test_matches_repo_exact():
    assert _matches_repo("acme/service-a", "acme/service-a") is True


def test_matches_repo_wildcard():
    assert _matches_repo("acme/service-a", "acme/*") is True


def test_matches_repo_wildcard_deep():
    assert _matches_repo("acme/team/service-a", "acme/*") is True


def test_matches_repo_no_match():
    assert _matches_repo("other/thing", "acme/*") is False


def test_matches_repo_single_segment():
    assert _matches_repo("helm", "helm") is True


def test_matches_repo_single_segment_no_match():
    assert _matches_repo("helm", "nginx") is False


# ---------------------------------------------------------------------------
# allowed_access
# ---------------------------------------------------------------------------


def _policy(users: dict) -> Policy:
    return Policy({"users": users})


def test_exact_match_two_segments():
    policy = _policy({"alice": {"repos": ["acme/service-a"], "actions": ["pull"]}})
    result = policy.allowed_access("alice", ["repository:acme/service-a:pull"])
    assert result == [
        {"type": "repository", "name": "acme/service-a", "actions": ["pull"]}
    ]


def test_exact_match_single_segment():
    policy = _policy({"alice": {"repos": ["helm"], "actions": ["pull"]}})
    result = policy.allowed_access("alice", ["repository:helm:pull"])
    assert result == [{"type": "repository", "name": "helm", "actions": ["pull"]}]


def test_wildcard_match():
    policy = _policy({"alice": {"repos": ["acme/*"], "actions": ["pull"]}})
    result = policy.allowed_access("alice", ["repository:acme/service-a:pull"])
    assert result == [
        {"type": "repository", "name": "acme/service-a", "actions": ["pull"]}
    ]


def test_wildcard_no_overmatch():
    policy = _policy({"alice": {"repos": ["acme/*"], "actions": ["pull"]}})
    result = policy.allowed_access("alice", ["repository:other/thing:pull"])
    assert result == []


def test_action_filtering():
    policy = _policy({"alice": {"repos": ["acme/service-a"], "actions": ["pull"]}})
    result = policy.allowed_access("alice", ["repository:acme/service-a:pull,push"])
    assert len(result) == 1
    assert result[0]["actions"] == ["pull"]


def test_unknown_user_returns_empty():
    policy = _policy({"alice": {"repos": ["acme/service-a"], "actions": ["pull"]}})
    result = policy.allowed_access("unknown", ["repository:acme/service-a:pull"])
    assert result == []


def test_repo_not_matched():
    policy = _policy({"alice": {"repos": ["acme/service-a"], "actions": ["pull"]}})
    result = policy.allowed_access("alice", ["repository:acme/service-b:pull"])
    assert result == []


def test_multiple_scopes():
    policy = _policy(
        {
            "alice": {
                "repos": ["helm", "acme/*"],
                "actions": ["pull"],
            }
        }
    )
    result = policy.allowed_access(
        "alice",
        ["repository:helm:pull", "repository:acme/service-a:pull"],
    )
    assert len(result) == 2
    assert result[0]["name"] == "helm"
    assert result[1]["name"] == "acme/service-a"


# ---------------------------------------------------------------------------
# generate_for
# ---------------------------------------------------------------------------


def test_generate_for_flat_repos():
    policy = _policy(
        {
            "alice": {
                "repos": ["helm", "acme/service-a"],
                "actions": ["pull"],
            }
        }
    )
    result = policy.generate_for("alice")
    assert result["sub"] == "alice"
    assert result["access"] == [
        {"type": "repository", "name": "helm", "actions": ["pull"]},
        {"type": "repository", "name": "acme/service-a", "actions": ["pull"]},
    ]
    assert "repository:helm:pull" in result["scope"]
    assert "repository:acme/service-a:pull" in result["scope"]


def test_generate_for_skips_wildcards():
    policy = _policy(
        {
            "alice": {
                "repos": ["acme/*", "helm"],
                "actions": ["pull"],
            }
        }
    )
    result = policy.generate_for("alice")
    assert len(result["access"]) == 1
    assert result["access"][0]["name"] == "helm"
    assert "acme" not in result["scope"]


def test_generate_for_unknown_user_raises():
    policy = _policy({"alice": {"repos": ["helm"], "actions": ["pull"]}})
    with pytest.raises(ValueError, match="not found"):
        policy.generate_for("unknown")


# ---------------------------------------------------------------------------
# from_file
# ---------------------------------------------------------------------------


def test_from_file_loads_yaml(tmp_path):
    path = tmp_path / "policy.yaml"
    path.write_text(
        yaml.safe_dump({"users": {"alice": {"repos": ["helm"], "actions": ["pull"]}}})
    )
    policy = Policy.from_file(str(path))
    result = policy.allowed_access("alice", ["repository:helm:pull"])
    assert len(result) == 1


def test_from_file_missing_returns_empty(tmp_path):
    policy = Policy.from_file(str(tmp_path / "nonexistent.yaml"))
    assert policy.allowed_access("anyone", ["repository:foo:pull"]) == []
