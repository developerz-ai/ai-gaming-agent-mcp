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
    """Run the MCP server.

    Supports two transport modes:
    - stdio: Standard I/O transport for local use (e.g., Claude Desktop)
    - http: HTTP/SSE transport for remote control over network
    """
    config = Config.load(Path(args.config) if args.config else None)

    # Override with CLI args
    if args.port:
        config.server.port = args.port
    if args.password:
        config.server.password = args.password
    if args.host:
        config.server.host = args.host

    transport = args.transport

    if transport == "stdio":
        from ai_gaming_agent.server import run_server

        print(f"Starting AI Gaming Agent MCP Server v{__version__} (stdio)", file=sys.stderr)
        asyncio.run(run_server(config))
    else:  # http
        from ai_gaming_agent.http_server import run_http_server

        print(f"Starting AI Gaming Agent MCP Server v{__version__} (HTTP/SSE)", file=sys.stderr)
        print(f"Listening on http://{config.server.host}:{config.server.port}", file=sys.stderr)
        print(f"MCP endpoint: http://{config.server.host}:{config.server.port}/mcp", file=sys.stderr)

        if not config.server.password:
            print("WARNING: No password configured. Authentication will fail.", file=sys.stderr)
            print("Run 'gaming-agent init --password <password>' to set one.", file=sys.stderr)

        asyncio.run(run_http_server(config))

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
    serve_parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "http"],
        default="http",
        help="Transport mode: 'stdio' for local use, 'http' for remote (default: http)",
    )
    serve_parser.add_argument("--host", type=str, help="Host to bind to (http mode)")
    serve_parser.add_argument("--port", type=int, help="Port to listen on (http mode)")
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
