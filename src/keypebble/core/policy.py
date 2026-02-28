from pathlib import Path

import yaml


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

        namespace = user_conf.get("namespace")
        allowed_repos = set(user_conf.get("repos", []))
        allowed_actions = set(user_conf.get("actions", []))

        access = []
        for scope in scopes:
            parts = scope.split(":", 2)
            if len(parts) != 3:
                continue

            type_, name, actions_str = parts
            actions = [a.strip() for a in actions_str.split(",") if a.strip()]

            # Expected form: registry/namespace/repo
            name_parts = name.split("/", 2)
            if len(name_parts) < 3:
                continue

            _, ns, repo = name_parts

            if ns == namespace and repo in allowed_repos:
                permitted = [a for a in actions if a in allowed_actions]
                if permitted:
                    access.append({"type": type_, "name": name, "actions": permitted})
        return access

    def generate_for(self, user: str) -> dict:
        """Generate claims for user. Raises ValueError if user not found."""
        users = self.data.get("users", {})
        entry = users.get(user)
        if not entry:
            raise ValueError(f"User '{user}' not found in policy")

        namespace = entry.get("namespace")
        repos = entry.get("repos", [])
        actions = entry.get("actions", [])

        access = [
            {"type": "repository", "name": f"{namespace}/{r}", "actions": actions}
            for r in repos
        ]
        scopes = " ".join(
            f"repository:{namespace}/{r}:{','.join(actions)}" for r in repos
        )

        return {"sub": user, "access": access, "scope": scopes}
