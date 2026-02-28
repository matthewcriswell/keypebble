class ClaimBuilder:
    """Builds a JWT claim dictionary from a mapping definition.

    Each mapping value may be:
      - callable(request) → computed dynamically
      - string with prefix "$.query." or "$.body." → resolved from request
      - any other literal → used as-is

    This follows a simple "triage builder pattern"—classify inputs by kind
    (callable, selector, literal) and handle each deterministically.
    The use of `continue` ensures no accidental overwriting or fall-through
    side effects.

    Duck-type protocol for the ``request`` argument:
      - ``request.args`` — mapping supporting ``.get(key)`` (query parameters)
      - ``request.method`` — string (HTTP verb, e.g. ``"GET"``)
      - ``request.get_json(silent=True)`` — returns parsed JSON body dict or ``None``
    """

    def build(self, request, mapping):
        claims = {}
        for key, ref in mapping.items():
            # 1. Callable → run it
            if callable(ref):
                claims[key] = ref(request)
                continue

            # 2. Strings → interpret special prefixes
            if isinstance(ref, str):
                if ref.startswith("$.query."):
                    claims[key] = request.args.get(ref[len("$.query.") :])
                    continue
                if ref.startswith("$.body."):
                    body = request.get_json(silent=True) or {}
                    claims[key] = body.get(ref[len("$.body.") :])
                    continue

            # 3. Everything else → literal value (int, list, dict, etc.)
            claims[key] = ref

        return claims
