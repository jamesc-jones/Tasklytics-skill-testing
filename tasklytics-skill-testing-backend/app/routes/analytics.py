from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Task
from app.auth.auth_dependencies import get_current_user

router = APIRouter(prefix="/tasks", tags=["Analytics"])

@router.get("/analytics")
def get_task_analytics(
        db: Session = Depends(get_db),
        user = Depends(get_current_user)
):
    tasks = db.query(Task).filter(Task.owner_id == user.id).all()

    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.completed])

    completion_rate = (
        (completed_tasks / total_tasks * 100)
        if total_tasks > 0 else 0
    )

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "completion_rate": round(completion_rate, 2)
    }