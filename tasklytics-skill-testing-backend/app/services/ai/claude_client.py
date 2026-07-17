import os
import json
import time
import logging
import anthropic

from app.services.ai.prompts import CHAT_PROMPT_VERSION, CHAT_SYSTEM_PROMPT, build_chat_user_message
from app.ai_agents.tools import get_productivity_stats

client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

logger = logging.getLogger("tasklytics.ai.usage")

MAX_RETRIES = 3
MAX_TOOL_ITERATIONS = 5

GET_PRODUCTIVITY_STATS_TOOL = {
    "name": "get_productivity_stats",
    "description": "Get the current user's productivity statistics: total tasks, completed tasks, and completion rate.",
    "input_schema": {
        "type": "object",
        "properties": {}
    }
}


def _create_with_retry(messages):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=300,
                temperature=0.2,
                system=CHAT_SYSTEM_PROMPT,
                tools=[GET_PRODUCTIVITY_STATS_TOOL],
                messages=messages,
            )
        except (anthropic.RateLimitError, anthropic.APITimeoutError, anthropic.APIError) as e:
            if attempt == MAX_RETRIES:
                raise
            backoff_seconds = 2 ** (attempt - 1)
            logger.warning(
                "claude_api_retry attempt=%s/%s error=%s backoff=%ss",
                attempt, MAX_RETRIES, type(e).__name__, backoff_seconds,
            )
            time.sleep(backoff_seconds)


def _log_usage(response):
    usage = response.usage
    logger.info(
        "claude_usage prompt_version=%s input_tokens=%s output_tokens=%s stop_reason=%s",
        CHAT_PROMPT_VERSION,
        usage.input_tokens,
        usage.output_tokens,
        response.stop_reason,
    )


def _execute_tool(tool_use_block, tasks):
    if tool_use_block.name == "get_productivity_stats":
        return get_productivity_stats(tasks)
    return {"error": f"Unknown tool: {tool_use_block.name}"}


def _append_tool_result(messages, response, tasks):
    tool_use_block = next(block for block in response.content if block.type == "tool_use")
    tool_output = _execute_tool(tool_use_block, tasks)

    messages.append({"role": "assistant", "content": response.content})
    messages.append({
        "role": "user",
        "content": [{
            "type": "tool_result",
            "tool_use_id": tool_use_block.id,
            "content": json.dumps(tool_output),
        }],
    })


def _extract_text(response):
    text_block = next((block for block in response.content if block.type == "text"), None)
    if text_block is None:
        return json.dumps({
            "response": "No response generated.",
            "priority_tasks": [],
            "insight": "Claude returned no text content."
        })
    return text_block.text


def _truncated_fallback():
    logger.warning("claude_response_truncated prompt_version=%s", CHAT_PROMPT_VERSION)
    return json.dumps({
        "response": "The response was too long and got cut off. Please try a shorter question.",
        "priority_tasks": [],
        "insight": "Response truncated (max_tokens)."
    })


def call_claude(tasks_context, user_message, tasks):

    context_json = json.dumps(
        tasks_context,
        indent=2
    )

    user_content = build_chat_user_message(context_json, user_message)
    messages = [{"role": "user", "content": user_content}]

    response = _create_with_retry(messages)
    _log_usage(response)

    iterations = 0
    while response.stop_reason == "tool_use" and iterations < MAX_TOOL_ITERATIONS:
        _append_tool_result(messages, response, tasks)
        response = _create_with_retry(messages)
        _log_usage(response)
        iterations += 1

    if response.stop_reason == "max_tokens":
        return _truncated_fallback()

    if response.stop_reason == "end_turn":
        return _extract_text(response)

    # Safe fallback for any other stop_reason (e.g. stop_sequence, or the
    # tool-iteration cap being hit while Claude still wants to call again)
    logger.warning("claude_unexpected_stop_reason stop_reason=%s", response.stop_reason)
    return _extract_text(response)
