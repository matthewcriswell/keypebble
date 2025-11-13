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
