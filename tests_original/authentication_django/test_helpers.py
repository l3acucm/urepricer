import pytest
from unittest.mock import Mock, patch
import requests
import json

from helpers.utils import (
    CustomJSON,
    format_slack_message,
    send_slack_validator_notification,
)
from helpers.exceptional_handling import handle_exceptions


class TestCustomJSON:

    def test_simple_key_access(self):
        data = CustomJSON({"key": "value", "number": 123})

        assert data.get("key") == "value"
        assert data.get("number") == 123

    def test_nested_key_access(self):
        data = CustomJSON({"level1": {"level2": {"level3": "deep_value"}}})

        assert data.get("level1.level2.level3") == "deep_value"

    def test_array_access(self):
        data = CustomJSON({"array": ["item0", "item1", {"nested": "value"}]})

        assert data.get("array.0") == "item0"
        assert data.get("array.2.nested") == "value"

    def test_missing_key_returns_none(self):
        data = CustomJSON({"key": "value"})

        assert data.get("missing_key") is None
        assert data.get("key.missing_nested") is None

    def test_invalid_array_index(self):
        data = CustomJSON({"array": ["item0", "item1"]})

        assert data.get("array.5") is None

    def test_type_error_handling(self):
        data = CustomJSON({"string": "value"})

        # Trying to access string as dict should return None
        assert data.get("string.key") is None


class TestSlackUtilities:

    def test_format_slack_message_basic(self):
        result = format_slack_message(
            title="Test Alert",
            message=["Error message", "Additional info"],
            emoji="warning",
            environment="test",
        )

        assert "blocks" in result
        assert len(result["blocks"]) >= 3

        # Check header block
        header_block = result["blocks"][0]
        assert (
            ":warning: :warning:   *Test Alert*   :warning: :warning:"
            in header_block["text"]["text"]
        )

    def test_format_slack_message_with_module(self):
        result = format_slack_message(
            title="Test Alert",
            message=["Error message"],
            module="TestModule",
            environment="test",
        )

        # Should have header, module, environment, details, and divider blocks
        assert len(result["blocks"]) >= 4

        # Check if module block exists
        module_found = any(
            ":gear: :gear:  TestModule  :gear: :gear:"
            in block.get("text", {}).get("text", "")
            for block in result["blocks"]
        )
        assert module_found

    @patch("traceback.format_exc")
    def test_format_slack_message_with_stack_trace(self, mock_format_exc):
        mock_format_exc.return_value = (
            "Traceback (most recent call last):\n  File test.py, line 1"
        )

        result = format_slack_message(
            title="Test Alert",
            message=["Error message"],
            print_stack_trace=True,
            environment="test",
        )

        # Should include stack trace block
        stack_trace_found = any(
            "Stack Trace:" in block.get("text", {}).get("text", "")
            for block in result["blocks"]
        )
        assert stack_trace_found

    @patch("requests.post")
    def test_send_slack_validator_notification_success(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        send_slack_validator_notification("TestError", "production")

        mock_post.assert_called_once()

        # Check the call arguments
        call_args = mock_post.call_args
        assert call_args[1]["data"]  # JSON data should be present

    @patch("requests.post")
    def test_send_slack_validator_notification_failure(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            send_slack_validator_notification("TestError", "production")

        assert "400" in str(exc_info.value)


class TestExceptionalHandling:

    @patch("helpers.exceptional_handling.send_slack_validator_notification")
    def test_handle_exceptions_decorator_success(self, mock_send_slack):
        @handle_exceptions
        def test_function():
            return "success"

        result = test_function()

        assert result == "success"
        mock_send_slack.assert_not_called()

    @patch("helpers.exceptional_handling.send_slack_validator_notification")
    @patch("helpers.exceptional_handling.settings.DEBUG", True)
    def test_handle_exceptions_decorator_with_exception(self, mock_send_slack):
        @handle_exceptions
        def test_function():
            raise ValueError("Test error")

        result = test_function()

        assert result is None
        mock_send_slack.assert_called_once_with("ValueError", "local")

    @patch("helpers.exceptional_handling.send_slack_validator_notification")
    @patch("helpers.exceptional_handling.settings.DEBUG", False)
    def test_handle_exceptions_decorator_production_environment(self, mock_send_slack):
        @handle_exceptions
        def test_function():
            raise RuntimeError("Production error")

        result = test_function()

        assert result is None
        mock_send_slack.assert_called_once_with("RuntimeError", "production")

    @patch("helpers.exceptional_handling.send_slack_validator_notification")
    def test_handle_exceptions_decorator_with_args(self, mock_send_slack):
        @handle_exceptions
        def test_function(arg1, arg2, kwarg1=None):
            if arg1 == "error":
                raise Exception("Test exception")
            return f"{arg1}-{arg2}-{kwarg1}"

        # Test success case
        result = test_function("test", "args", kwarg1="kwargs")
        assert result == "test-args-kwargs"
        mock_send_slack.assert_not_called()

        # Test exception case
        result = test_function("error", "args", kwarg1="kwargs")
        assert result is None
        mock_send_slack.assert_called_once()
