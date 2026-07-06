import json

def parse_claude_response(raw_text):
    try:
        return json.loads(raw_text)
    except Exception as e:
        return {
            "response": raw_text,
            "priority_tasks": [],
            "insight": "Could not parse structured output.",
            "error": str(e)
        }