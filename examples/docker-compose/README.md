# Docker Compose Examples

Three standalone compose files for running keypebble with a Docker registry.

| File | Use case |
|------|----------|
| `docker-compose.local.yaml` | Local dev — full stack, mkcert certs, builds from source |
| `docker-compose.dev.yaml` | Dev — keypebble only, HS256, no certs |
| `docker-compose.yaml` | Production — full stack, pre-built image, real certs |

---

## Local development (full stack)

One command sets up certs, demo users, and Docker CA trust:

```bash
./local_setup.sh
```

Then start the stack:

```bash
docker compose -f docker-compose.local.yaml up -d --build
```

Test with the demo users (defined in `examples/policy.yaml`):

```bash
# bob has pull + push access to bob-space/*
docker login registry.localhost -u bob -p bobrules
docker pull alpine:latest
docker tag alpine:latest registry.localhost/bob-space/app-api:test
docker push registry.localhost/bob-space/app-api:test

# alice has pull-only access to alice-space/*
docker login registry.localhost -u alice -p swordfish123
docker pull registry.localhost/bob-space/app-api:test  # denied (not her namespace)
```

Teardown:

```bash
docker compose -f docker-compose.local.yaml down -v
```

### What `local_setup.sh` does

1. Checks for prerequisites (`mkcert`, `htpasswd`, `docker`)
2. Installs the mkcert local CA into your system trust store (`mkcert -install`)
3. Generates a TLS certificate for `registry.localhost`
4. Copies the root CA into `certs/`
5. Creates an htpasswd file with demo users (alice, bob)
6. Configures Docker to trust the local CA:
   - **macOS**: copies to `~/.docker/certs.d/registry.localhost/ca.crt`
   - **Linux**: copies to `/etc/docker/certs.d/registry.localhost/ca.crt` (uses sudo)

The script is idempotent — safe to run multiple times.

---

## Dev mode (keypebble only)

No certs needed. Uses HS256 with a hardcoded dev secret.

```bash
docker compose -f docker-compose.dev.yaml up -d --build
```

Test the token endpoint directly:

```bash
curl http://localhost:8080/healthz

curl -H "X-Authenticated-User: alice" \
  "http://localhost:8080/v2/token?service=registry.example.com&scope=repository:alice-space/app-api:pull"
```

> **Note:** The Docker registry only supports RSA token verification, so HS256 dev mode is
> useful for testing keypebble's token endpoint directly — not for the full registry flow.

---

## Production

Prerequisites:

- `keypebble:latest` image built and available
- TLS certificates at `/etc/keypebble/certs/` (see certificate setup below)
- `config.yaml` and `policy.yaml` at `/etc/keypebble/`
- `htpasswd` file at `/etc/keypebble/certs/htpasswd`

```bash
docker compose up -d
```

The production compose file is the default (`docker-compose.yaml`), so no `-f` flag is needed when running from this directory.

---

## Certificate setup

### Local development (mkcert)

Handled automatically by `local_setup.sh`. See [mkcert](https://github.com/FiloSottile/mkcert) for details.

### Self-signed (production)

Create a root CA:

```bash
openssl genrsa -out rootCA.key 4096
openssl req -x509 -new -nodes -key rootCA.key \
  -sha256 -days 3650 \
  -subj "/C=US/ST=Texas/L=Austin/O=Keypebble Root CA/CN=Keypebble Root CA" \
  -out rootCA.pem
```

Create a server certificate:

```bash
openssl genrsa -out keypebble-private.pem 4096

openssl req -new -key keypebble-private.pem \
  -subj "/C=US/ST=Texas/L=Austin/O=Example/CN=registry.example.com" \
  -out keypebble.csr

cat > san.cnf <<EOF
subjectAltName = @alt_names
[alt_names]
DNS.1 = registry.example.com
EOF

openssl x509 -req -in keypebble.csr \
  -CA rootCA.pem -CAkey rootCA.key -CAcreateserial \
  -out keypebble-cert.pem -days 825 -sha256 \
  -extfile san.cnf
```

Combine into a chain bundle (used by nginx and the x5c JWT header):

```bash
cat keypebble-cert.pem rootCA.pem > keypebble-chain.pem
```

Copy to `/etc/keypebble/certs/`:

```
/etc/keypebble/
  certs/
    keypebble-private.pem   # RSA private key
    keypebble-chain.pem     # cert + CA chain (for nginx fullchain + x5c)
    rootCA.pem              # root CA (for registry ROOTCERTBUNDLE)
    htpasswd                # basic auth users
  config.yaml
  policy.yaml
```

### Let's Encrypt (production)

```bash
# Install acme.sh
curl https://get.acme.sh | sh
~/.acme.sh/acme.sh --set-default-ca --server letsencrypt

# Issue cert
~/.acme.sh/acme.sh --issue -d registry.example.com -w /var/www/html --keylength 4096

# Install to /etc/keypebble
~/.acme.sh/acme.sh --install-cert -d registry.example.com \
  --key-file       /etc/keypebble/certs/keypebble-private.pem  \
  --fullchain-file /etc/keypebble/certs/keypebble-chain.pem    \
  --reloadcmd      "docker compose restart nginx keypebble"
```
