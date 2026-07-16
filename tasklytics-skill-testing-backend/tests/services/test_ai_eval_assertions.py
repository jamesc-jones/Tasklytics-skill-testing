"""Proves the AI eval assertion functions (tests/ai_eval/assertions.py) actually
discriminate between good and bad output, using synthetic data only - no real
Claude API calls. This is what makes the eval suite trustworthy: an assertion
that always passes regardless of input isn't testing anything.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "ai_eval"))

from assertions import ASSERTION_REGISTRY  # noqa: E402


SCENARIO = {
    "tasks_context": {
        "tasks": "- Finish quarterly report (Priority: high, Due: 2026-07-01)",
    },
}


class TestNonEmptyResponse:
    def test_passes_on_real_content(self):
        ok, _ = ASSERTION_REGISTRY["non_empty_response"]({"response": "Focus on the report."}, SCENARIO)
        assert ok is True

    def test_fails_on_empty_string(self):
        ok, _ = ASSERTION_REGISTRY["non_empty_response"]({"response": ""}, SCENARIO)
        assert ok is False

    def test_fails_on_missing_key(self):
        ok, _ = ASSERTION_REGISTRY["non_empty_response"]({}, SCENARIO)
        assert ok is False


class TestNoParseError:
    def test_passes_when_no_error_key(self):
        ok, _ = ASSERTION_REGISTRY["no_parse_error"]({"response": "ok"}, SCENARIO)
        assert ok is True

    def test_fails_when_error_key_present(self):
        ok, msg = ASSERTION_REGISTRY["no_parse_error"](
            {"response": "raw text", "error": "Expecting value: line 1 column 1"}, SCENARIO
        )
        assert ok is False
        assert "Expecting value" in msg


class TestPriorityTasksNonEmpty:
    def test_passes_with_items(self):
        ok, _ = ASSERTION_REGISTRY["priority_tasks_non_empty"](
            {"priority_tasks": ["Finish quarterly report"]}, SCENARIO
        )
        assert ok is True

    def test_fails_when_empty(self):
        ok, _ = ASSERTION_REGISTRY["priority_tasks_non_empty"]({"priority_tasks": []}, SCENARIO)
        assert ok is False


class TestMentionsARealTask:
    def test_passes_when_task_title_referenced(self):
        ok, _ = ASSERTION_REGISTRY["mentions_a_real_task"](
            {"response": "You should finish quarterly report first.", "priority_tasks": []},
            SCENARIO,
        )
        assert ok is True

    def test_fails_when_response_is_generic_and_unrelated(self):
        ok, _ = ASSERTION_REGISTRY["mentions_a_real_task"](
            {"response": "Have a great day and stay productive!", "priority_tasks": []},
            SCENARIO,
        )
        assert ok is False
