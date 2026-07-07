import json

from sqlalchemy.dialects.mysql.reflection import cleanup_text


def parse_claude_response(raw_text):
    try:

        cleaned_text = raw_text.strip()

        # Remove Claude markdown JSON wrapper
        if cleaned_text.startswith("```json"):

            cleaned_text = (
                cleaned_text
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

        return json.loads(cleaned_text)

    except Exception as e:

        return {
            "response": raw_text,
            "priority_tasks": [],
            "insight": "Could not parse structured output.",
            "error": str(e)
        }