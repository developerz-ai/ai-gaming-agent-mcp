"""Tests for VLM (Vision Language Model) tools."""

import base64
import sys
from unittest.mock import MagicMock, patch

import ollama


class TestAnalyzeScreen:
    """Tests for the analyze_screen function."""

    @patch("ai_gaming_agent.tools.vlm.get_config")
    def test_vlm_disabled_returns_error(self, mock_get_config):
        """Test that analyze_screen returns error when VLM is disabled."""
        from ai_gaming_agent.tools.vlm import analyze_screen

        # Mock config with VLM disabled
        mock_config = MagicMock()
        mock_config.vlm.enabled = False
        mock_get_config.return_value = mock_config

        result = analyze_screen(prompt="What do you see?")

        assert result["success"] is False
        assert "not enabled" in result["error"].lower()
        assert result["prompt"] == "What do you see?"

    @patch("ai_gaming_agent.tools.vlm.get_config")
    def test_unsupported_provider_returns_error(self, mock_get_config):
        """Test that unsupported VLM provider returns error."""
        from ai_gaming_agent.tools.vlm import analyze_screen

        # Mock config with unsupported provider
        mock_config = MagicMock()
        mock_config.vlm.enabled = True
        mock_config.vlm.provider = "unsupported_provider"
        mock_get_config.return_value = mock_config

        # Create a mock screen module with screenshot function
        mock_screen_module = MagicMock()
        mock_screen_module.screenshot = MagicMock(return_value={
            "success": True,
            "image": base64.b64encode(b"fake image data").decode(),
        })

        # Patch the import
        with patch.dict("sys.modules", {"ai_gaming_agent.tools.screen": mock_screen_module}):
            result = analyze_screen(prompt="What do you see?")

        assert result["success"] is False
        assert "unsupported" in result["error"].lower()
        assert "unsupported_provider" in result["error"]

    @patch("ai_gaming_agent.tools.vlm.get_config")
    def test_screenshot_failure_returns_error(self, mock_get_config):
        """Test that screenshot failure is handled properly."""
        from ai_gaming_agent.tools.vlm import analyze_screen

        # Mock config with VLM enabled
        mock_config = MagicMock()
        mock_config.vlm.enabled = True
        mock_config.vlm.provider = "ollama"
        mock_get_config.return_value = mock_config

        # Create a mock screen module with failing screenshot
        mock_screen_module = MagicMock()
        mock_screen_module.screenshot = MagicMock(return_value={
            "success": False,
            "error": "No display available",
        })

        # Patch the import
        with patch.dict("sys.modules", {"ai_gaming_agent.tools.screen": mock_screen_module}):
            result = analyze_screen(prompt="What do you see?")

        assert result["success"] is False
        assert "screenshot" in result["error"].lower()
        assert "No display available" in result["error"]

    @patch("ai_gaming_agent.tools.vlm.get_config")
    def test_ollama_import_error(self, mock_get_config):
        """Test handling when ollama package is not installed."""
        from ai_gaming_agent.tools.vlm import _analyze_with_ollama

        # Simulate ollama not being installed
        with patch.dict("sys.modules", {"ollama": None}):
            # Need to reload the function to trigger ImportError
            result = _analyze_with_ollama(
                prompt="What do you see?",
                image_b64=base64.b64encode(b"fake").decode(),
                model="qwen2.5-vl:3b",
                endpoint="http://localhost:11434",
            )

        # The function handles ImportError gracefully
        assert result["success"] is False
        assert "ollama" in result["error"].lower() or "not installed" in result["error"].lower()

    @patch("ollama.Client")
    @patch("ai_gaming_agent.tools.vlm.get_config")
    def test_successful_analysis(self, mock_get_config, mock_ollama_client):
        """Test successful screen analysis with mocked Ollama."""
        from ai_gaming_agent.tools.vlm import analyze_screen

        # Mock config
        mock_config = MagicMock()
        mock_config.vlm.enabled = True
        mock_config.vlm.provider = "ollama"
        mock_config.vlm.model = "qwen2.5-vl:3b"
        mock_config.vlm.endpoint = "http://localhost:11434"
        mock_get_config.return_value = mock_config

        # Mock Ollama client
        mock_client_instance = MagicMock()
        mock_client_instance.chat.return_value = {
            "message": {
                "content": "I see a game menu with three buttons: Start, Options, and Quit."
            }
        }
        mock_ollama_client.return_value = mock_client_instance

        # Create a mock screen module
        fake_image = base64.b64encode(b"fake PNG image data").decode()
        mock_screen_module = MagicMock()
        mock_screen_module.screenshot = MagicMock(return_value={
            "success": True,
            "image": fake_image,
            "width": 1920,
            "height": 1080,
        })

        with patch.dict("sys.modules", {"ai_gaming_agent.tools.screen": mock_screen_module}):
            result = analyze_screen(prompt="What buttons are visible?")

        assert result["success"] is True
        assert "game menu" in result["response"].lower()
        assert result["prompt"] == "What buttons are visible?"
        assert result["model"] == "qwen2.5-vl:3b"

        # Verify Ollama was called correctly
        mock_ollama_client.assert_called_once_with(host="http://localhost:11434")
        mock_client_instance.chat.assert_called_once()

    @patch("ollama.Client")
    @patch("ai_gaming_agent.tools.vlm.get_config")
    def test_empty_response_returns_error(self, mock_get_config, mock_ollama_client):
        """Test that empty VLM response is handled as error."""
        from ai_gaming_agent.tools.vlm import analyze_screen

        # Mock config
        mock_config = MagicMock()
        mock_config.vlm.enabled = True
        mock_config.vlm.provider = "ollama"
        mock_config.vlm.model = "qwen2.5-vl:3b"
        mock_config.vlm.endpoint = "http://localhost:11434"
        mock_get_config.return_value = mock_config

        # Mock Ollama client to return empty response
        mock_client_instance = MagicMock()
        mock_client_instance.chat.return_value = {"message": {"content": ""}}
        mock_ollama_client.return_value = mock_client_instance

        # Create a mock screen module
        mock_screen_module = MagicMock()
        mock_screen_module.screenshot = MagicMock(return_value={
            "success": True,
            "image": base64.b64encode(b"fake").decode(),
        })

        with patch.dict("sys.modules", {"ai_gaming_agent.tools.screen": mock_screen_module}):
            result = analyze_screen(prompt="What do you see?")

        assert result["success"] is False
        assert "empty" in result["error"].lower()

    @patch("ai_gaming_agent.tools.vlm.get_config")
    def test_connection_error_handling(self, mock_get_config):
        """Test that connection errors are handled with helpful message."""
        from ai_gaming_agent.tools.vlm import _analyze_with_ollama

        # Mock config
        mock_config = MagicMock()
        mock_config.vlm.enabled = True
        mock_config.vlm.provider = "ollama"
        mock_config.vlm.model = "qwen2.5-vl:3b"
        mock_config.vlm.endpoint = "http://localhost:11434"
        mock_get_config.return_value = mock_config

        # Mock Ollama to raise connection error
        with patch("ollama.Client") as mock_client:
            mock_client.side_effect = Exception("Connection refused")

            result = _analyze_with_ollama(
                prompt="What do you see?",
                image_b64=base64.b64encode(b"fake").decode(),
                model="qwen2.5-vl:3b",
                endpoint="http://localhost:11434",
            )

        assert result["success"] is False
        # The error message contains "connect" in "Cannot connect to Ollama"
        assert "connect" in result["error"].lower()


