from app.ai.client import call_llm
from app.ai.prompts import task_insight_prompt

def get_task_insights(tasks: list[dict]):
    prompt = task_insight_prompt(tasks)
    return call_llm(prompt)