from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.ai.service import get_task_insights
from app.ai.utils import format_tasks_for_ai
from app.auth.auth_dependencies import get_current_user

router = APIRouter(prefix="/ai", tags=["AI"])

class TaskModel(BaseModel):
    title: str
    completed: bool
    priority: str
    due_date: str | None = None

class TaskRequest(BaseModel):
    tasks: list[TaskModel]

@router.post("/task-insights")
def task_insights(request: TaskRequest, user = Depends(get_current_user)):

    _ = user

    tasks = format_tasks_for_ai(request.tasks)
    result = get_task_insights(tasks)

    return{
        "success": True,
        "insight": result
    }