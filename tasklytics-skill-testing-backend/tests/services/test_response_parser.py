from app.services.ai.response_parser import parse_claude_response


class TestValidResponse:
    def test_valid_json_passes_schema_validation(self):
        raw = '{"response": "Focus on X", "priority_tasks": ["X"], "insight": "Y"}'
        result = parse_claude_response(raw)

        assert result["response"] == "Focus on X"
        assert result["priority_tasks"] == ["X"]
        assert result["insight"] == "Y"
        assert "error" not in result

    def test_strips_markdown_json_fence(self):
        raw = '```json\n{"response": "ok", "priority_tasks": [], "insight": null}\n```'
        result = parse_claude_response(raw)

        assert result["response"] == "ok"
        assert "error" not in result


class TestMalformedJson:
    def test_invalid_json_falls_back_gracefully(self):
        raw = "not json at all"
        result = parse_claude_response(raw)

        assert result["response"] == raw
        assert result["priority_tasks"] == []
        assert "error" in result


class TestSchemaValidationFailure:
    """The gap this file exists to close: valid JSON that doesn't match
    ChatResponse must not reach FastAPI's response_model as an unhandled
    500 - it should hit the same graceful fallback as malformed JSON."""

    def test_valid_json_missing_required_field_falls_back_gracefully(self):
        # priority_tasks is required by ChatResponse and is missing here
        raw = '{"response": "ok"}'
        result = parse_claude_response(raw)

        assert result["priority_tasks"] == []
        assert "error" in result
        assert result["response"] == raw  # original raw text preserved in the fallback

    def test_wrong_type_falls_back_gracefully(self):
        # priority_tasks must be a list of strings, not a single string
        raw = '{"response": "ok", "priority_tasks": "not a list", "insight": null}'
        result = parse_claude_response(raw)

        assert "error" in result
        assert result["priority_tasks"] == []
