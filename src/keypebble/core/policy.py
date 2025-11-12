from pathlib import Path
from typing import Dict, List

import yaml


class PolicyHandler:
    """Minimal policy reader and enforcer."""

    def __init__(self, path: str = "/etc/keypebble/policy.yaml"):
        self.path = Path(path)

    def _load(self) -> Dict:
        """Always load the policy file fresh."""
        if not self.path.exists():
            return {}
        with self.path.open() as f:
            return yaml.safe_load(f) or {}

    def allowed_access(self, user: str, scopes: List[str]) -> List[Dict]:
        """Filter requested scopes through the user policy."""
        policy = self._load()
        user_conf = policy.get("users", {}).get(user)
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


class PolicyGenerator:
    """Generate claims from a simple static policy file."""

    def __init__(self, policy_path: str):
        with open(policy_path, "r") as f:
            self.policy = yaml.safe_load(f)

    def generate_claims_for(self, user: str) -> dict:
        users = self.policy.get("users", {})
        entry = users.get(user)
        if not entry:
            raise ValueError(f"User '{user}' not found in policy")

        namespace = entry.get("namespace")
        repos = entry.get("repos", [])
        actions = entry.get("actions", [])

        # Build access entries
        access = [
            {"type": "repository", "name": f"{namespace}/{r}", "actions": actions}
            for r in repos
        ]

        # Build Docker-style scope string
        scopes = " ".join(
            f"repository:{namespace}/{r}:{','.join(actions)}" for r in repos
        )

        return {"sub": user, "access": access, "scope": scopes}
