from typing import Any, Dict

from flask import Request


class ClaimBuilder:
    """Extracts claims from request data or static strings based on a simple mapping."""

    def build(self, request: Request, mapping: Dict[str, str]) -> Dict[str, Any]:
        claims = {}
        for key, ref in mapping.items():
            if ref.startswith("$.query."):
                param = ref[len("$.query.") :]
                claims[key] = request.args.get(param)
            elif ref.startswith("$.body."):
                body = request.get_json(silent=True) or {}
                field = ref[len("$.body.") :]
                claims[key] = body.get(field)
            else:
                claims[key] = ref
        return claims
