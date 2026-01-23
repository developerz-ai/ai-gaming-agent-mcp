"""Tests for VLM (Vision Language Model) tools."""

import base64
from unittest.mock import MagicMock, patch


class TestAnalyzeScreen:
    """Tests for analyze_screen function."""

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
        assert "VLM is not enabled" in result["error"]
        assert "vlm.enabled=true" in result["error"]
        assert result["prompt"] == "What do you see?"

    @patch("ai_gaming_agent.tools.vlm.get_config")
    def test_screenshot_failure_propagates(self, mock_get_config):
        """Test that screenshot failures are properly handled."""
        # Mock screenshot function before importing
        mock_screen = MagicMock()
        mock_screen.screenshot = MagicMock(return_value={
            "success": False,
            "error": "No display available",
        })

        with patch.dict("sys.modules", {"ai_gaming_agent.tools.screen": mock_screen}):
            from ai_gaming_agent.tools.vlm import analyze_screen

            # Mock config with VLM enabled
            mock_config = MagicMock()
            mock_config.vlm.enabled = True
            mock_config.vlm.provider = "ollama"
            mock_config.vlm.model = "qwen2.5-vl:3b"
            mock_config.vlm.endpoint = "http://localhost:11434"
            mock_get_config.return_value = mock_config

            result = analyze_screen(prompt="Describe the screen")

        assert result["success"] is False
        assert "Failed to capture screenshot" in result["error"]
        assert "No display available" in result["error"]

    @patch("ai_gaming_agent.tools.vlm.get_config")
    def test_screenshot_exception_handled(self, mock_get_config):
        """Test that exceptions during screenshot capture are handled."""
        # Mock screenshot to raise exception
        mock_screen = MagicMock()
        mock_screen.screenshot = MagicMock(side_effect=RuntimeError("Display connection failed"))

        with patch.dict("sys.modules", {"ai_gaming_agent.tools.screen": mock_screen}):
            from ai_gaming_agent.tools.vlm import analyze_screen

            mock_config = MagicMock()
            mock_config.vlm.enabled = True
            mock_config.vlm.provider = "ollama"
            mock_config.vlm.model = "qwen2.5-vl:3b"
            mock_config.vlm.endpoint = "http://localhost:11434"
            mock_get_config.return_value = mock_config

            result = analyze_screen(prompt="What's on screen?")

        assert result["success"] is False
        assert "Screenshot capture failed" in result["error"]
        assert "Display connection failed" in result["error"]

    @patch("ai_gaming_agent.tools.vlm.get_config")
    def test_unsupported_provider_returns_error(self, mock_get_config):
        """Test that unsupported VLM providers return an error."""
        # Mock screenshot
        mock_screen = MagicMock()
        mock_screen.screenshot = MagicMock(return_value={"success": True, "image": "base64imagedata"})

        with patch.dict("sys.modules", {"ai_gaming_agent.tools.screen": mock_screen}):
            from ai_gaming_agent.tools.vlm import analyze_screen

            # Create config and bypass validation
            mock_config = MagicMock()
            mock_config.vlm.enabled = True
            mock_config.vlm.provider = "unsupported_provider"
            mock_get_config.return_value = mock_config

            result = analyze_screen(prompt="Test prompt")

        assert result["success"] is False
        assert "Unsupported VLM provider" in result["error"]
        assert "unsupported_provider" in result["error"]

    @patch("ai_gaming_agent.tools.vlm.get_config")
    def test_successful_analysis_with_ollama(self, mock_get_config):
        """Test successful screen analysis with Ollama."""
        # Mock screenshot with valid base64 data
        mock_screen = MagicMock()
        mock_screen.screenshot = MagicMock(return_value={"success": True, "image": "dGVzdA=="})

        # Mock Ollama client
        mock_client = MagicMock()
        mock_client.chat.return_value = {"message": {"content": "I see a desktop with a terminal window"}}

        mock_ollama = MagicMock()
        mock_ollama.Client.return_value = mock_client

        with patch.dict("sys.modules", {
            "ai_gaming_agent.tools.screen": mock_screen,
            "ollama": mock_ollama
        }):
            from ai_gaming_agent.tools.vlm import analyze_screen

            mock_config = MagicMock()
            mock_config.vlm.enabled = True
            mock_config.vlm.provider = "ollama"
            mock_config.vlm.model = "qwen2.5-vl:3b"
            mock_config.vlm.endpoint = "http://localhost:11434"
            mock_get_config.return_value = mock_config

            result = analyze_screen(prompt="What do you see?")

        assert result["success"] is True
        assert result["response"] == "I see a desktop with a terminal window"
        assert result["prompt"] == "What do you see?"
        assert result["model"] == "qwen2.5-vl:3b"

    @patch("ai_gaming_agent.tools.vlm.get_config")
    def test_monitor_parameter_passed_to_screenshot(self, mock_get_config):
        """Test that monitor parameter is passed to screenshot function."""
        # Mock screenshot with valid base64 data
        mock_screen = MagicMock()
        mock_screen.screenshot = MagicMock(return_value={"success": True, "image": "dGVzdA=="})

        # Mock Ollama
        mock_client = MagicMock()
        mock_client.chat.return_value = {"message": {"content": "Test response"}}
        mock_ollama = MagicMock()
        mock_ollama.Client.return_value = mock_client

        with patch.dict("sys.modules", {
            "ai_gaming_agent.tools.screen": mock_screen,
            "ollama": mock_ollama
        }):
            from ai_gaming_agent.tools.vlm import analyze_screen

            mock_config = MagicMock()
            mock_config.vlm.enabled = True
            mock_config.vlm.provider = "ollama"
            mock_config.vlm.model = "qwen2.5-vl:3b"
            mock_config.vlm.endpoint = "http://localhost:11434"
            mock_get_config.return_value = mock_config

            analyze_screen(prompt="Test", monitor=2)

            # Verify screenshot was called with monitor=2
            mock_screen.screenshot.assert_called_once_with(monitor=2)


