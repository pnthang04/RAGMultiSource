from app.core.constants import (
    RETRIEVAL_SCOPE_ALL_USER_UPLOADS,
    RETRIEVAL_SCOPE_AUTO,
    RETRIEVAL_SCOPE_CURRENT_UPLOAD,
    RETRIEVAL_SCOPE_CURRENT_SESSION_UPLOADS,
    RETRIEVAL_SCOPE_GENERAL_QUERY,
    RETRIEVAL_SCOPE_HYBRID_SYSTEM_AND_USER,
    RETRIEVAL_SCOPE_MIXED,
    RETRIEVAL_SCOPE_NEED_CLARIFICATION,
    RETRIEVAL_SCOPE_SYSTEM_DOCS,
    RETRIEVAL_SCOPE_SYSTEM_PROCEDURE,
    RETRIEVAL_SCOPE_USER_ALL_UPLOADS,
    RETRIEVAL_SCOPE_USER_FILE_NAME,
    SOURCE_TYPE_SYSTEM,
    SOURCE_TYPE_USER_UPLOAD,
)
from app.rag.generation.openai_llm import OpenAILLMService
from app.rag.generation.source_formatter import SourceFormatter
from app.rag.graph import RAGGraphRunner
from app.rag.query import IntentRouter
from app.rag.rewrite import QueryRewriter, RewriteGate
from app.rag.retrieval.context_validator import FALLBACK_NO_CONTEXT, ContextValidator
from app.rag.retrieval.resolvers import DocumentResolver
from app.rag.retrieval.retriever import Retriever
from app.rag.retrieval.strategy import RetrievalStrategy
from langsmith import traceable


LOGGABLE_RETRIEVAL_SCOPES = {
    RETRIEVAL_SCOPE_CURRENT_UPLOAD,
    RETRIEVAL_SCOPE_CURRENT_SESSION_UPLOADS,
    RETRIEVAL_SCOPE_ALL_USER_UPLOADS,
    RETRIEVAL_SCOPE_USER_ALL_UPLOADS,
    RETRIEVAL_SCOPE_USER_FILE_NAME,
    RETRIEVAL_SCOPE_SYSTEM_DOCS,
    RETRIEVAL_SCOPE_SYSTEM_PROCEDURE,
    RETRIEVAL_SCOPE_HYBRID_SYSTEM_AND_USER,
    RETRIEVAL_SCOPE_GENERAL_QUERY,
    RETRIEVAL_SCOPE_NEED_CLARIFICATION,
    RETRIEVAL_SCOPE_MIXED,
    RETRIEVAL_SCOPE_AUTO,
}


class QAPipeline:
    def __init__(self) -> None:
        self.rewrite_gate = RewriteGate()
        self.intent_router = IntentRouter()
        self.document_resolver = DocumentResolver()
        self.query_rewriter = QueryRewriter()
        self.retrieval_strategy = RetrievalStrategy()
        self.context_validator = ContextValidator()
        self.retriever = Retriever()
        self.llm = OpenAILLMService()
        self.source_formatter = SourceFormatter()

    def _resolved_scope_for_response(self, scope_resolution: dict, intent_resolution: dict) -> str:
        scope = scope_resolution.get("scope") or RETRIEVAL_SCOPE_NEED_CLARIFICATION
        internal_scope_map = {
            "system_only": RETRIEVAL_SCOPE_SYSTEM_DOCS,
            "current_uploads_only": RETRIEVAL_SCOPE_CURRENT_SESSION_UPLOADS,
            "past_uploads_only": RETRIEVAL_SCOPE_USER_ALL_UPLOADS,
            "user_uploads_all": RETRIEVAL_SCOPE_USER_ALL_UPLOADS,
        }
        if scope in internal_scope_map:
            return internal_scope_map[scope]
        if scope in LOGGABLE_RETRIEVAL_SCOPES:
            return scope
        if scope == "none":
            if intent_resolution.get("intent") == "general_query" or not intent_resolution.get("needs_retrieval", True):
                return RETRIEVAL_SCOPE_GENERAL_QUERY
            return RETRIEVAL_SCOPE_NEED_CLARIFICATION

        intent = intent_resolution.get("intent")
        if intent == "general_query" or not intent_resolution.get("needs_retrieval", True):
            return RETRIEVAL_SCOPE_GENERAL_QUERY
        if intent == "need_clarification":
            return RETRIEVAL_SCOPE_NEED_CLARIFICATION
        if intent == "compare_documents":
            return RETRIEVAL_SCOPE_HYBRID_SYSTEM_AND_USER

        targets = scope_resolution.get("targets") if isinstance(scope_resolution, dict) else None
        targets = targets if isinstance(targets, list) else []
        source_types = {target.get("source_type") for target in targets if isinstance(target, dict)}
        if SOURCE_TYPE_SYSTEM in source_types and SOURCE_TYPE_USER_UPLOAD in source_types:
            return RETRIEVAL_SCOPE_HYBRID_SYSTEM_AND_USER
        if SOURCE_TYPE_USER_UPLOAD in source_types:
            if any(target.get("session_scope") == "current_session" for target in targets if isinstance(target, dict)):
                return RETRIEVAL_SCOPE_CURRENT_SESSION_UPLOADS
            return RETRIEVAL_SCOPE_USER_ALL_UPLOADS
        if SOURCE_TYPE_SYSTEM in source_types:
            return RETRIEVAL_SCOPE_SYSTEM_DOCS

        return RETRIEVAL_SCOPE_NEED_CLARIFICATION

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
        conversation_state = conversation_state or {}
        graph_result = await RAGGraphRunner(self).run(
            {
                "original_query": question,
                "user_id": user_id,
                "session_id": session_id,
                "requested_scope": scope if scope != RETRIEVAL_SCOPE_AUTO else RETRIEVAL_SCOPE_AUTO,
                "selected_document_ids": selected_document_ids or [],
                "runtime_context": conversation_state,
            }
        )
        scope_resolution = graph_result.get("scope_resolution") or {}
        document_resolution = graph_result.get("document_resolution") or {}
        intent_resolution = graph_result.get("intent_resolution", {})
        return {
            "answer": graph_result.get("answer", FALLBACK_NO_CONTEXT),
            "sources": graph_result.get("sources", []),
            "raw_contexts": graph_result.get("raw_contexts", []),
            "scope": self._resolved_scope_for_response(scope_resolution, intent_resolution),
            "intent_resolution": intent_resolution,
            "scope_resolution": scope_resolution,
            "document_resolution": document_resolution,
            "rewrite_gate": graph_result.get("rewrite_gate", {}),
            "query_rewrite": graph_result.get("query_rewrite", {}),
            "retrieval_plan": graph_result.get("retrieval_plan", {}),
            "context_validation": graph_result.get("context_validation", {}),
            "retrieval_filter": graph_result.get("metadata_filter", document_resolution.get("metadata_filter", {})),
        }
