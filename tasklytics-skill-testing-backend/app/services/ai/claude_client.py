import os
import anthropic

client = anthropic.Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

print("ANTHROPIC KEY:", os.getenv("ANTHROPIC_API_KEY"))

def call_claude(tasks_context, user_message):
    prompt= f"""
    You are a productivity assistant inside Tasklytics.
    
    Use ONLY the provided tasks.
    
    Return STRICT JSON ONLY with this structure:
    {{
    "response": "string",
    "priority_tasks": ["string"],
    "insight": "string"
    }}
    
    If no tasks exist, return empty arrays.
    
    Tasks:
    {tasks_context}
    
    User message:
    {user_message}
    """

    print("STEP 1: calling Claude")

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=300,
        temperature=0.2,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    print("STEP 2: Claude returned")


    return response.content[0].text