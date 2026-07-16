import logging
from unittest.mock import MagicMock

from app.services.ai.claude_client import call_claude
from app.services.ai.prompts import CHAT_PROMPT_VERSION


class TestCallClaudeUsageLogging:
    def test_logs_prompt_version_and_token_usage(self, monkeypatch, caplog):
        fake_response = MagicMock()
        fake_response.content = [MagicMock(text='{"response": "ok"}')]
        fake_response.usage.input_tokens = 123
        fake_response.usage.output_tokens = 45

        mock_create = MagicMock(return_value=fake_response)
        monkeypatch.setattr(
            "app.services.ai.claude_client.client.messages.create", mock_create
        )

        with caplog.at_level(logging.INFO, logger="tasklytics.ai.usage"):
            result = call_claude({"tasks": []}, "What should I do today?")

        assert result == '{"response": "ok"}'
        assert mock_create.called

        assert CHAT_PROMPT_VERSION in caplog.text
        assert "input_tokens=123" in caplog.text
        assert "output_tokens=45" in caplog.text


class TestCallClaudePromptContent:
    def test_prompt_includes_task_context_and_user_message(self, monkeypatch):
        fake_response = MagicMock()
        fake_response.content = [MagicMock(text="{}")]
        fake_response.usage.input_tokens = 1
        fake_response.usage.output_tokens = 1

        mock_create = MagicMock(return_value=fake_response)
        monkeypatch.setattr(
            "app.services.ai.claude_client.client.messages.create", mock_create
        )

        call_claude({"tasks": [{"title": "Ship the report"}]}, "focus me")

        sent_prompt = mock_create.call_args.kwargs["messages"][0]["content"]
        assert "Ship the report" in sent_prompt
        assert "focus me" in sent_prompt
