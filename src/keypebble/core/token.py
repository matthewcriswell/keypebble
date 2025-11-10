import time
from pathlib import Path
from typing import Any, Dict

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
    now = int(time.time())
    ttl = config.get("default_ttl_seconds", 3600)

    payload = {
        "iss": config.get("issuer", "https://keypebble.local"),
        "aud": config.get("audience", "keypebble-edge"),
        "iat": now,
        "nbf": now,
        "exp": now + ttl,
        **config.get("static_claims", {}),
        **(custom_claims or {}),
    }

    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(config: dict, token: str) -> Dict[str, Any]:
    """Decode and verify a JWT using the configured secret."""
    secret = config.get("hs256_secret")
    if not secret:
        raise ValueError("Missing hs256_secret in configuration.")

    try:
        payload = jwt.decode(
            token, secret, algorithms=["HS256"], audience=config.get("audience")
        )
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}") from e
    return payload
