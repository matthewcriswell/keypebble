# src/keypebble/service/app.py
from flask import Blueprint, Flask, current_app, jsonify, request

from keypebble.core import issue_token

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


def create_app(config: dict | None = None):
    """Flask application factory."""
    app = Flask(__name__)
    app.config.update(config or {})
    app.register_blueprint(bp)
    return app
