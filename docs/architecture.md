# Keypebble Architecture Overview

Keypebble is a lightweight token-issuing service designed for local, edge, and development environments.
It exposes a simple REST API that maps request data into cryptographically signed tokens.

---

##  Core Components

### 1. Flask Application (`service/app.py`)
The entry point of the Keypebble service.

- Defines the HTTP API using a single `Blueprint` (`bp`).
- Provides endpoints:
  - **`/healthz`** — Readiness probe returning `{"status": "ok"}`.
  - **`/auth`** — Issues a JWT from arbitrary JSON claims provided in the request body.
  - **`/v2/token`** — Issues Docker-style registry tokens using structured claim extraction via `ClaimBuilder`.
- Created via `create_app(config)` factory for easy testing and configuration injection.

Example:
```python
@bp.route("/v2/token", methods=["GET"])
def v2_token():
    mapping = {
        "service": "docker-registry",
        "scope": "$.query.scope",
        "sub": "$.query.account",
        "access": lambda req: build_access_claim(req.args.get("scope")),
    }
    claims = ClaimBuilder().build(request, mapping)
    token = issue_token(current_app.config, claims)
    return jsonify({"token": token, "claims": claims}), 200
```

---

### 2. ClaimBuilder (`core/claims.py`)
Responsible for mapping HTTP request data, static values, and computed expressions into structured claim dictionaries.

```python
claims = ClaimBuilder().build(request, mapping)
```

Each mapping entry defines how a single claim is resolved:

| Type | Example | Description |
|------|----------|-------------|
| **Query selector** | `"$.query.account"` | Reads from `request.args["account"]` |
| **Body selector** | `"$.body.username"` | Reads from JSON body field `"username"` |
| **Static literal** | `"docker-registry"` | Inserts the value directly |
| **Callable** | `lambda req: {...}` | Computes structured or dynamic claims |

This flexible design follows a simple **“triage builder” pattern**:
1. Classify each mapping value by kind (callable → selector → literal).  
2. Handle it deterministically with no fall-through or overwriting.

#### Example: Dynamic `access` claim
```python
def build_access_claim(scope_str):
    type_, name, actions = scope_str.split(":", 2)
    return [{"type": type_, "name": name, "actions": actions.split(",")}]
```

---

### 3. Token Logic (`core/token.py`)
Handles all JWT creation and decoding.

#### `issue_token(config, claims)`
- Merges provided claims with registered ones (`iss`, `aud`, `iat`, `exp`, etc.).
- Signs the payload using **HS256** and a secret loaded from configuration.

#### `decode_token(config, token)`
- Verifies and decodes JWTs using the same secret.
- Validates audience if `config["audience"]` is set.

Together, these functions form Keypebble’s **trust boundary** — the layer ensuring token authenticity and integrity.

---

### 4. Configuration
All configuration is passed as a simple dictionary to `create_app(config)`.

Example:
```python
config = {
    "hs256_secret": "super-secret-key",
    "issuer": "https://keypebble.local",
    "audience": "keypebble-edge",
}
```

This keeps Keypebble lightweight, portable, and easy to embed or reconfigure.

---

## Request Flow

```text
Client ──▶ /v2/token ──▶ ClaimBuilder ──▶ issue_token()
        │                     │
        │                     ├── Builds structured claims
        │                     └── Signs payload into JWT
        │
        └─── Receives { "token": "<jwt>", "claims": {...} }
```

Example flow:
1. Client requests  
   `/v2/token?account=tester&scope=repository:demo/payload:pull`
2. `ClaimBuilder` extracts query params and static values into a claims dict,  
   including an `access` list built from the `scope` string.
3. `issue_token()` signs the claims into a JWT.
4. The service responds with both the encoded token and raw claims.

Resulting claim payload:
```json
{
  "service": "docker-registry",
  "scope": "repository:demo/payload:pull",
  "sub": "tester",
  "access": [
    {
      "type": "repository",
      "name": "demo/payload",
      "actions": ["pull"]
    }
  ]
}
```

---

## Module Relationships

```
core/
 ├── claims.py       # ClaimBuilder for dynamic claim extraction
 └── token.py        # issue_token and decode_token

service/
 └── app.py          # Flask app and HTTP endpoints

tests/
 ├── test_claims.py          # Integration tests for request mapping
 ├── test_claims_builder.py  # Unit tests for ClaimBuilder logic
 ├── test_v2_token.py        # End-to-end /v2/token verification
 ├── test_token_decode.py    # Round-trip encode/decode
 └── test_issue.py           # Token issuance edge cases
```

