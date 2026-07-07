from app.services.ai.context_builder import build_task_context
from app.services.ai.claude_client import call_claude
from app.services.ai.response_parser import parse_claude_response

from app.ai_agents.tools import (
        get_tasks,
        get_productivity_stats
)

class ChatAgent:

    async def run(self, user_id, message, db):

        # ---------------------------------
        # Tool 1:
        # Retrieve user tasks
        # ---------------------------------

        tasks = get_tasks(db, user_id)

        # ---------------------------------
        # Tool 2:
        # Calculate productivity statistics
        # ---------------------------------

        stats = get_productivity_stats(tasks)

        # ---------------------------------
        # Context Engineering Layer
        # ---------------------------------

        task_context = build_task_context(tasks)

        context = {
            "tasks": task_context,
            "stats": stats
        }

        # ---------------------------------
        # Claude API Call
        # ---------------------------------

        raw_response = call_claude(context, message)

        # ---------------------------------
        # Structured Output Parser
        # ---------------------------------

        parsed_response = parse_claude_response(raw_response)

        return parsed_response
