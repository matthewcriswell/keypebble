from datetime import datetime, timedelta
from pathlib import Path

import jwt


def _load_secret(config: dict) -> str:
    """Return the HS256 secret from inline config or file path."""
    if "hs256_secret" in config:
        return config["hs256_secret"]
    elif "hs256_secret_path" in config:
        return Path(config["hs256_secret_path"]).read_text().strip()
    raise ValueError("Missing hs256_secret or hs256_secret_path in configuration.")


def issue_token(config: dict, custom_claims: dict | None = None) -> str:
    """Issue a signed JWT using HS256."""
    secret = _load_secret(config)
    now = datetime.utcnow()
    ttl = config.get("default_ttl_seconds", 3600)

    payload = {
        "iss": config["issuer"],
        "aud": config["audience"],
        "iat": now,
        "exp": now + timedelta(seconds=ttl),
        **config.get("static_claims", {}),
        **(custom_claims or {}),
    }

    return jwt.encode(payload, secret, algorithm="HS256")
