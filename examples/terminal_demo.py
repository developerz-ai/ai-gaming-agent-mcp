#!/usr/bin/env python
"""Terminal Demo - Connect to AI Gaming Agent MCP Server and run a workflow.

This script demonstrates how to:
1. Connect to the AI Gaming Agent MCP server over HTTP with SSE transport
2. Run the demo_terminal_workflow tool
3. Display results including screenshots

Usage:
    # Using default server (localhost:8765) with password
    python terminal_demo.py --password mypassword

    # Using custom server URL
    python terminal_demo.py --url http://192.168.1.100:8765 --password mypassword

    # Run custom command instead of "echo hello world"
    python terminal_demo.py --password mypassword --command "ls -la"

    # Without closing terminal automatically
    python terminal_demo.py --password mypassword --keep-open

Requirements:
    - AI Gaming Agent server running (gaming-agent serve)
    - Network access to the server
    - Python 3.12+
    - Dependencies: mcp (installed via pip)

Example with server setup:
    # Terminal 1: Start the server
    $ gaming-agent init --password secret
    $ gaming-agent serve

    # Terminal 2: Run this demo
    $ python examples/terminal_demo.py --password secret
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import logging
import sys
from pathlib import Path
from typing import Any

import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class MCPClient:
    """Client for connecting to AI Gaming Agent MCP server via HTTP/SSE."""

    def __init__(self, url: str = "http://localhost:8765", password: str = ""):
        """Initialize MCP client.

        Args:
            url: Base URL of the MCP server (e.g., http://localhost:8765)
            password: Authentication password for the server
        """
        self.url = url.rstrip("/")
        self.password = password
        self.client = httpx.AsyncClient()
        self.session_id: str | None = None

    async def health_check(self) -> dict[str, Any]:
        """Check server health.

        Returns:
            Health check response from server.

        Raises:
            httpx.HTTPError: If request fails.
        """
        try:
            response = await self.client.get(f"{self.url}/health", timeout=10.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Health check failed: {e}")
            raise

    async def connect(self) -> None:
        """Establish SSE connection to server.

        This initiates the MCP protocol handshake.

        Raises:
            httpx.HTTPError: If connection fails.
        """
        headers = {
            "Authorization": f"Bearer {self.password}",
            "Content-Type": "application/json",
        }

        try:
            # Initialize the SSE connection
            # Note: Real MCP SSE transport would use EventSource protocol
            # For this demo, we'll use HTTP polling instead
            response = await self.client.get(
                f"{self.url}/mcp",
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            logger.info("Connected to MCP server")
        except httpx.HTTPError as e:
            logger.error(f"Connection failed: {e}")
            raise

    async def call_tool(
        self,
        tool_name: str,
        args: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call an MCP tool on the server.

        Args:
            tool_name: Name of the tool to call (e.g., "demo_terminal_workflow")
            args: Arguments to pass to the tool. Defaults to {}.

        Returns:
            Result from the tool execution.

        Raises:
            httpx.HTTPError: If request fails.
        """
        if args is None:
            args = {}

        # Build the MCP request
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": args,
            },
            "id": 1,
        }

        headers = {
            "Authorization": f"Bearer {self.password}",
            "Content-Type": "application/json",
        }

        try:
            logger.info(f"Calling tool: {tool_name}")
            response = await self.client.post(
                f"{self.url}/mcp/messages",
                json=request_data,
                headers=headers,
                timeout=60.0,
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"Tool {tool_name} completed")
            return result
        except httpx.HTTPError as e:
            logger.error(f"Tool call failed: {e}")
            raise

    async def close(self) -> None:
        """Close the client connection."""
        await self.client.aclose()


