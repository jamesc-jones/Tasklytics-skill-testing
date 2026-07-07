from app.services.ai.claude_client import call_claude

class InsightAgent:

    async def analyze(self, tasks):

        prompt = f"""

Analyze these tasks.

Find:

- patterns
- bottlenecks
- productivity improvements

Tasks:

{tasks}

"""

        return await call_claude(prompt)