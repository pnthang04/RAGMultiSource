from app.core.constants import RETRIEVAL_SCOPE_AUTO, RETRIEVAL_SCOPE_NEED_CLARIFICATION
from app.rag.generation.openai_llm import OpenAILLMService
from app.rag.retrieval.resolvers import DocumentResolver, ScopeResolver
from app.rag.retrieval.retriever import Retriever
from app.schemas.common_schema import SourceItem
from langsmith import traceable


class QAPipeline:
    def __init__(self) -> None:
        self.scope_resolver = ScopeResolver()
        self.document_resolver = DocumentResolver()
        self.retriever = Retriever()
        self.llm = OpenAILLMService()

    async def run(
        self,
        question: str,
        user_id: str,
        session_id: str | None,
        scope: str,
        selected_document_ids: list[str] | None = None,
        conversation_state: dict | None = None,
    ) -> dict:
        return await self._run_traced(question, user_id, session_id, scope, selected_document_ids, conversation_state)

    @traceable(name="rag_qa_pipeline")
    async def _run_traced(
        self,
        question: str,
        user_id: str,
        session_id: str | None,
        scope: str,
        selected_document_ids: list[str] | None = None,
        conversation_state: dict | None = None,
    ) -> dict:
        resolution = self.scope_resolver.resolve(
            question=question,
            user_id=user_id,
            session_id=session_id,
            scope=scope if scope != RETRIEVAL_SCOPE_AUTO else RETRIEVAL_SCOPE_AUTO,
            selected_document_ids=selected_document_ids,
            conversation_state=conversation_state,
        )
        document_resolution = await self.document_resolver.resolve(
            scope=resolution.scope,
            metadata_filter=resolution.metadata_filter,
            user_id=user_id,
            session_id=session_id,
            detected_filename=resolution.detected_filename,
            detected_procedure_title=resolution.detected_procedure_title,
            selected_document_ids=selected_document_ids,
            conversation_state=conversation_state,
        )

        if resolution.scope == RETRIEVAL_SCOPE_NEED_CLARIFICATION or document_resolution.needs_clarification:
            answer = "Mình cần bạn làm rõ tài liệu muốn hỏi: file vừa upload, file cũ, tài liệu hệ thống, hoặc một file cụ thể."
            contexts: list[dict] = []
        else:
            contexts = []
            if resolution.should_retrieve:
                contexts = self.retriever.retrieve(question=question, where_filter=document_resolution.metadata_filter)
            answer = self.llm.generate_answer(question=question, contexts=contexts)

        sources = [
            SourceItem(
                document_id=item["metadata"].get("document_id", ""),
                chunk_id=item["metadata"].get("chunk_id", item.get("id", "")),
                filename=item["metadata"].get("filename", ""),
                source_type=item["metadata"].get("source_type", ""),
                procedure_title=item["metadata"].get("procedure_title"),
                page_number=item["metadata"].get("page_number"),
                page_source=item["metadata"].get("page_source"),
                section_title=item["metadata"].get("section_title"),
                score=item.get("similarity"),
                visibility=item["metadata"].get("visibility"),
                owner_user_id=item["metadata"].get("owner_user_id"),
                session_id=item["metadata"].get("session_id"),
            ).model_dump()
            for item in contexts
        ]
        return {
            "answer": answer,
            "sources": sources,
            "raw_contexts": contexts,
            "scope": resolution.scope,
            "scope_resolution": resolution.model_dump(),
            "document_resolution": document_resolution.model_dump(),
            "retrieval_filter": document_resolution.metadata_filter,
        }
