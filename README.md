# Keypebble

**Keypebble** is a lightweight token issuing service that provides simple, self-contained authentication for local, edge, and development environments—without requiring an external identity system.

Loosely inspired by OpenStack’s Keystone in practice and by SQLite in spirit, Keypebble aims to help projects start on solid footing with secure, stateless, token-based authorization.

---

## Project Overview
| Area | Decision |
|------|-----------|
| **Language / Runtime** | Python 3.11+ |
| **Framework** | [Flask](https://flask.palletsprojects.com/) for early iterations (may evolve toward [Falcon](https://falcon.readthedocs.io/en/stable/) later) |
| **Data Model** | Standard-library [`dataclasses`](https://docs.python.org/3/library/dataclasses.html) — avoiding third-party frameworks initially |
| **Config Format** | YAML (`example-config.yaml`) for readability and easy gitops |
| **Token Types** | JWT (initially HS256 / RS256), with long-term goals to explore JWE and Fernet |
| **Packaging** | `pyproject.toml` + setuptools, `src/` layout, wheel/distribution ready |
| **Metrics** | OpenMetrics RED metrics (`Rate`, `Errors`, `Duration`) exposed at `/metrics` |
| **License** | Apache 2.0 — permissive, business-friendly |

---

## Goals
- Security: Follow established JWT best practices (explicit algorithms, issuer/audience validation, short TTLs). Focus on correctness and transparency before performance or complexity.
- Simplicity: Be easy to understand and predictable. Stick to well-understood, standard-library primitives wherever possible.
- Ease of distribution: Installable via `pip install .` or as a minimal Docker image.
- Extensibility: Architecture that can later grow to include JWE, Fernet, or persistent backends.
- Observability: Include built-in RED metrics and health checks from the start.

---

## Project Layout

```
keypebble/
├── docs/
│   ├── index.md
│   ├── architecture.md
│   └── token-profile.md
│
├── examples/
│   ├── config.yaml                # example service configuration
│   ├── policy.yaml                # example policy file
│   └── docker-compose/
│
├── src/
│   └── keypebble/
│       ├── __init__.py
│       │
│       ├── cli.py                 # CLI interface (issue / serve)
│       ├── main.py                # unified entrypoint
│       ├── config.py              # YAML config loader
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── claims.py          # ClaimBuilder
│       │   ├── policy.py          # parse_scopes() + Policy class
│       │   └── token.py           # issue_token / decode_token
│       │
│       └── service/
│           ├── __init__.py
│           └── app.py             # Flask app factory, build_v2_claims, routes
│
├── tests/
│   ├── conftest.py
│   ├── test_claims_builder.py
│   ├── test_scopes.py
│   ├── test_policy.py
│   ├── test_cli.py
│   ├── test_issue.py
│   ├── test_service.py
│   ├── test_token_decode.py
│   └── test_v2_token.py
│
├── CLAUDE.md
├── Makefile
├── pyproject.toml
├── README.md
└── LICENSE
```

---

## Packaging & Distribution

Keypebble uses the modern `pyproject.toml` standard and `setuptools` backend.

```bash
# install locally (editable)
pip install -e .

# build wheel / source distribution
python -m build

# run locally
keypebble issue --config examples/example-config.yaml
```

Minimal Docker image:
```
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md LICENSE /app/
COPY src /app/src
RUN pip install --no-cache-dir .
EXPOSE 8080
CMD ["keypebble"]
```

## Example Configuration
```
issuer: "https://keypebble.example/issuer"
audience: "keypebble-edge"
default_ttl_seconds: 14400

# Choose one:
# hs256_secret: "change-me-supersecret"
rs256_private_key: "/keys/jwt_signing.key"

kid: "v1"

static_claims:
  scope: "controller:read controller:write"
  roles: ["controller"]

allowed_custom_claims:
  - sub
  - edge_id
  - scope
  - roles
```
---

## Usage

### Quick start

```bash
# Install
pip install .

# Minimal HS256 config
cat > config.yaml <<EOF
issuer: "example.com"
audience: "example.com"
algorithm: "HS256"
hs256_secret: "change-me"
EOF

# Issue a token
keypebble issue --config config.yaml --claims '{"sub": "alice"}'

# Or run as a service
keypebble serve --config config.yaml
```

---

### CLI

#### keypebble issue

Issues a JWT directly from the command line and prints it to stdout.

| Flag | Required | Description |
|------|----------|-------------|
| `--config PATH` | Yes | Path to YAML config file |
| `--claims JSON` | No | Custom claims as a JSON string |
| `--policy PATH` | No | Path to policy YAML file |
| `--generate` | No | Generate all claims from policy (ignores requested scope) |

User identity is resolved from `sub` or `user` in `--claims`, defaulting to `"unknown"`.

```bash
# Simple token
keypebble issue --config config.yaml --claims '{"sub": "alice"}'

# With scope
keypebble issue --config config.yaml \
  --claims '{"sub": "alice", "scope": "repository:alice-space/app-api:pull"}'

# Policy-filtered scopes (push is stripped if not allowed)
keypebble issue --config config.yaml --policy policy.yaml \
  --claims '{"sub": "alice", "scope": "repository:alice-space/app-api:pull,push"}'

# Generate all claims from policy
keypebble issue --config config.yaml --policy policy.yaml \
  --generate --claims '{"sub": "alice"}'
```

#### keypebble serve

Runs keypebble as an HTTP service.

| Flag | Required | Description |
|------|----------|-------------|
| `--config PATH` | Yes | Path to YAML config file |
| `--policy PATH` | No | Path to policy YAML file (defaults to `/etc/keypebble/policy.yaml`) |

```bash
keypebble serve --config config.yaml --policy policy.yaml
```

Bind address and port are read from `service.host` / `service.port` in the config (defaults: `0.0.0.0:8080`).

---

### HTTP endpoints

#### `GET /healthz`

Readiness check.

```
200 {"status": "ok"}
```

#### `POST /auth`

Issues a JWT for arbitrary claims.

```bash
curl -X POST http://localhost:8080/auth \
  -H "Content-Type: application/json" \
  -d '{"sub": "alice", "role": "admin"}'
```

```json
{"token": "<jwt>", "claims": {"sub": "alice", "role": "admin", ...}}
```

#### `GET /v2/token`

Docker registry token endpoint with optional policy enforcement.

**Request headers:**

| Header | Required | Description |
|--------|----------|-------------|
| `X-Authenticated-User` | Yes | User identity; 401 if absent |
| `X-Policy-Generate` | No | Set to `"true"` to generate claims from policy |
| `X-Scopes` | No | Space-separated scopes (alternative to `?scope=`) |

**Query parameters:**

| Parameter | Description |
|-----------|-------------|
| `service` | Audience override for the issued token |
| `scope` | Requested scope(s); repeatable |

**Scope format:** `type:name:action1,action2` — e.g. `repository:alice-space/app-api:pull`

**Response (200):**

```json
{
  "token": "<jwt>",
  "expires_in": 3600,
  "issued_at": "2025-01-01T00:00:00",
  "claims": {
    "iss": "registry.example.com",
    "aud": "registry.example.com",
    "sub": "alice",
    "access": [{"type": "repository", "name": "alice-space/app-api", "actions": ["pull"]}]
  }
}
```

**Error responses:** `401` (missing user header), `403` (policy violation / user not found)

**Examples:**

```bash
# Token with no scope
curl -H "X-Authenticated-User: alice" \
  "http://localhost:8080/v2/token?service=registry.example.com"

# Token with scope
curl -H "X-Authenticated-User: alice" \
  "http://localhost:8080/v2/token?service=registry.example.com&scope=repository:alice-space/app-api:pull"

# Generate all claims from policy
curl -H "X-Authenticated-User: alice" -H "X-Policy-Generate: true" \
  "http://localhost:8080/v2/token?service=registry.example.com"
```

---

### Policy file

The policy file controls which users can access which repositories and with what actions. Requested scopes are filtered against the policy; `X-Policy-Generate: true` generates the full claim set from the policy without requiring a scope request.

```yaml
users:
  alice:
    namespace: "alice-space"
    repos: ["app-api", "app-ui"]
    actions: ["pull"]
  bob:
    namespace: "bob-space"
    repos: ["app-api"]
    actions: ["pull", "push"]
```

- `namespace` — Docker namespace; incoming scopes are matched as `registry/<namespace>/<repo>`
- `repos` — allowed repository names within the namespace
- `actions` — allowed actions; any actions beyond this list are stripped from the token

See [`examples/policy.yaml`](examples/policy.yaml) for a full example.

---

## Development

Keypebble uses a modern Python packaging layout (pyproject.toml + src/ structure) with an editable install for local development.

### Setup

```bash
git clone git@github.com:matthewcriswell/keypebble.git
cd keypebble
make setup
```

`make setup` creates `.venv/`, upgrades pip, and installs the package in editable mode with all dev dependencies. Run `keypebble` to verify:

```
keypebble
# usage: keypebble [-h] {issue,serve} ...
# keypebble: error: the following arguments are required: command
```

If you prefer to set up manually:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### Typical development loop

Keypebble includes a simple Makefile to standardize common development tasks.

```bash
# Create virtualenv and install dependencies (first time only)
make setup

# Auto-format and lint code
make fmt

# Run linters only
make lint

# Run all tests
make test

# Run full pre-commit suite on all files
make check

# Clean build and cache artifacts
make clean
```

### Code style

Formatting is handled by **Black** (line length 88) and linting by **Ruff** (rules `E`, `F`, `I`; `E501` suppressed). Both are configured in `pyproject.toml`. Always run `make all` before committing — it runs `fmt`, `test`, and `check` (pre-commit) in sequence.

Typical loop before committing:
```bash
make all
git add -A
git commit -m "describe your change"
```

---

## Future Roadmap
* JWE and Fernet token support
* Persistent datastore (SQLite or Postgres)
* Falcon backend for high-performance mode
* Integration tests and OpenAPI spec generation
* GitHub Actions CI / PyPI publishing
* CLI for key rotation and token inspection

## License
Licensed under the Apache License, Version 2.0.
See the LICENSE file.
