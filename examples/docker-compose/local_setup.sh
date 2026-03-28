#!/usr/bin/env bash
set -euo pipefail

# Sets up a local Docker registry with keypebble token auth using mkcert.
# Run from the project root or from examples/docker-compose/.
#
# After setup, start the stack with:
#   docker compose -f examples/docker-compose/docker-compose.local.yaml up -d --build
#
# Demo users (defined in examples/policy.yaml):
#   alice / swordfish123  — pull only
#   bob   / bobrules      — pull + push

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CERTS_DIR="${SCRIPT_DIR}/certs"
DOMAIN="registry.localhost"

# --- Prerequisites ---

check_command() {
    if ! command -v "$1" &>/dev/null; then
        echo "ERROR: '$1' is not installed."
        echo "$2"
        exit 1
    fi
}

check_command mkcert \
    "Install mkcert: https://github.com/FiloSottile/mkcert#installation
  macOS:  brew install mkcert
  Linux:  https://github.com/FiloSottile/mkcert#linux"

check_command htpasswd \
    "Install htpasswd (part of Apache tools):
  macOS:  brew install httpd
  Linux:  sudo apt-get install apache2-utils"

check_command docker \
    "Install Docker: https://docs.docker.com/get-docker/"

# --- 1. Install local CA ---

echo "==> Installing mkcert local CA into system trust store..."
mkcert -install

# --- 2. Generate certs ---

mkdir -p "${CERTS_DIR}"

if [[ -f "${CERTS_DIR}/${DOMAIN}.pem" ]]; then
    echo "==> Certs already exist, skipping generation."
else
    echo "==> Generating TLS certificate for ${DOMAIN}..."
    mkcert -cert-file "${CERTS_DIR}/${DOMAIN}.pem" \
           -key-file "${CERTS_DIR}/${DOMAIN}-key.pem" \
           "${DOMAIN}"
fi

# --- 3. Copy root CA ---

if [[ -f "${CERTS_DIR}/rootCA.pem" ]]; then
    echo "==> rootCA.pem already present, skipping copy."
else
    echo "==> Copying mkcert root CA..."
    cp "$(mkcert -CAROOT)/rootCA.pem" "${CERTS_DIR}/rootCA.pem"
fi

# --- 4. Create htpasswd ---

if [[ -f "${CERTS_DIR}/htpasswd" ]]; then
    echo "==> htpasswd already exists, skipping."
    echo "    To add more users: htpasswd -B ${CERTS_DIR}/htpasswd <username>"
else
    echo "==> Creating htpasswd with demo users..."
    htpasswd -Bbc "${CERTS_DIR}/htpasswd" alice swordfish123
    htpasswd -Bb "${CERTS_DIR}/htpasswd" bob bobrules
fi

# --- 5. Docker CA trust ---

echo "==> Configuring Docker to trust the local CA for ${DOMAIN}..."

case "$(uname -s)" in
    Darwin)
        DOCKER_CERT_DIR="${HOME}/.docker/certs.d/${DOMAIN}"
        mkdir -p "${DOCKER_CERT_DIR}"
        cp "${CERTS_DIR}/rootCA.pem" "${DOCKER_CERT_DIR}/ca.crt"
        echo "    Installed CA to ${DOCKER_CERT_DIR}/ca.crt"
        echo "    If push/pull still fails, restart Docker Desktop."
        ;;
    Linux)
        DOCKER_CERT_DIR="/etc/docker/certs.d/${DOMAIN}"
        if [[ -d "${DOCKER_CERT_DIR}" ]] && [[ -f "${DOCKER_CERT_DIR}/ca.crt" ]]; then
            echo "    ${DOCKER_CERT_DIR}/ca.crt already exists."
        else
            echo "    Writing to ${DOCKER_CERT_DIR}/ca.crt (requires sudo)..."
            sudo mkdir -p "${DOCKER_CERT_DIR}"
            sudo cp "${CERTS_DIR}/rootCA.pem" "${DOCKER_CERT_DIR}/ca.crt"
        fi
        echo "    If push/pull still fails, restart Docker: sudo systemctl restart docker"
        ;;
    *)
        echo "    WARNING: Unknown platform $(uname -s). Manually copy"
        echo "    ${CERTS_DIR}/rootCA.pem to your Docker cert trust directory."
        ;;
esac

# --- Done ---

echo ""
echo "Setup complete. Start the local registry:"
echo ""
echo "  docker compose -f ${SCRIPT_DIR}/docker-compose.local.yaml up -d --build"
echo ""
echo "Then test:"
echo ""
echo "  docker login ${DOMAIN} -u bob -p bobrules"
echo "  docker pull alpine:latest"
echo "  docker tag alpine:latest ${DOMAIN}/bob-space/app-api:test"
echo "  docker push ${DOMAIN}/bob-space/app-api:test"
