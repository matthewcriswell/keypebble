# src/keypebble/service/app.py
from flask import Blueprint, Flask, current_app, jsonify, request

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
    mapping = {
        "service": "docker-registry",
        "scope": "$.query.scope",
        "sub": "$.query.account",
        "access": lambda req: build_access_claim(req.args.get("scope")),
    }
    claims = ClaimBuilder().build(request, mapping)
    token = issue_token(current_app.config, claims)
    return jsonify({"token": token, "claims": claims}), 200


def create_app(config: dict | None = None):
    """Flask application factory."""
    app = Flask(__name__)
    app.config.update(config or {})
    app.register_blueprint(bp)
    return app