async def save_screenshot(
    image_data: str,
    output_dir: Path = Path("."),
) -> Path:
    """Save base64-encoded image to file.

    Args:
        image_data: Base64-encoded image data
        output_dir: Directory to save the image to

    Returns:
        Path to the saved image file
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Decode base64 image
    image_bytes = base64.b64decode(image_data)

    # Save to file
    image_path = output_dir / "terminal_output.png"
    image_path.write_bytes(image_bytes)

    logger.info(f"Screenshot saved to {image_path}")
    return image_path


async def run_demo(
    url: str = "http://localhost:8765",
    password: str = "",
    command: str = "echo hello world",
    keep_open: bool = False,
    save_screenshots: bool = True,
) -> dict[str, Any]:
    """Run the terminal demo workflow.

    Args:
        url: Base URL of the MCP server
        password: Server password
        command: Command to execute in terminal
        keep_open: If True, don't close the terminal after execution
        save_screenshots: If True, save captured screenshots to disk

    Returns:
        Result from the workflow execution
    """
    logger.info("=" * 80)
    logger.info("AI Gaming Agent - Terminal Demo")
    logger.info("=" * 80)

    # Create client
    client = MCPClient(url, password)

    try:
        # Check server health
        logger.info("Checking server health...")
        health = await client.health_check()
        logger.info(f"Server status: {health['status']}")
        logger.info(f"Server version: {health['version']}")

        # Optionally connect (for proper SSE handshake)
        # In this simplified version, we skip the full SSE setup
        # and directly call tools via HTTP POST
        logger.info("Connecting to MCP server...")
        # await client.connect()

        # Call demo_terminal_workflow
        logger.info(f"Running terminal workflow: {command}")
        logger.info("-" * 80)

        result = await client.call_tool(
            "demo_terminal_workflow",
            {
                "text": command,
                "terminal_wait_ms": 2000,
                "post_type_wait_ms": 500,
                "post_enter_wait_ms": 1000,
                "capture_screenshot": True,
                "close_terminal": not keep_open,
            },
        )

        # Display results
        logger.info("-" * 80)
        logger.info("WORKFLOW RESULTS")
        logger.info("-" * 80)

        if isinstance(result, dict) and "result" in result:
            # Handle JSON-RPC response format
            workflow_result = result.get("result", {})
        else:
            workflow_result = result

        logger.info(f"Success: {workflow_result.get('success', False)}")
        logger.info(f"Platform: {workflow_result.get('platform', 'Unknown')}")
        logger.info(f"Terminal: {workflow_result.get('terminal_command', 'Unknown')}")
        logger.info(f"Text typed: {workflow_result.get('text_typed', '')}")
        logger.info(f"Total time: {workflow_result.get('total_time_ms', 0)}ms")

        # Log completed steps
        steps = workflow_result.get("steps_completed", [])
        logger.info(f"Completed steps ({len(steps)}):")
        for step in steps:
            logger.info(f"  ✓ {step}")

        # Handle error if present
        if workflow_result.get("error"):
            logger.error(f"Error: {workflow_result['error']}")

        # Save screenshot if present
        if save_screenshots and workflow_result.get("screenshot"):
            screenshot = workflow_result["screenshot"]
            if screenshot.get("success") and screenshot.get("image"):
                logger.info("Saving screenshot...")
                try:
                    image_path = await save_screenshot(
                        screenshot["image"],
                        Path("./screenshots"),
                    )
                    logger.info(f"Screenshot saved: {image_path}")
                except Exception as e:
                    logger.warning(f"Failed to save screenshot: {e}")

        logger.info("=" * 80)
        logger.info("Demo complete!")
        logger.info("=" * 80)

        return workflow_result

    except Exception as e:
        logger.error(f"Demo failed with error: {e}")
        logger.exception("Full traceback:")
        raise
    finally:
        await client.close()


def main() -> int:
    """Main entry point for the script.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    parser = argparse.ArgumentParser(
        description="AI Gaming Agent - Terminal Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with default server
  python terminal_demo.py --password mypassword

  # Custom server
  python terminal_demo.py --url http://192.168.1.100:8765 --password secret

  # Different command
  python terminal_demo.py --password secret --command "ls -la /home"

  # Keep terminal open
  python terminal_demo.py --password secret --keep-open
        """,
    )

    parser.add_argument(
        "--url",
        default="http://localhost:8765",
        help="URL of the MCP server (default: http://localhost:8765)",
    )
    parser.add_argument(
        "--password",
        required=True,
        help="Server password for authentication",
    )
    parser.add_argument(
        "--command",
        default="echo hello world",
        help="Command to execute in terminal (default: echo hello world)",
    )
    parser.add_argument(
        "--keep-open",
        action="store_true",
        help="Keep terminal open after command execution",
    )
    parser.add_argument(
        "--no-screenshots",
        action="store_true",
        help="Don't save screenshots to disk",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Run the demo
    try:
        result = asyncio.run(
            run_demo(
                url=args.url,
                password=args.password,
                command=args.command,
                keep_open=args.keep_open,
                save_screenshots=not args.no_screenshots,
            )
        )
        return 0 if result.get("success") else 1
    except KeyboardInterrupt:
        logger.info("Demo interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
