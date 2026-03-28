from fnmatch import fnmatch
from pathlib import Path

import yaml


def _has_wildcard(pattern: str) -> bool:
    """Return True if pattern contains fnmatch special characters."""
    return any(c in pattern for c in ("*", "?", "["))


def _matches_repo(name: str, pattern: str) -> bool:
    """Check if a repository name matches a policy pattern.

    Supports exact matches and fnmatch-style wildcards (e.g. 'acme/*').
    """
    return fnmatch(name, pattern)


def parse_scopes(scopes: list[str]) -> list[dict]:
    """Convert Docker-style scope strings to access dicts.
    Malformed entries (fewer than 3 colon-separated parts) are skipped.
    """
    result = []
    for scope_str in scopes:
        parts = scope_str.split(":", 2)
        if len(parts) < 3:
            continue
        type_, name, actions_str = parts
        actions = [a.strip() for a in actions_str.split(",") if a.strip()]
        result.append({"type": type_, "name": name, "actions": actions})
    return result


class Policy:
    """Unified policy class for access enforcement and claim generation."""

    def __init__(self, data: dict):
        self.data = data

    @classmethod
    def from_file(cls, path: str) -> "Policy":
        """Load from YAML file. Returns empty Policy if file absent."""
        p = Path(path)
        if not p.exists():
            return cls({})
        with p.open() as f:
            return cls(yaml.safe_load(f) or {})

    def allowed_access(self, user: str, scopes: list[str]) -> list[dict]:
        """Filter requested scopes through the user policy."""
        user_conf = self.data.get("users", {}).get(user)
        if not user_conf:
            return []

        allowed_patterns = user_conf.get("repos", [])
        allowed_actions = set(user_conf.get("actions", []))

        access = []
        for parsed in parse_scopes(scopes):
            repo_name = parsed["name"]
            if any(_matches_repo(repo_name, pat) for pat in allowed_patterns):
                permitted = [a for a in parsed["actions"] if a in allowed_actions]
                if permitted:
                    access.append(
                        {
                            "type": parsed["type"],
                            "name": repo_name,
                            "actions": permitted,
                        }
                    )
        return access

    def generate_for(self, user: str) -> dict:
        """Generate claims for user. Raises ValueError if user not found.
        Wildcard patterns are skipped (cannot enumerate concrete repos).
        """
        users = self.data.get("users", {})
        entry = users.get(user)
        if not entry:
            raise ValueError(f"User '{user}' not found in policy")

        repos = entry.get("repos", [])
        actions = entry.get("actions", [])

        concrete_repos = [r for r in repos if not _has_wildcard(r)]

        access = [
            {"type": "repository", "name": r, "actions": actions}
            for r in concrete_repos
        ]
        scopes = " ".join(f"repository:{r}:{','.join(actions)}" for r in concrete_repos)

        return {"sub": user, "access": access, "scope": scopes}
