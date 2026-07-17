import json

from app.models.chat_models import ChatResponse


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

        parsed = json.loads(cleaned_text)

        # Validate against the same schema FastAPI enforces at the route
        # boundary (response_model=ChatResponse) - catches a schema mismatch
        # here, with the existing graceful fallback, instead of letting an
        # unhandled 500 surface at the API layer.
        validated = ChatResponse(**parsed)
        return validated.model_dump()

    except Exception as e:

        return {
            "response": raw_text,
            "priority_tasks": [],
            "insight": "Could not parse structured output.",
            "error": str(e)
        }