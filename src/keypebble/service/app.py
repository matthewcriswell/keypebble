# src/keypebble/service/app.py
from datetime import datetime, timezone

from flask import Blueprint, Flask, current_app, jsonify, make_response, request

from keypebble.core import issue_token
from keypebble.core.claims import ClaimBuilder

bp = Blueprint("basic", __name__)


@bp.route("/healthz", methods=["GET"])
def healthz():
    """Simple readiness endpoint."""
    return jsonify({"status": "ok"}), 200


@bp.route("/auth", methods=["POST"])
def auth():
    """Issue a JWT for the provided claims."""
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify({"error": "invalid json"}), 400

    token = issue_token(current_app.config, body)
    return jsonify({"token": token, "claims": body}), 200


def build_access_claim(scope_str: str | None):
    if not scope_str:
        return []
    try:
        type_, name, actions = scope_str.split(":", 2)
        return [
            {
                "type": type_,
                "name": name,
                "actions": actions.split(","),
            }
        ]
    except ValueError:
        return []


@bp.route("/v2/token", methods=["GET"])
def v2_token():
    """Prototype Docker-style registry token endpoint."""
    now = datetime.now(timezone.utc)
    ttl = current_app.config.get("default_ttl_seconds", 3600)
    mapping = {
        "service": "docker-registry",
        "scope": "$.query.scope",
        "sub": "$.query.account",
        "access": lambda req: build_access_claim(req.args.get("scope")),
    }
    claims = ClaimBuilder().build(request, mapping)
    #claims = {k: v for k, v in claims.items() if v is not None}
    # Get identity from nginx
    user = request.headers.get("X-Authenticated-User")
    if not user:
        # This means nginx didn’t authenticate the user first
        resp = make_response(jsonify({"error": "unauthenticated"}), 401)
        resp.headers["WWW-Authenticate"] = 'Basic realm="Keypebble"'
        return resp

    claims["sub"] = user
    service = request.args.get("service")
    if service:
        claims["aud"] = service
    token = issue_token(current_app.config, claims)
    return (
        jsonify(
            {
                "token": token,
                "expires_in": ttl,
                "issued_at": now.isoformat(timespec="seconds"),
                "nbf": now,
                "claims": claims,
            }
        ),
        200,
    )


def create_app(config: dict | None = None):
    """Flask application factory."""
    app = Flask(__name__)
    app.config.update(config or {})
    app.register_blueprint(bp)
    return app
