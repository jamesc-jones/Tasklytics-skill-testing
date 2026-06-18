from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models
from app.auth.auth_dependencies import get_current_user

from app.schemas import TaskCreate, TaskUpdate

from app.database import get_db

from app.utils.responses import success_response, error_response

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# Get User Tasks
@router.get("/")
def get_tasks(
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):

    if current_user.role == "admin":
        tasks = db.query(models.Task).all()
    else:
        tasks = db.query(models.Task).filter(
            models.Task.user_id == current_user.id
        ).all()

    return success_response("Tasks fetched successfully", tasks)



# Create a Task
@router.post("/")
def create_task(
        task: TaskCreate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):

    new_task = models.Task(
        title=task.title,
        description=task.description,
        priority=task.priority,
        user_id=current_user.id
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return success_response("Task created successfully", new_task)


# Update a Task
@router.put("/{task_id}")
def update_task(
        task_id: int,
        task_data: TaskUpdate,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):

    query = db.query(models.Task).filter(models.Task.id == task_id)

    if current_user.role != "admin":
        query = query.filter(models.Task.user_id == current_user.id)

    db_task = query.first()

    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    db_task.title = task_data.title
    db_task.description = task_data.description
    db_task.completed = task_data.completed

    db.commit()
    db.refresh(db_task)

    return success_response("Task updated successfully", db_task)


# Delete a Task
@router.delete("/{task_id}")
def delete_task(
        task_id: int,
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):

    query = db.query(models.Task).filter(models.Task.id == task_id)

    if current_user.role != "admin":
        query = query.filter(models.Task.user_id == current_user.id)

    db_task = query.first()

    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(db_task)
    db.commit()

    return success_response("Task deleted successfully")


@router.get("/analytics")
def get_analytics(
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user)
):

    base_query = db.query(models.Task)

    # role-based filtering
    if current_user.role != "admin":
        base_query = base_query.filter(
            models.Task.user_id == current_user.id
        )

    tasks = base_query.all()

    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.completed])
    pending_tasks = total_tasks - completed_tasks

    high_priority = len([t for t in tasks if t.priority == "high"])
    medium_priority = len([t for t in tasks if t.priority == "medium"])
    low_priority = len([t for t in tasks if t.priority == "low"])

    analytics_data = {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "pending_tasks": pending_tasks,
            "priority_breakdown": {
                "high": high_priority,
                "medium": medium_priority,
                "low": low_priority
            },
            "completion_rate": round(
                (completed_tasks / total_tasks) * 100, 2
            ) if total_tasks > 0 else 0,
    }

    return success_response(
    "Analytics fetched successfully",
            analytics_data
    )