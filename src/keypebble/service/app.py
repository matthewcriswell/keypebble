# src/keypebble/service/app.py
from datetime import datetime, timezone

from flask import Blueprint, Flask, current_app, jsonify, make_response, request

from keypebble.core import issue_token
from keypebble.core.policy import Policy, parse_scopes

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


def build_v2_claims(
    user: str,
    requested_scopes: list[str],
    policy: "Policy | None",
    policy_path: str | None,
    generate_mode: bool,
    config: dict,
    service_audience: str | None,
    now: datetime,
    ttl: int,
) -> dict:
    """Assemble JWT claims for a Docker registry token request.
    Raises ValueError if generate_mode is True and user not in policy.
    """
    if policy:
        if generate_mode:
            inferred = Policy.from_file(policy_path).generate_for(user)
            final_scopes = inferred.get("scope", "").split()
            access_claims = parse_scopes(final_scopes)
        elif requested_scopes:
            access_claims = policy.allowed_access(user, requested_scopes)
            final_scopes = requested_scopes
        else:
            access_claims, final_scopes = [], []
    else:
        access_claims = parse_scopes(requested_scopes)
        final_scopes = requested_scopes

    return {
        "iss": config.get("issuer", "https://keypebble.local"),
        "aud": service_audience or config.get("audience", "docker-registry"),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(now.timestamp()) + ttl,
        "sub": user,
        "service": service_audience,
        "scope": " ".join(final_scopes),
        "access": access_claims,
    }


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

    # --- 3. Build claims ---
    policy = getattr(current_app, "policy_handler", None)
    policy_path = current_app.config.get("POLICY_PATH")
    generate_mode = (
        policy is not None
        and request.headers.get("X-Policy-Generate", "").lower() == "true"
    )

    try:
        claims = build_v2_claims(
            user=user,
            requested_scopes=requested_scopes,
            policy=policy,
            policy_path=policy_path,
            generate_mode=generate_mode,
            config=current_app.config,
            service_audience=request.args.get("service"),
            now=now,
            ttl=ttl,
        )
    except ValueError as e:
        return jsonify({"error": "unauthorized", "message": str(e)}), 403

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
        app.policy_handler = Policy.from_file(policy_path)
    else:
        app.policy_handler = None
    app.register_blueprint(bp)

    return app
