from pydantic import BaseModel
from typing import List, Optional

class ChatRequest(BaseModel):
    message: str
    user_id: int

class ChatResponse(BaseModel):
    response: str
    priority_tasks: List[str]
    insight: Optional[str]