from app.models.message import MessageModel
from app.repositories.message_repository import MessageRepository
from app.rag.pipeline.qa_pipeline import QAPipeline
from app.services.session_service import SessionService
from app.utils.id_utils import generate_id


class ChatService:
    def __init__(self) -> None:
        self.qa_pipeline = QAPipeline()
        self.message_repository = MessageRepository()
        self.session_service = SessionService()

    async def ask_question(self, request, user_id: str):
        if request.session_id:
            session = await self.session_service.get_session(request.session_id, user_id)
            if session is None:
                raise ValueError("Session not found.")
        result = self.qa_pipeline.run(
            question=request.question,
            user_id=user_id,
            session_id=request.session_id,
            scope=request.scope,
            selected_document_ids=request.selected_document_ids,
        )
        user_message = MessageModel(
            id=generate_id("msg"),
            session_id=request.session_id or "no_session",
            owner_user_id=user_id,
            role="user",
            content=request.question,
        )
        assistant_message = MessageModel(
            id=generate_id("msg"),
            session_id=request.session_id or "no_session",
            owner_user_id=user_id,
            role="assistant",
            content=result["answer"],
            sources=result["sources"],
        )
        await self.message_repository.create_message(user_message)
        await self.message_repository.create_message(assistant_message)
        if request.session_id:
            await self.session_service.touch_session(request.session_id)
        return result
