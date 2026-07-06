from fastapi import APIRouter, Depends
from app.models.chat_models import ChatRequest, ChatResponse
from app.services.ai.context_builder import build_task_context
from app.services.ai.claude_client import call_claude
from app.services.ai.response_parser import parse_claude_response

from app.database import get_db

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, db=Depends(get_db)):
    tasks = get_user_tasks(db, request.user_id)

    task_context = build_task_context(tasks)

    raw_response = call_claude(task_context, request.message)

    parsed = parse_claude_response(raw_response)

    return parsed