from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def mock_call_llm(monkeypatch):
    """Stubs the legacy Together AI call so no network request is ever made.

    Patched at app.ai.service.call_llm -- app/ai/service.py does
    `from app.ai.client import call_llm`, binding its own local name at
    import time, same pattern as chat_agent.py's call_claude binding
    (see tests/conftest.py's mock_call_claude for the original precedent).
    """
    mock = MagicMock(return_value="Focus on the high-priority task first.")
    monkeypatch.setattr("app.ai.service.call_llm", mock)
    return mock


class TestLegacyAiTaskInsights:
    def test_authenticated_user_gets_insight(self, client, auth_headers, mock_call_llm):
        resp = client.post(
            "/ai/task-insights",
            json={"tasks": [
                {"title": "Ship report", "completed": False, "priority": "high", "due_date": None}
            ]},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["insight"] == "Focus on the high-priority task first."
        assert mock_call_llm.called

    def test_rejects_unauthenticated_request(self, client, mock_call_llm):
        resp = client.post(
            "/ai/task-insights",
            json={"tasks": []},
        )
        assert resp.status_code in (401, 403)
        assert not mock_call_llm.called

    def test_rejects_malformed_task_list(self, client, auth_headers, mock_call_llm):
        resp = client.post(
            "/ai/task-insights",
            json={"tasks": [{"title": "missing required fields"}]},
            headers=auth_headers,
        )
        assert resp.status_code == 422