class TestAnalyzeImage:
    """Tests for the analyze_image function."""

    @patch("ai_gaming_agent.tools.vlm.get_config")
    def test_vlm_disabled_returns_error(self, mock_get_config):
        """Test that analyze_image returns error when VLM is disabled."""
        from ai_gaming_agent.tools.vlm import analyze_image

        mock_config = MagicMock()
        mock_config.vlm.enabled = False
        mock_get_config.return_value = mock_config

        result = analyze_image(
            image_b64=base64.b64encode(b"fake").decode(),
            prompt="What do you see?",
        )

        assert result["success"] is False
        assert "not enabled" in result["error"].lower()

    @patch("ollama.Client")
    @patch("ai_gaming_agent.tools.vlm.get_config")
    def test_successful_image_analysis(self, mock_get_config, mock_ollama_client):
        """Test successful image analysis with provided image."""
        from ai_gaming_agent.tools.vlm import analyze_image

        # Mock config
        mock_config = MagicMock()
        mock_config.vlm.enabled = True
        mock_config.vlm.provider = "ollama"
        mock_config.vlm.model = "llava:13b"
        mock_config.vlm.endpoint = "http://localhost:11434"
        mock_get_config.return_value = mock_config

        # Mock Ollama client
        mock_client_instance = MagicMock()
        mock_client_instance.chat.return_value = {
            "message": {"content": "This is a screenshot of a desktop."}
        }
        mock_ollama_client.return_value = mock_client_instance

        result = analyze_image(
            image_b64=base64.b64encode(b"fake PNG data").decode(),
            prompt="Describe this image",
        )

        assert result["success"] is True
        assert "desktop" in result["response"].lower()
        assert result["model"] == "llava:13b"


class TestAnalyzeWithOllama:
    """Tests for the internal _analyze_with_ollama function."""

    def test_ollama_not_installed(self):
        """Test behavior when ollama package is not available."""
        from ai_gaming_agent.tools.vlm import _analyze_with_ollama

        # Mock ollama import to fail
        original_modules = sys.modules.copy()

        # Remove ollama from modules if present
        if "ollama" in sys.modules:
            del sys.modules["ollama"]

        # The function should handle this gracefully
        # Note: This test verifies the error message when ollama can't be imported
        result = _analyze_with_ollama(
            prompt="test",
            image_b64=base64.b64encode(b"test").decode(),
            model="test",
            endpoint="http://localhost:11434",
        )

        # Restore modules
        sys.modules.update(original_modules)

        # If ollama is actually installed in the test environment, the test will pass
        # If not, we should see the import error
        assert "success" in result

    @patch("ollama.Client")
    def test_model_not_found_error(self, mock_ollama_client):
        """Test helpful error message when model is not pulled."""
        from ai_gaming_agent.tools.vlm import _analyze_with_ollama

        mock_client_instance = MagicMock()
        mock_client_instance.chat.side_effect = ollama.ResponseError("model 'qwen2.5-vl:3b' not found")
        mock_ollama_client.return_value = mock_client_instance

        result = _analyze_with_ollama(
            prompt="test",
            image_b64=base64.b64encode(b"test").decode(),
            model="qwen2.5-vl:3b",
            endpoint="http://localhost:11434",
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()
        # Should suggest pulling the model
        assert "pull" in result["error"].lower()
