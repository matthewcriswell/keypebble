"""Pure unit tests for keypebble.core.policy.parse_scopes"""

from keypebble.core.policy import parse_scopes


def test_single_scope():
    result = parse_scopes(["repository:foo/bar:pull"])
    assert result == [{"type": "repository", "name": "foo/bar", "actions": ["pull"]}]


def test_multiple_scopes():
    result = parse_scopes(
        ["repository:foo/bar:pull", "repository:foo/baz:pull,push"]
    )
    assert result == [
        {"type": "repository", "name": "foo/bar", "actions": ["pull"]},
        {"type": "repository", "name": "foo/baz", "actions": ["pull", "push"]},
    ]


def test_empty_list():
    assert parse_scopes([]) == []


def test_malformed_scope_skipped():
    """Entries with fewer than 3 colon-separated parts are dropped."""
    result = parse_scopes(["repository:foo/bar", "repository:foo/baz:pull"])
    assert result == [{"type": "repository", "name": "foo/baz", "actions": ["pull"]}]


def test_comma_separated_actions_split():
    result = parse_scopes(["repository:ns/repo:pull,push,delete"])
    assert result == [
        {
            "type": "repository",
            "name": "ns/repo",
            "actions": ["pull", "push", "delete"],
        }
    ]


def test_actions_whitespace_stripped():
    result = parse_scopes(["repository:ns/repo:pull, push"])
    assert result == [
        {"type": "repository", "name": "ns/repo", "actions": ["pull", "push"]}
    ]
