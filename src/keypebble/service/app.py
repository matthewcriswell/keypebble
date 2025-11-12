# src/keypebble/service/app.py
from datetime import datetime, timezone

from flask import Blueprint, Flask, current_app, jsonify, make_response, request

from keypebble.core import issue_token
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
    """Docker-style registry token endpoint with optional policy enforcement and generation."""
    now = datetime.now(timezone.utc)
    ttl = current_app.config.get("default_ttl_seconds", 3600)

    # --- 1. Identity ---
    user = request.headers.get("X-Authenticated-User")
    if not user:
        resp = make_response(jsonify({"error": "unauthenticated"}), 401)
        resp.headers["WWW-Authenticate"] = 'Basic realm="Keypebble"'
        return resp

    # --- 2. Requested scopes ---
    requested_scopes = []
    if request.args.getlist("scope"):
        requested_scopes.extend(request.args.getlist("scope"))
    if request.headers.get("X-Scopes"):
        requested_scopes.extend(request.headers.get("X-Scopes").split())



    # --- 3. Policy enforcement / generation ---
    access_claims = []
    final_scopes = []
    policy_handler = getattr(current_app, "policy_handler", None)
    
    if policy_handler:
        generate_mode = request.headers.get("X-Policy-Generate", "").lower() == "true"
    
        if generate_mode:
            # Explicitly requested generation (future or simple mock)
            access_claims = []
            build_access_claim(requested_scopes, access_claims)
            final_scopes = requested_scopes
        elif requested_scopes:
            # Normal request with explicit scopes – enforce policy rules
            access_claims = policy_handler.allowed_access(
                request.headers.get("X-Authenticated-User"), requested_scopes
            )
            final_scopes = requested_scopes
        else:
            # No scopes at all
            access_claims, final_scopes = [], []
    else:
        # No policy handler at all – same behavior as before
        access_claims = []
        build_access_claim(requested_scopes, access_claims)
        final_scopes = requested_scopes



    # --- 4. Token payload ---
    claims = {
        "iss": current_app.config.get("issuer", "https://keypebble.local"),
        "aud": request.args.get("service")
        or current_app.config.get("audience", "docker-registry"),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(now.timestamp()) + ttl,
        "sub": user,
        "service": request.args.get("service"),
        "scope": " ".join(final_scopes),
        "access": access_claims,
    }

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
