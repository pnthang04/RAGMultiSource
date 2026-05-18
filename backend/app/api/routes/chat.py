from fastapi import APIRouter, Depends

from app.api.deps import get_chat_service, get_current_user_id
from app.schemas.chat_schema import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

router = APIRouter()


@router.post("", response_model=ChatResponse)
async def ask_chat(
    request: ChatRequest,
    user_id: str = Depends(get_current_user_id),
    service: ChatService = Depends(get_chat_service),
):
    result = await service.ask_question(request=request, user_id=user_id)
    return ChatResponse(answer=result["answer"], sources=result["sources"], raw_contexts=result["raw_contexts"])
