"""CLI for AI Gaming Agent."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from ai_gaming_agent import __version__
from ai_gaming_agent.config import Config


def cmd_serve(args: argparse.Namespace) -> int:
    """Run the MCP server."""
    from ai_gaming_agent.server import run_server

    config = Config.load(Path(args.config) if args.config else None)

    # Override with CLI args
    if args.port:
        config.server.port = args.port
    if args.password:
        config.server.password = args.password
    if args.host:
        config.server.host = args.host

    print(f"Starting AI Gaming Agent MCP Server v{__version__}", file=sys.stderr)
    print(f"Host: {config.server.host}:{config.server.port}", file=sys.stderr)

    asyncio.run(run_server(config))
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """Initialize configuration."""
    config_path = Path.home() / ".gaming-agent" / "config.json"

    if config_path.exists() and not args.force:
        print(f"Config already exists at {config_path}", file=sys.stderr)
        print("Use --force to overwrite", file=sys.stderr)
        return 1

    config = Config()
    if args.password:
        config.server.password = args.password
    if args.port:
        config.server.port = args.port

    config.save(config_path)
    print(f"Created config at {config_path}")
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    """Show current configuration."""
    config = Config.load()
    print(json.dumps(config.model_dump(), indent=2))
    return 0


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="gaming-agent",
        description="AI Gaming Agent - MCP server for remote PC automation",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Run the MCP server")
    serve_parser.add_argument("--host", type=str, help="Host to bind to")
    serve_parser.add_argument("--port", type=int, help="Port to listen on")
    serve_parser.add_argument("--password", type=str, help="Authentication password")
    serve_parser.add_argument("--config", type=str, help="Path to config file")
    serve_parser.set_defaults(func=cmd_serve)

    # init command
    init_parser = subparsers.add_parser("init", help="Initialize configuration")
    init_parser.add_argument("--password", type=str, help="Set authentication password")
    init_parser.add_argument("--port", type=int, help="Set server port")
    init_parser.add_argument("--force", action="store_true", help="Overwrite existing config")
    init_parser.set_defaults(func=cmd_init)

    # config command
    config_parser = subparsers.add_parser("config", help="Show current configuration")
    config_parser.set_defaults(func=cmd_config)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
