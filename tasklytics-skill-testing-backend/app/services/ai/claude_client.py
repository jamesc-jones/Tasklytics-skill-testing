import os
import anthropic

client = anthropic.Anthropic(
    api_key=os.getenv("CLAUDE_API_KEY")
)

def call_claude(tasks_context, user_message):
    prompt= f"""
    You are a productivity assistant inside Tasklytics.
    
    Use ONLY the provided tasks.
    
    Return structured JSON:
    {{
    "response": "...",
    "priority_tasks": [],
    "insight": ""
    }}
    
    Tasks:
    {tasks_context}
    
    User message:
    {user_message}
    """

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=500,
        temperature=0.2,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return response.content[0].text