class TestAnalyzeWithOllama:
    """Tests for _analyze_with_ollama function."""

    def test_ollama_not_installed_returns_error(self):
        """Test that missing Ollama package returns helpful error."""
        # Make ollama import fail
        import builtins

        from ai_gaming_agent.tools.vlm import _analyze_with_ollama
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "ollama":
                raise ImportError("No module named 'ollama'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            result = _analyze_with_ollama(
                prompt="Test",
                image_b64="dGVzdA==",  # "test" in base64
                model="qwen2.5-vl:3b",
                endpoint="http://localhost:11434",
            )

        assert result["success"] is False
        assert "Ollama Python client not installed" in result["error"]
        assert "pip install" in result["error"]

    def test_successful_ollama_analysis(self):
        """Test successful analysis with Ollama."""
        from ai_gaming_agent.tools.vlm import _analyze_with_ollama

        # Mock Ollama client
        mock_client = MagicMock()
        mock_client.chat.return_value = {"message": {"content": "The image shows a health bar at 75%"}}

        mock_ollama = MagicMock()
        mock_ollama.Client.return_value = mock_client

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            result = _analyze_with_ollama(
                prompt="What is the health percentage?",
                image_b64="dGVzdA==",  # "test" in base64
                model="qwen2.5-vl:3b",
                endpoint="http://localhost:11434",
            )

        assert result["success"] is True
        assert result["response"] == "The image shows a health bar at 75%"
        assert result["model"] == "qwen2.5-vl:3b"
        assert result["prompt"] == "What is the health percentage?"

    def test_ollama_empty_response(self):
        """Test handling of empty response from Ollama."""
        from ai_gaming_agent.tools.vlm import _analyze_with_ollama

        mock_client = MagicMock()
        mock_client.chat.return_value = {"message": {"content": ""}}

        mock_ollama = MagicMock()
        mock_ollama.Client.return_value = mock_client

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            result = _analyze_with_ollama(
                prompt="Test",
                image_b64="dGVzdA==",
                model="qwen2.5-vl:3b",
                endpoint="http://localhost:11434",
            )

        assert result["success"] is False
        assert "empty response" in result["error"]

    def test_ollama_model_not_found(self):
        """Test helpful error message when model is not found."""
        from ai_gaming_agent.tools.vlm import _analyze_with_ollama

        # Create a mock ResponseError that properly inherits from Exception
        class MockResponseError(Exception):
            pass

        mock_client = MagicMock()
        mock_client.chat.side_effect = MockResponseError("model not found")

        mock_ollama = MagicMock()
        mock_ollama.Client.return_value = mock_client
        mock_ollama.ResponseError = MockResponseError

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            result = _analyze_with_ollama(
                prompt="Test",
                image_b64="dGVzdA==",
                model="nonexistent-model",
                endpoint="http://localhost:11434",
            )

        assert result["success"] is False
        assert "Model 'nonexistent-model' not found" in result["error"]
        assert "ollama pull" in result["error"]

    def test_ollama_connection_refused(self):
        """Test connection error handling."""
        from ai_gaming_agent.tools.vlm import _analyze_with_ollama

        # Create mock that raises on Client instantiation
        mock_ollama = MagicMock()
        mock_ollama.Client.side_effect = Exception("connection refused")
        mock_ollama.ResponseError = type("ResponseError", (Exception,), {})

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            result = _analyze_with_ollama(
                prompt="Test",
                image_b64="dGVzdA==",
                model="qwen2.5-vl:3b",
                endpoint="http://localhost:11434",
            )

        assert result["success"] is False
        assert "Cannot connect to Ollama" in result["error"]
        assert "ollama serve" in result["error"]

    def test_ollama_generic_error(self):
        """Test generic error handling."""
        from ai_gaming_agent.tools.vlm import _analyze_with_ollama

        # Create mock with different exception type
        class CustomError(Exception):
            pass

        mock_client = MagicMock()
        mock_client.chat.side_effect = CustomError("Unexpected error")

        mock_ollama = MagicMock()
        mock_ollama.Client.return_value = mock_client
        mock_ollama.ResponseError = type("ResponseError", (Exception,), {})

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            result = _analyze_with_ollama(
                prompt="Test",
                image_b64="dGVzdA==",
                model="qwen2.5-vl:3b",
                endpoint="http://localhost:11434",
            )

        assert result["success"] is False
        assert "VLM analysis failed" in result["error"]
        assert "Unexpected error" in result["error"]

    def test_ollama_base64_decoding(self):
        """Test that base64 image is properly decoded and sent to Ollama."""
        from ai_gaming_agent.tools.vlm import _analyze_with_ollama

        # Create a simple test image data
        test_image_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        test_image_b64 = base64.b64encode(test_image_data).decode()

        mock_client = MagicMock()
        mock_client.chat.return_value = {"message": {"content": "Analysis result"}}

        mock_ollama = MagicMock()
        mock_ollama.Client.return_value = mock_client

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            result = _analyze_with_ollama(
                prompt="Analyze",
                image_b64=test_image_b64,
                model="qwen2.5-vl:3b",
                endpoint="http://localhost:11434",
            )

        assert result["success"] is True

        # Verify the chat call received bytes
        call_args = mock_client.chat.call_args
        messages = call_args[1]["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Analyze"
        assert messages[0]["images"] == [test_image_data]


class TestAnalyzeImage:
    """Tests for analyze_image function (direct image analysis)."""

    @patch("ai_gaming_agent.tools.vlm.get_config")
    def test_vlm_disabled_returns_error(self, mock_get_config):
        """Test that analyze_image returns error when VLM is disabled."""
        from ai_gaming_agent.tools.vlm import analyze_image

        mock_config = MagicMock()
        mock_config.vlm.enabled = False
        mock_get_config.return_value = mock_config

        result = analyze_image(image_b64="dGVzdA==", prompt="What do you see?")

        assert result["success"] is False
        assert "VLM is not enabled" in result["error"]

    @patch("ai_gaming_agent.tools.vlm.get_config")
    def test_unsupported_provider(self, mock_get_config):
        """Test that unsupported provider returns error."""
        from ai_gaming_agent.tools.vlm import analyze_image

        mock_config = MagicMock()
        mock_config.vlm.enabled = True
        mock_config.vlm.provider = "unsupported"
        mock_get_config.return_value = mock_config

        result = analyze_image(image_b64="dGVzdA==", prompt="Test")

        assert result["success"] is False
        assert "Unsupported VLM provider" in result["error"]

    @patch("ai_gaming_agent.tools.vlm.get_config")
    def test_successful_analysis(self, mock_get_config):
        """Test successful image analysis."""
        from ai_gaming_agent.tools.vlm import analyze_image

        mock_config = MagicMock()
        mock_config.vlm.enabled = True
        mock_config.vlm.provider = "ollama"
        mock_config.vlm.model = "qwen2.5-vl:3b"
        mock_config.vlm.endpoint = "http://localhost:11434"
        mock_get_config.return_value = mock_config

        # Mock Ollama client
        mock_client = MagicMock()
        mock_client.chat.return_value = {"message": {"content": "A red apple on a table"}}

        mock_ollama = MagicMock()
        mock_ollama.Client.return_value = mock_client

        with patch.dict("sys.modules", {"ollama": mock_ollama}):
            result = analyze_image(image_b64="dGVzdA==", prompt="What fruit is in the image?")

        assert result["success"] is True
        assert result["response"] == "A red apple on a table"
        assert result["prompt"] == "What fruit is in the image?"
        assert result["model"] == "qwen2.5-vl:3b"
