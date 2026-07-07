from app.services.ai.context_builder import build_task_context
from app.services.ai.claude_client import call_claude
from app.ai_agents.tools import (
        get_tasks,
        get_productivity_stats
)

class ChatAgent:

    def __init__(self):
        pass

    async def run(self, user_id, message, db):

        tasks = get_tasks(db, user_id)

        stats = get_productivity_stats(tasks)

        context = {
            "tasks": tasks,
            "stats": stats,
        }

        response = await call_claude(
            message,
            context
        )

        return response