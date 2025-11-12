# src/keypebble/service/app.py
from datetime import datetime, timezone

from flask import Blueprint, Flask, current_app, jsonify, make_response, request

from keypebble.core import issue_token
from keypebble.core.claims import ClaimBuilder
from keypebble.core.policy import PolicyHandler

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


def build_access_claim(scopes_list: list | None, access_claim: list):
    if not scopes_list:
        return []

    try:
        # output = list()
        for scope_str in scopes_list:
            scope_list = scope_str.split(":")
            access_claim.append(
                {
                    "type": scope_list[0],
                    "name": scope_list[1],
                    "actions": scope_list[-1].split(","),
                }
            )

        # return output
    except ValueError:
        return []


@bp.route("/v2/token", methods=["GET"])
def v2_token():
    """Prototype Docker-style registry token endpoint."""
    now = datetime.now(timezone.utc)
    ttl = current_app.config.get("default_ttl_seconds", 3600)
    scopes = []
    access_claim = []
    if request.args.getlist("scope"):
        build_access_claim(request.args.getlist("scope"), access_claim)
        scopes += request.args.getlist("scope")
    if request.headers.get("X-Scopes"):
        build_access_claim(request.headers.get("X-Scopes").split(" "), access_claim)
        scopes += request.args.getlist("scope")
    mapping = {
        "service": "$.query.service",
        "scope": " ".join(scopes),
        "sub": "$.query.account",
        "access": access_claim,
    }
    claims = ClaimBuilder().build(request, mapping)
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


def create_app(config: dict | None = None, policy_path: str | None = None):
    """Flask application factory."""
    app = Flask(__name__)
    app.config.update(config or {})
    if policy_path:
        app.config["POLICY_PATH"] = policy_path
        app.policy_handler = PolicyHandler(policy_path)
    else:
        app.policy_handler = None
    app.register_blueprint(bp)

    return app
