# Keypebble Token Profile

**Issuer:** `https://keypebble.local`  
**Audience:** Service consuming the token (e.g., Docker registry, edge controller)

This document defines the structure and semantics of JWTs issued by Keypebble.

---

## Registered Claims
| Claim | Type | Description |
|--------|------|-------------|
| `iss` | string | Token issuer |
| `sub` | string | Subject account or service |
| `aud` | string | Intended recipient |
| `exp` | integer | Expiration time (Unix epoch seconds) |
| `iat` | integer | Issued-at time |

---

## Public Claims
| Claim | Type | Description |
|--------|------|-------------|
| `scope` | string | Permission string (e.g., `repository:demo/payload:pull`) |
| `service` | string | Target service name (e.g., `docker-registry`) |

---

## Private Claims
| Claim | Type | Description |
|--------|------|-------------|
| `https://keypebble.io/environment_id` | string | Environment identifier |
| `https://keypebble.io/tenant_id` | string | Internal tenant or customer reference |

---

## Example Payload
```json
{
  "iss": "https://keypebble.local",
  "sub": "tester",
  "aud": "docker-registry",
  "service": "docker-registry",
  "scope": "repository:demo/payload:pull",
  "https://keypebble.io/environment_id": "acme-inc",
  "exp": 1731272237,
  "iat": 1731271937
}

