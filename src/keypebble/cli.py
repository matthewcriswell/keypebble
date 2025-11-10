import argparse
import json

from keypebble.config import load_config
from keypebble.core import issue_token
from keypebble.service.app import create_app


def cmd_issue(args):
    config = load_config(args.config)
    claims = json.loads(args.claims) if args.claims else {}
    token = issue_token(config, claims)
    print(token)


def cmd_serve(args):
    config = load_config(args.config)
    app = create_app(config)
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
    p_issue.set_defaults(func=cmd_issue)

    # keypebble serve
    p_serve = subparsers.add_parser(
        "serve", help="Run Keypebble service mode (not implemented)"
    )
    p_serve.add_argument("--config", required=True, help="Path to YAML configuration")
    p_serve.set_defaults(func=cmd_serve)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
