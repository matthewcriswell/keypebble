import time
from pathlib import Path
from typing import Any, Dict

import jwt


def _load_secret(config: dict) -> str:
    """Return HS256 secret from inline config or file path."""
    if "hs256_secret" in config:
        return config["hs256_secret"].strip()
    if "hs256_secret_path" in config:
        return Path(config["hs256_secret_path"]).read_text().strip()
    raise ValueError("Missing hs256_secret or hs256_secret_path in configuration.")


def _load_private_key(config: dict) -> str:
    """Load RSA private key from file."""
    key_path = config.get("rs256_private_key")
    if not key_path:
        raise ValueError("Missing rs256_private_key for RS256 configuration.")
    return Path(key_path).read_text()


def _load_public_key(config: dict) -> str:
    """Load RSA public key from file, or fall back to private key."""
    pub_key_path = config.get("rs256_public_key") or config.get("rs256_private_key")
    if not pub_key_path:
        raise ValueError("Missing rs256_public_key for RS256 verification.")
    return Path(pub_key_path).read_text()


def _load_x5c_chain(config: dict) -> list[str] | None:
    """Optionally load an x5c certificate chain from PEM file."""
    x5c_path = config.get("x5c_chain_path")
    if not x5c_path:
        return None
    text = Path(x5c_path).read_text()
    certs = []
    block = ""
    for line in text.splitlines():
        if "BEGIN CERTIFICATE" in line:
            block = ""
        elif "END CERTIFICATE" in line:
            certs.append(block.replace("\n", ""))
            block = ""
        else:
            block += line.strip()
    return certs or None


def issue_token(config: dict, custom_claims: dict | None = None) -> str:
    """Issue a signed JWT using HS256 or RS256, including optional kid/x5c headers."""
    algorithm = config.get("algorithm", "HS256").upper()
    now = int(time.time())
    ttl = int(config.get("default_ttl_seconds", 3600))

    allowed = config.get("allowed_custom_claims")
    if allowed is not None and custom_claims:
        custom_claims = {k: v for k, v in custom_claims.items() if k in allowed}

    payload = {
        "iss": config.get("issuer", "https://keypebble.local"),
        "aud": config.get("audience", "keypebble-edge"),
        "iat": now,
        "nbf": now,
        "exp": now + ttl,
        **config.get("static_claims", {}),
        **(custom_claims or {}),
    }

    # --- JWT header metadata ---
    headers: Dict[str, Any] = {"typ": "JWT", "alg": algorithm}
    if kid := config.get("key_id"):
        headers["kid"] = kid
    if algorithm == "RS256" and (x5c := _load_x5c_chain(config)):
        headers["x5c"] = x5c

    # --- Signing ---
    if algorithm == "RS256":
        key = _load_private_key(config)
    elif algorithm == "HS256":
        key = _load_secret(config)
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    return jwt.encode(payload, key, algorithm=algorithm, headers=headers)


def decode_token(config: dict, token: str) -> Dict[str, Any]:
    """Decode and verify a JWT using configured secret or public key."""
    algorithm = config.get("algorithm", "HS256").upper()

    if algorithm == "RS256":
        key = _load_public_key(config)
    else:
        key = _load_secret(config)

    try:
        return jwt.decode(
            token,
            key,
            algorithms=[algorithm],
            audience=config.get("audience"),
        )
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}") from e
