import argparse
import json
from datetime import datetime, timezone

from keypebble.config import load_config
from keypebble.core import build_command_claims, issue_token
from keypebble.core.policy import Policy, parse_scopes
from keypebble.service.app import create_app


def cmd_issue(args):
    """Issue a JWT token directly from the CLI."""
    config = load_config(args.config)
    claims = json.loads(args.claims) if args.claims else {}

    if args.policy:
        policy = Policy.from_file(args.policy)
        user = claims.get("sub") or claims.get("user") or "unknown"

        # --- Policy generation phase ---
        if args.generate:
            # Explicit generation request
            generated = policy.generate_for(user)
            claims.update(generated)

            # Also build structured access list from generated scopes
            scopes = claims.get("scope", "").split()
            claims["access"] = parse_scopes(scopes)

        else:
            # Normal validation mode
            if "scope" not in claims and "access" not in claims:
                inferred = policy.generate_for(user)
                claims.update(inferred)

            scopes = claims["scope"].split() if isinstance(claims["scope"], str) else []
            claims["access"] = policy.allowed_access(user, scopes)

    token = issue_token(config, claims)
    print(token)


def cmd_command(args):
    """Mint a signed command token."""
    config = load_config(args.config)
    user = args.user or config.get("issuer", "keypebble")
    ttl = int(config.get("default_ttl_seconds", 3600))
    now = datetime.now(timezone.utc)

    claims = build_command_claims(
        user=user,
        command=args.cmd,
        target=args.target,
        config=config,
        now=now,
        ttl=ttl,
    )

    # Structured claim builders produce trusted claims — skip allowlist filter
    issue_config = dict(config)
    issue_config.pop("allowed_custom_claims", None)
    token = issue_token(issue_config, claims)
    print(token)


def cmd_serve(args):
    """Run Keypebble in service mode (Flask API)."""
    config = load_config(args.config)
    policy_path = args.policy or "/etc/keypebble/policy.yaml"
    app = create_app(config, policy_path=policy_path)

    svc = config.get("service", {})
    host = svc.get("host", "0.0.0.0")
    port = svc.get("port", 8080)
    app.run(host=host, port=port)


def build_parser():
    parser = argparse.ArgumentParser(description="Keypebble command-line interface")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # keypebble issue
    p_issue = subparsers.add_parser("issue", help="Issue a JWT token")
    p_issue.add_argument("--config", required=True, help="Path to YAML configuration")
    p_issue.add_argument("--claims", help="Custom claims as JSON string")
    p_issue.add_argument("--policy", help="Optional path to policy file")
    p_issue.add_argument(
        "--generate",
        action="store_true",
        help="Generate claims automatically from policy for the given user (ignores provided scope)",
    )

    p_issue.set_defaults(func=cmd_issue)

    # keypebble command
    p_cmd = subparsers.add_parser("command", help="Mint a signed command token")
    p_cmd.add_argument("--config", required=True, help="Path to YAML configuration")
    p_cmd.add_argument(
        "--target", required=True, help="Target remote environment (maps to aud)"
    )
    p_cmd.add_argument(
        "--command", dest="cmd", required=True, help="Command string to embed"
    )
    p_cmd.add_argument(
        "--user", help="Issuing user (maps to sub; defaults to config issuer)"
    )
    p_cmd.set_defaults(func=cmd_command)

    # keypebble serve
    p_serve = subparsers.add_parser("serve", help="Run Keypebble service mode")
    p_serve.add_argument("--config", required=True, help="Path to YAML configuration")
    p_serve.add_argument(
        "--policy",
        help="Optional path to policy configuration file (default: /etc/keypebble/policy.yaml)",
    )
    p_serve.set_defaults(func=cmd_serve)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
