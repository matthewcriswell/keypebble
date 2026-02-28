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

Typical loop before committing:
```bash
make fmt test
git add -A
git commit -m "describe your change"
```

You can also run all checks at once:
```bash
make check
```
These commands ensure consistent formatting (via Black), linting (via Ruff), and test coverage (pytest) before each commit.

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
