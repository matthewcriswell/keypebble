import uuid
from datetime import datetime


def build_command_claims(
    user: str,
    command: str,
    target: str,
    config: dict,
    now: datetime,
    ttl: int,
    jti_factory=lambda: uuid.uuid4().hex,
) -> dict:
    """Assemble JWT claims for a command token.

    All inputs are explicit parameters — no hidden state or framework dependency.
    ``jti_factory`` is injectable for deterministic testing; defaults to uuid4.
    """
    now_ts = int(now.timestamp())
    return {
        "iss": config.get("issuer", "https://keypebble.local"),
        "aud": target,
        "iat": now_ts,
        "nbf": now_ts,
        "exp": now_ts + ttl,
        "jti": jti_factory(),
        "sub": user,
        "command": command,
    }
