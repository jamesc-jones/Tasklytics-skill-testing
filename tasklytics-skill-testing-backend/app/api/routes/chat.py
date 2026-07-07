from fastapi import APIRouter, Depends
from app.models.chat_models import (ChatRequest, ChatResponse)

from app.database import get_db

from app.models import User

from app.auth.auth_dependencies import get_current_user

from app.ai_agents.chat_agent import ChatAgent


# from app.services.ai.context_builder import build_task_context
# from app.services.ai.claude_client import call_claude
# from app.services.ai.response_parser import parse_claude_response
# from app.services.task_service import get_user_tasks

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
        request: ChatRequest,
        db=Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    agent = ChatAgent()

    response = await agent.run(
        user_id=current_user.id,
        message=request.message,
        db=db
    )

    return response




    # tasks = get_user_tasks(db, current_user.id)

    # task_context = build_task_context(tasks)

    # raw_response = call_claude(task_context, request.message)

    # parsed = parse_claude_response(raw_response)

    # return parsed