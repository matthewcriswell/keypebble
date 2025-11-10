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
  - **`/auth`** — Issues a JWT based on arbitrary JSON claims provided in the request body.
  - **`/v2/token`** — Issues Docker-style registry tokens using structured claim extraction.
- Created via `create_app(config)` factory for easy testing and configuration injection.

---

### 2. ClaimBuilder (`core/claims.py`)
Responsible for mapping HTTP request data into claim dictionaries.

```python
claims = ClaimBuilder().build(request, mapping)
```

Mapping keys can reference:
- `$.query.*` → query parameters
- `$.body.*` → JSON body fields
- Static string values

This enables endpoints to define declarative claim templates without hardcoding logic.

---

### 3. Token Logic (`core/token.py`)
Handles all JWT creation and decoding.

#### `issue_token(config, claims)`
- Combines provided `claims` with registered ones (`iss`, `iat`, `exp`, etc.).
- Signs the payload using `HS256` and a secret from `config["hs256_secret"]`.

#### `decode_token(config, token)`
- Verifies and decodes JWTs using the same secret.
- Optionally validates the `aud` claim if `config["audience"]` is set.

Together, these functions form Keypebble’s trust boundary — the layer responsible for authenticity and integrity.

---

### 4. Configuration
All configuration is passed as a simple dictionary to `create_app(config)`.

Example:
```python
config = {
    "hs256_secret": "super-secret-key",
    "issuer": "keypebble-local",
    "audience": "docker-registry"
}
```

This approach keeps Keypebble easy to embed or reconfigure for different environments.

---

## Request Flow

```text
Client ──▶ /v2/token ──▶ ClaimBuilder ──▶ issue_token()
        │                     │
        │                     ├── Builds claims from request
        │                     └── Signs payload into JWT
        │
        └─── Receives { "token": "<jwt>", "claims": {...} }
```

Example flow:
1. A client requests `/v2/token?account=tester&scope=repository:demo/payload:pull`
2. `ClaimBuilder` extracts the query params and static values into a claims dict.
3. `issue_token()` signs the claims into a JWT.
4. The service responds with both the encoded token and the raw claims.

---

## Module Relationships

```
core/
 ├── token.py       # issue_token, decode_token
 └── claims.py      # ClaimBuilder

service/
 └── app.py         # Flask app and routes

tests/
 ├── test_claims.py
 ├── test_v2_token.py
 └── test_token_decode.py
```
