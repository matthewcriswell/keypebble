# Keypebble

**Keypebble** is a lightweight token issuing service inspired by OpenStack’s Keystone — designed to be the “SQLite of Keystone.”   It provides simple, self-contained authentication token issuance for local, edge, or development environments without requiring an external identity service.

---

## Project Overview
| Area | Decision |
|------|-----------|
| **Language / Runtime** | Python 3.11+ |
| **Framework** | [Flask](https://flask.palletsprojects.com/) for early iterations (may evolve toward Falcon later) |
| **Data Model** | Standard-library [`dataclasses`](https://docs.python.org/3/library/dataclasses.html) — avoiding third-party validation frameworks initially |
| **Config Format** | YAML (`example-config.yaml`) for readability and easy gitops |
| **Token Types** | JWT (initially HS256 / RS256), with long-term goals to explore JWE and Fernet |
| **Packaging** | `pyproject.toml` + setuptools, `src/` layout, wheel/distribution ready |
| **Metrics** | OpenMetrics RED metrics (`Rate`, `Errors`, `Duration`) exposed at `/metrics` |
| **License** | Apache 2.0 — permissive, business-friendly |

---

## Goals
- Simplicity first: Focus on correctness and transparency before performance or complexity.  
- Durability: Stick to well-understood, standard-library primitives wherever possible.  
- Ease of distribution: Installable via `pip install .` or as a minimal Docker image.  
- Security awareness: Follow established JWT best practices (explicit algorithms, issuer/audience validation, short TTLs).  
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

## Acknowledgments
Keypebble draws conceptual inspiration from OpenStack Keystone, but aims to deliver a lightweight, developer-friendly alternative for standalone or embedded use cases.