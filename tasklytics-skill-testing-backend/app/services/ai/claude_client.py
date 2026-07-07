import os
import anthropic

client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# print("API KEY:", os.getenv("ANTHROPIC_API_KEY")) used to debug issues

def call_claude(tasks_context, user_message):
    prompt = f"""
    You are a productivity assistant inside Tasklytics.

    Return ONLY raw JSON.
    DO NOT use markdown.
    DO NOT wrap in ```.

    Return STRICT JSON with this structure:
    {{
    "response": "string",
    "priority_tasks": ["string"],
    "insight": "string"
    }}

    Tasks:
    {tasks_context}

    User message:
    {user_message}
    
    Focus on:
    - What tasks matter most today
    - What should be done first
    - Any productivity insights    
    """

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

    return response.content[0].text