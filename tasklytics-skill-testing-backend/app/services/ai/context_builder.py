def build_task_context(tasks):
    if not tasks:
        return "No tasks available."

    formatted_tasks = []
    for task in tasks:
        due = task.due_date.strftime("%Y-%m-%d") if task.due_date else "No due date"

        formatted_tasks.append(
            f"- {task.title} (Priority: {task.priority}, Due: {due})"
        )

    return "\n".join(formatted_tasks)