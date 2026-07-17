from app.services.ai.context_builder import build_task_context
from app.services.ai.claude_client import call_claude
from app.services.ai.response_parser import parse_claude_response

from app.ai_agents.tools import get_tasks

class ChatAgent:

    async def run(self, user_id, message, db):

        # ---------------------------------
        # Retrieve user tasks
        # ---------------------------------

        tasks = get_tasks(db, user_id)

        # ---------------------------------
        # Context Engineering Layer
        # ---------------------------------
        # Productivity stats are NOT precomputed here - get_productivity_stats
        # is exposed to Claude as a native tool (claude_client.py) so the model
        # decides whether it needs them, rather than always receiving them
        # whether relevant or not.

        task_context = build_task_context(tasks)

        context = {
            "tasks": task_context
        }

        # ---------------------------------
        # Claude API Call (tasks passed through for tool execution)
        # ---------------------------------

        raw_response = call_claude(context, message, tasks)

        # ---------------------------------
        # Structured Output Parser
        # ---------------------------------

        parsed_response = parse_claude_response(raw_response)

        return parsed_response
