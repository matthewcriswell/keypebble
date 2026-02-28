## Usage

The compose setup uses a base file for shared infrastructure plus individual service files layered in via `-f`.

### Production (RS256, full stack)

Requires certificates — see the cert setup sections below.

```bash
docker compose \
  -f examples/docker-compose/docker-compose.yaml \
  -f examples/docker-compose/keypebble.yaml \
  -f examples/docker-compose/nginx.yaml \
  -f examples/docker-compose/registry.yaml \
  up -d
```

### Dev (HS256, keypebble only — no certs needed)

Uses `examples/config.dev.yaml` (HS256, `dev-only-secret`). No nginx or registry required.

```bash
docker compose \
  -f examples/docker-compose/docker-compose.yaml \
  -f examples/docker-compose/keypebble.yaml \
  -f examples/docker-compose/docker-compose.dev.yaml \
  up -d
```

Test the token endpoint:

```bash
# Health check
curl http://localhost:8080/healthz

# Token request (no scope)
curl -H "X-Authenticated-User: alice" \
  "http://localhost:8080/v2/token?service=registry.example.com"

# Token request with scope
curl -H "X-Authenticated-User: alice" \
  "http://localhost:8080/v2/token?service=registry.example.com&scope=repository:alice-space/app-api:pull"
```

> **Note:** The Docker registry only supports RSA token verification, so HS256 dev mode is useful
> for testing keypebble's token endpoint directly. For the full registry flow, use the production
> stack with RS256 certificates.

---

## How to make a selfsigned cert

### Create a Root Certificate Authority
1. Generate root CA key
```bash
openssl genrsa -out rootCA.key 4096
```

2. Self-sign the CA certificate (valid 10 years)
```bash
openssl req -x509 -new -nodes -key rootCA.key \
  -sha256 -days 3650 \
  -subj "/C=US/ST=Texas/L=Austin/O=Keypebble Root CA/CN=Keypebble Root CA" \
  -out rootCA.pem
```

### Create a Server Key and CSR (Certificate Signing Request)
3. Generate server private key
```bash
openssl genrsa -out keypebble-private.pem 4096
```

4. Create a certificate signing request (CSR)
```bash
openssl req -new -key keypebble-private.pem \
  -subj "/C=US/ST=Texas/L=Austin/O=Matt Co./CN=registry.example.com" \
  -out keypebble.csr
```


### Create a Configuration for SubjectAltName (SAN)
Create a temporary config file san.cnf:
```bash
cat > san.cnf <<EOF
subjectAltName = @alt_names
[alt_names]
DNS.1 = registry.example.com
DNS.2 = keypebble.local
IP.1 = 127.0.0.1
EOF
```

### Sign the Server Cert with the Root CA
```bash
openssl x509 -req -in keypebble.csr \
  -CA rootCA.pem -CAkey rootCA.key -CAcreateserial \
  -out keypebble-cert.pem -days 825 -sha256 \
  -extfile san.cnf
```

### Verify and Combine Chain
Verify it
```bash
openssl verify -CAfile rootCA.pem keypebble-cert.pem
```

Combine into a full chain bundle (useful for Registry)
```bash
cat keypebble-cert.pem rootCA.pem > keypebble-chain.pem
```


## How to make a "real" cert

### Install acme.sh if not already
```bash
curl https://get.acme.sh | sh
~/.acme.sh/acme.sh --set-default-ca --server letsencrypt
```

### Issue an RSA cert for your domain
```bash
~/.acme.sh/acme.sh --issue -d registry.example.com -w /var/www/html --keylength 4096
```

This creates:
```bash
~/.acme.sh/registry.example.com/
  ├── registry.example.com.key   	# RSA private key
  ├── registry.example.com.cer   	# leaf cert
  ├── fullchain.cer                     # cert + intermediate chain
  └── ca.cer                            # intermediate CA
```


Then export them to a stable system path:
```bash
~/.acme.sh/acme.sh --install-cert -d registry.example.com \
  --key-file       /etc/keypebble/keypebble-private.pem  \
  --fullchain-file /etc/keypebble/keypebble-cert.pem     \
  --reloadcmd      "docker compose restart registry keypebble"
```
