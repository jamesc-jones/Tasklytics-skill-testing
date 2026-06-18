def format_tasks_for_ai(tasks):
    """
    Converts task objects into clean structured data for LLM input
    """

    formatted = []

    for t in tasks:
        formatted.append({
            "title": t.title,
            "completed": t.completed,
            "priority": getattr(t, "priority", "medium")
        })

    return formatted