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

```bash
keypebble/
├─ src/
│ └─ keypebble/
│ ├─ init.py
│ ├─ main.py # CLI / Flask entrypoint
│ ├─ app.py # Flask app factory and routes
│ ├─ config.py # YAML config loader
│ ├─ signing.py # JWT signing logic
│ ├─ schemas.py # dataclasses for requests / responses
│ └─ metrics.py # Prometheus RED metrics
├─ example-config.yaml
├─ tests/
│ └─ test_issue.py
├─ pyproject.toml
├─ Dockerfile
├─ README.md
└─ LICENSE
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
keypebble --config example-config.yaml
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
rs256_private_key_path: "/keys/jwt_signing.key"

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

1. Clone and create a virtual environment

    ```bash
    git clone git@github.com:matthewcriswell/keypebble.git
    cd keypebble
    python3.11 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    ```

2. Install in editable mode with dev dependencies

    ```bash
    pip install -e ".[dev]"
    ```
    This:
    * Installs all runtime and developer dependencies
    * Links the src/keypebble package into your environment
    * Exposes the CLI command keypebble

    Run it to verify:
    ```
    keypebble
    # → Hello from Keypebble!
    ```

### Typical development loop

```bash
# Run linters and tests
black src tests && ruff check src tests --fix && pytest -q

# Rebuild distributable artifacts
python -m build

# Test the built wheel
pip install dist/keypebble-0.1.0-py3-none-any.whl
keypebble
```

Your build artifacts are stored under dist/:

```bash
dist/
keypebble-0.1.0.tar.gz
keypebble-0.1.0-py3-none-any.whl
```

### Common cleanup and checks

```bash
# Remove old build artifacts
rm -rf build dist src/*.egg-info

# Validate project metadata
validate-pyproject pyproject.toml

# Sort pyproject.toml keys
toml-sort --in-place pyproject.toml
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