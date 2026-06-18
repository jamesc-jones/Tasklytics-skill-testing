def task_insight_prompt(tasks: list[dict]):
    return f"""
You are a senior productivity AI assistant.

Analyze the following tasks:

{tasks}

Return your answer in clear markdown with headings.

Include:

### 1. Priority order
- Rank task based on urgency and importance

### 2. What to do today
- Clear, actionable steps

### 3. Productivity patterns
- Any patterns in workload, priorities, or behavior

### 4. Risks 
- Deadlines, overload, or missed priorities

### 5. Recommendation
- One specific, high-impact action

Rules:
- Be concise
- Avoid generic advice
- Be practical and specific


"""
