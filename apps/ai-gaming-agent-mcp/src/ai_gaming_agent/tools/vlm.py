"""Vision Language Model (VLM) tools for screen analysis.

This module provides tools for analyzing screenshots using local VLM providers
like Ollama. The VLM integration is optional and must be enabled in config.
"""

from __future__ import annotations

import base64
import logging
from typing import Any

from ai_gaming_agent.config import get_config

logger = logging.getLogger(__name__)


def analyze_screen(
    prompt: str,
    monitor: int | None = None,
) -> dict[str, Any]:
    """Analyze the current screen using a Vision Language Model.

    Takes a screenshot and sends it to the configured VLM (e.g., Ollama with
    qwen2.5-vl) along with a prompt for analysis. Useful for understanding
    game state, reading text, or identifying UI elements.

    Args:
        prompt: The analysis prompt/question about the screen content.
            Examples:
            - "What is the current health bar percentage?"
            - "Is there a dialog box on screen? What does it say?"
            - "List all visible menu options"
        monitor: Optional monitor index for multi-monitor setups.

    Returns:
        Dict with:
        - success: bool indicating if analysis completed
        - response: str containing the VLM's analysis (if successful)
        - error: str with error message (if failed)
        - model: str name of the VLM model used
        - prompt: str the original prompt for reference

    Raises:
        No exceptions are raised; errors are returned in the result dict.

    Configuration:
        Requires VLM to be enabled in ~/.gaming-agent/config.json:
        {
            "vlm": {
                "enabled": true,
                "provider": "ollama",
                "model": "qwen2.5-vl:3b",
                "endpoint": "http://localhost:11434"
            }
        }
    """
    config = get_config()

    # Check if VLM is enabled
    if not config.vlm.enabled:
        return {
            "success": False,
            "error": (
                "VLM is not enabled. Set vlm.enabled=true in config. "
                "Also ensure you have installed the vlm extra: pip install ai-gaming-agent[vlm]"
            ),
            "prompt": prompt,
        }

    # Get the screenshot first
    try:
        # Import screenshot here to avoid circular imports and GUI issues
        from ai_gaming_agent.tools.screen import screenshot

        screenshot_result = screenshot(monitor=monitor)
        if not screenshot_result.get("success"):
            return {
                "success": False,
                "error": f"Failed to capture screenshot: {screenshot_result.get('error', 'Unknown error')}",
                "prompt": prompt,
            }

        image_b64 = screenshot_result["image"]
    except Exception as e:
        return {
            "success": False,
            "error": f"Screenshot capture failed: {e!s}",
            "prompt": prompt,
        }

    # Process with VLM based on provider
    if config.vlm.provider == "ollama":
        return _analyze_with_ollama(
            prompt=prompt,
            image_b64=image_b64,
            model=config.vlm.model,
            endpoint=config.vlm.endpoint,
        )
    else:
        return {
            "success": False,
            "error": f"Unsupported VLM provider: {config.vlm.provider}. Supported: ollama",
            "prompt": prompt,
        }


def _analyze_with_ollama(
    prompt: str,
    image_b64: str,
    model: str,
    endpoint: str,
) -> dict[str, Any]:
    """Analyze an image using Ollama's vision models.

    Args:
        prompt: The analysis prompt.
        image_b64: Base64-encoded PNG image data.
        model: Ollama model name (e.g., "qwen2.5-vl:3b", "llava:13b").
        endpoint: Ollama API endpoint URL.

    Returns:
        Dict with success status, response or error message.
    """
    try:
        import ollama
    except ImportError:
        return {
            "success": False,
            "error": (
                "Ollama Python client not installed. "
                "Install with: pip install ai-gaming-agent[vlm] or pip install ollama"
            ),
            "prompt": prompt,
            "model": model,
        }

    try:
        # Create Ollama client with custom endpoint
        client = ollama.Client(host=endpoint)

        # Ollama expects images as bytes or file paths
        # We have base64, so decode it
        image_bytes = base64.b64decode(image_b64)

        # Call the vision model
        response = client.chat(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_bytes],
                }
            ],
        )

        # Extract the response text
        response_text = response.get("message", {}).get("content", "")

        if not response_text:
            return {
                "success": False,
                "error": "VLM returned empty response",
                "prompt": prompt,
                "model": model,
            }

        return {
            "success": True,
            "response": response_text,
            "prompt": prompt,
            "model": model,
        }

    except ollama.ResponseError as e:
        error_msg = str(e)
        # Provide helpful messages for common errors
        if "model" in error_msg.lower() and "not found" in error_msg.lower():
            error_msg = f"Model '{model}' not found. Pull it first with: ollama pull {model}"
        return {
            "success": False,
            "error": f"Ollama API error: {error_msg}",
            "prompt": prompt,
            "model": model,
        }
    except Exception as e:
        # Check for connection errors
        error_str = str(e).lower()
        if "connection" in error_str or "refused" in error_str:
            return {
                "success": False,
                "error": (f"Cannot connect to Ollama at {endpoint}. Ensure Ollama is running: ollama serve"),
                "prompt": prompt,
                "model": model,
            }
        return {
            "success": False,
            "error": f"VLM analysis failed: {e!s}",
            "prompt": prompt,
            "model": model,
        }


def analyze_image(
    image_b64: str,
    prompt: str,
) -> dict[str, Any]:
    """Analyze a provided base64 image (without taking a screenshot).

    This is useful when you already have an image and want to analyze it,
    rather than capturing a new screenshot.

    Args:
        image_b64: Base64-encoded image data (PNG or JPEG).
        prompt: The analysis prompt/question about the image.

    Returns:
        Dict with success status, response or error message.
    """
    config = get_config()

    if not config.vlm.enabled:
        return {
            "success": False,
            "error": "VLM is not enabled. Set vlm.enabled=true in config.",
            "prompt": prompt,
        }

    if config.vlm.provider == "ollama":
        return _analyze_with_ollama(
            prompt=prompt,
            image_b64=image_b64,
            model=config.vlm.model,
            endpoint=config.vlm.endpoint,
        )
    else:
        return {
            "success": False,
            "error": f"Unsupported VLM provider: {config.vlm.provider}",
            "prompt": prompt,
        }
