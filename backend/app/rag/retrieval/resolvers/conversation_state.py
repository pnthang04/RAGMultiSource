from __future__ import annotations

from typing import Any

from app.core.constants import RETRIEVAL_SCOPE_GENERAL_QUERY, RETRIEVAL_SCOPE_NEED_CLARIFICATION


class ConversationStateManager:
    def load(self, session: dict[str, Any] | None, user_id: str, session_id: str | None) -> dict[str, Any]:
        state = dict((session or {}).get("conversation_state") or {})
        state["current_user_id"] = user_id
        state["current_session_id"] = session_id
        state.setdefault("active_document_ids", [])
        state.setdefault("current_session_docs", [])
        return state

    def update_after_answer(
        self,
        state: dict[str, Any],
        intent: str,
        scope: str,
        sources: list[dict[str, Any]],
        selected_document_ids: list[str],
        rewritten_question: str | None = None,
        detected_procedure_title: str | None = None,
        detected_filename: str | None = None,
        retrieval_filter: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        next_state = dict(state)
        next_state["last_intent"] = intent
        next_state["last_scope"] = scope
        next_state["last_sources"] = sources
        next_state["last_document_ids"] = selected_document_ids
        if rewritten_question:
            next_state["last_rewritten_question"] = rewritten_question
        next_state["active_document_ids"] = selected_document_ids or next_state.get("active_document_ids", [])

        if detected_procedure_title:
            next_state["last_procedure_title"] = detected_procedure_title
        if detected_filename:
            next_state["last_filename"] = detected_filename

        should_update_resolved_context = bool(retrieval_filter) and scope not in {
            RETRIEVAL_SCOPE_GENERAL_QUERY,
            RETRIEVAL_SCOPE_NEED_CLARIFICATION,
        } and bool(sources or selected_document_ids)

        if should_update_resolved_context:
            next_state["last_resolved_context"] = {
                "scope": scope,
                "source_type": sources[0].get("source_type") if sources else None,
                "procedure_title": detected_procedure_title or next_state.get("last_procedure_title"),
                "filename": detected_filename or next_state.get("last_filename"),
                "document_id": selected_document_ids[0] if selected_document_ids else None,
                "filter": retrieval_filter,
            }

        if sources:
            first_source = sources[0]
            if first_source.get("source_type") == "user_upload" and first_source.get("session_id") == state.get("current_session_id"):
                session_doc_ids = [source.get("document_id") for source in sources if source.get("document_id")]
                next_state["current_session_docs"] = list(dict.fromkeys(session_doc_ids))
            next_state["last_referenced_doc"] = {
                "document_id": first_source.get("document_id"),
                "filename": first_source.get("filename"),
                "source_type": first_source.get("source_type"),
                "procedure_title": first_source.get("procedure_title"),
                "session_id": first_source.get("session_id"),
            }
        elif selected_document_ids:
            next_state["last_referenced_doc"] = {"document_id": selected_document_ids[0]}

        return next_state
