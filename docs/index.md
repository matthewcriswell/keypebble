# Documentation

Welcome to the Keypebble project docs.

Keypebble is a lightweight token-issuing service designed for local, edge, and development environments.  
It provides simple, self-contained JWT issuance without requiring an external identity system — inspired by OpenStack Keystone in concept and SQLite in spirit.

---

## Index

| Topic | Description |
|--------|-------------|
| [Token Profile](token-profile.md) | Defines the structure and meaning of Keypebble-issued JWTs, including registered, public, and private claims. |
| [Architecture Overview](architecture.md) | Explains the internal design: how the Flask app, ClaimBuilder, and token logic interact. |

---

## Key Concepts

- **ClaimBuilder** – Maps HTTP request data into JWT claims.
- **/auth** – Generic endpoint for issuing tokens from arbitrary claim sets.
- **/v2/token** – Prototype Docker-style endpoint that demonstrates scoped authorization tokens.
- **JWT Claims** – The signed “dictionary” of facts asserted by Keypebble about the token holder.

## Development Quick Start

```bash
git clone https://github.com/<yourname>/keypebble
cd keypebble
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
make test
```
