# Keypebble — Claude Code Guide

## Development environment

```bash
make setup      # create .venv and install package + dev deps (first-time only)
make test       # run full test suite (pytest -q)
make fmt        # auto-format with Black + Ruff
make lint       # lint only (Ruff)
make check      # run pre-commit on all files
```

All `make` targets use `.venv/bin/` directly — no need to activate the virtualenv first.

## Code style

Formatting and linting are enforced by **Black** and **Ruff** (configured in `pyproject.toml`):

- Line length: **88** (Black default)
- Ruff rule sets: `E` (pycodestyle errors), `F` (Pyflakes), `I` (isort) — `E501` is suppressed (Black owns line length)
- Quote style: double; indent: spaces

**Always run `make fmt test` before committing.** `make fmt` runs Black then Ruff with `--fix`; `make lint` runs Ruff check-only. A mid-file import or unsorted import block will fail CI via the `I` and `E402` rules.

## Running tests

```bash
make test
```

55 tests, all pure Python — no external services required. Tests that exercise Flask routes use `app.test_client()` via the `client` / `app` fixtures in `tests/conftest.py`. The growing set of pure unit tests (for `parse_scopes`, `build_v2_claims`, `allowed_custom_claims`) require neither Flask nor `tmp_path`.

## Project layout

```
src/keypebble/
  __init__.py          # version
  config.py            # load_config() — YAML → dict
  cli.py               # argparse CLI: `keypebble issue` and `keypebble serve`
  main.py              # unified entrypoint
  core/
    __init__.py        # re-exports issue_token
    claims.py          # ClaimBuilder — builds JWT claim dicts from a mapping
    policy.py          # parse_scopes() + Policy class
    token.py           # issue_token() / decode_token()
  service/
    __init__.py
    app.py             # Flask app factory, build_v2_claims(), v2_token route

tests/
  conftest.py          # app / client / config fixtures (Flask test client)
  test_claims_builder.py
  test_scopes.py
  test_policy.py
  test_issue.py
  test_token_decode.py
  test_v2_token.py     # Flask client tests + pure unit tests for build_v2_claims
  test_cli.py
  test_service.py
```

## Key modules

### `core/policy.py`
- **`parse_scopes(scopes: list[str]) -> list[dict]`** — pure function; converts Docker-style scope strings (`"type:name:action1,action2"`) to access dicts. Entries with fewer than 3 colon-separated parts are silently skipped.
- **`Policy`** — unified policy class.
  - `Policy.from_file(path)` — loads YAML once; returns empty `Policy` if file absent.
  - `policy.allowed_access(user, scopes)` — filters requested scopes against the user's policy entry.
  - `policy.generate_for(user)` — generates full claims from policy; raises `ValueError` if user not found.

### `core/token.py`
- **`issue_token(config, custom_claims)`** — signs a JWT (HS256 or RS256). If `allowed_custom_claims` is present in config, custom claims are filtered to that allowlist before the payload is assembled. Standard registered claims (`iss`, `aud`, `iat`, etc.) come from `config` and are never filtered.

### `service/app.py`
- **`build_v2_claims(...) -> dict`** — pure function (no Flask); encapsulates scope resolution, policy dispatch, and claim assembly for the Docker registry token flow.
- **`v2_token`** — thin HTTP adapter: parse headers/args → `build_v2_claims` → catch `ValueError` → `issue_token` → return JSON.
- **`create_app(config, policy_path)`** — Flask application factory.

### `cli.py`
- `keypebble issue` — issues a token directly; supports `--policy` and `--generate`.
- `keypebble serve` — starts the Flask server.
- Imports from `core` only; does not import from `service`.

## Config keys (YAML)

| Key | Description |
|-----|-------------|
| `issuer` | JWT `iss` claim |
| `audience` | JWT `aud` claim |
| `default_ttl_seconds` | Token lifetime (default 3600) |
| `algorithm` | `HS256` or `RS256` |
| `hs256_secret` / `hs256_secret_path` | Secret for HS256 |
| `rs256_private_key` | Path to RSA private key for RS256 |
| `rs256_public_key` | Path to RSA public key (falls back to private key) |
| `x5c_chain_path` | Optional PEM certificate chain for `x5c` header |
| `key_id` | Optional `kid` header |
| `static_claims` | Claims merged into every token |
| `allowed_custom_claims` | Allowlist of permitted custom claim keys; absent = no filtering |
| `service.host` / `service.port` | Bind address for `serve` mode |

## Policy file format

```yaml
users:
  alice:
    namespace: "alice-space"
    repos: ["app-api", "app-ui"]
    actions: ["pull"]
```

Scope format expected by `allowed_access`: `"type:registry/namespace/repo:action1,action2"`

## Conventions

- All imports flow `cli` → `core`; `service` → `core`. `cli` does not import from `service` except for `create_app`.
- New business logic goes in `core/`; Flask glue stays in `service/`.
- Prefer pure functions testable without Flask. Use `app.test_client()` only for HTTP-layer concerns.
- When patching `Policy` in tests: `patch("keypebble.cli.Policy")` and set `mock_class.from_file.return_value = mock_policy`.
- PRs branch from `main`; no force push to `main`.
