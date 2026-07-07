from app.models.task import Task

def get_tasks(db, user_id):

    tasks = (
        db.query(Task)
        .filter(Task.user_id == user_id)
        .all()
    )

    return tasks

def get_productivity_stats(tasks):

    total = len(tasks)

    completed = len(
        [
            task
            for task in tasks
            if task.completed
        ]
    )

    return {
        'total': total,
        'completed': completed,
        'completion_rate':
            completed / total if total else 0
    }