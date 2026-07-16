import os
import json
import logging
import anthropic

from app.services.ai.prompts import CHAT_PROMPT_VERSION, build_chat_prompt

client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

logger = logging.getLogger("tasklytics.ai.usage")

def call_claude(tasks_context, user_message):

    context_json = json.dumps(
        tasks_context,
        indent=2
    )

    prompt = build_chat_prompt(context_json, user_message)

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=300,
        temperature=0.2,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    usage = response.usage
    logger.info(
        "claude_usage prompt_version=%s input_tokens=%s output_tokens=%s",
        CHAT_PROMPT_VERSION,
        usage.input_tokens,
        usage.output_tokens,
    )

    return response.content[0].text