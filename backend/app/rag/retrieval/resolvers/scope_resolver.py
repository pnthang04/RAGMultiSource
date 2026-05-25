from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from app.core.constants import (
    RETRIEVAL_SCOPE_ALL_USER_UPLOADS,
    RETRIEVAL_SCOPE_AUTO,
    RETRIEVAL_SCOPE_CURRENT_SESSION_UPLOADS,
    RETRIEVAL_SCOPE_CURRENT_UPLOAD,
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
    VISIBILITY_GLOBAL,
)
from app.rag.retrieval.resolvers.scope_resolver_patterns import (
    AMBIGUOUS_DOCUMENT_PATTERNS,
    COMPARE_PATTERNS,
    CURRENT_UPLOAD_PATTERNS,
    FILENAME_PATTERN,
    FOLLOW_UP_PATTERNS,
    PROCEDURE_INTENT_TAIL_PATTERN,
    SYSTEM_GENERAL_PATTERNS,
    USER_HISTORY_PATTERNS,
    _and,
    _normalize_text,
    _or,
    _strip_quotes,
)


@dataclass
class ScopeResolution:
    scope: str
    metadata_filter: dict[str, Any]
    should_retrieve: bool = True
    detected_procedure_title: str | None = None
    detected_filename: str | None = None
    matched_rules: list[str] = field(default_factory=list)
    reason: str | None = None

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


class ScopeResolver:
    _current_upload_patterns = CURRENT_UPLOAD_PATTERNS
    _ambiguous_document_patterns = AMBIGUOUS_DOCUMENT_PATTERNS
    _user_history_patterns = USER_HISTORY_PATTERNS
    _compare_patterns = COMPARE_PATTERNS
    _system_general_patterns = SYSTEM_GENERAL_PATTERNS
    _follow_up_patterns = FOLLOW_UP_PATTERNS
    _filename_pattern = FILENAME_PATTERN
    _procedure_intent_tail_pattern = PROCEDURE_INTENT_TAIL_PATTERN

    def _contains_any(self, text: str, patterns: tuple[str, ...]) -> bool:
        return any(pattern in text for pattern in patterns)

    def _detect_filename(self, question: str) -> str | None:
        match = self._filename_pattern.search(question)
        if not match:
            return None
        filename = _strip_quotes(match.group("filename"))
        filename = re.sub(r"(?i)^.*\b(?:file|tai\s+lieu|document)\s+", "", filename)
        filename = re.sub(r"\s+", " ", filename).strip()
        return filename or None

    def _detect_procedure_title(self, question: str) -> str | None:
        normalized = _normalize_text(question)
        if not self._contains_any(normalized, self._system_general_patterns):
            return None

        candidate = question
        for keyword in ("thủ tục", "procedure", "quy trình", "hồ sơ", "quy định"):
            keyword_normalized = _normalize_text(keyword)
            if keyword_normalized in normalized:
                index = normalized.find(keyword_normalized)
                candidate = question[index + len(keyword) :]
                break

        candidate = _strip_quotes(candidate)
        candidate = re.sub(r"^\s*[:\-]\s*", "", candidate)
        candidate = re.sub(r"^\s*(của|cho|về)\s+", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\s+", " ", candidate).strip()
        if not candidate:
            return None

        candidate_normalized = _normalize_text(candidate)
        tail_match = self._procedure_intent_tail_pattern.search(candidate_normalized)
        if tail_match:
            candidate = candidate[: tail_match.start()].strip(" ,.;:-")
            candidate_normalized = _normalize_text(candidate)

        if not candidate or candidate_normalized in {"thu tuc", "quy trinh", "ho so", "quy dinh"}:
            return None
        if candidate_normalized.startswith(("hanh chinh", "thu tuc hanh chinh")):
            return None
        if candidate_normalized.endswith(("la gi", "nao", "nhu the nao", "ra sao")):
            return None
        return candidate

    def _looks_like_follow_up(self, normalized_question: str) -> bool:
        if len(normalized_question.split()) <= 6:
            return True
        return self._contains_any(normalized_question, self._follow_up_patterns)

    def _build_filter_for_scope(
        self,
        scope: str,
        user_id: str,
        session_id: str | None,
        selected_document_ids: list[str],
        detected_procedure_title: str | None = None,
        detected_filename: str | None = None,
    ) -> dict[str, Any]:
        selected_document_ids = [doc_id for doc_id in selected_document_ids if doc_id]

        if scope == RETRIEVAL_SCOPE_SYSTEM_PROCEDURE:
            conditions: list[dict[str, Any]] = [
                {"source_type": SOURCE_TYPE_SYSTEM},
                {"visibility": VISIBILITY_GLOBAL},
            ]
            if detected_procedure_title:
                conditions.append({"procedure_title": detected_procedure_title})
            base: dict[str, Any] = _and(*conditions)
        elif scope in {RETRIEVAL_SCOPE_CURRENT_SESSION_UPLOADS, RETRIEVAL_SCOPE_CURRENT_UPLOAD}:
            conditions = [
                {"source_type": SOURCE_TYPE_USER_UPLOAD},
                {"owner_user_id": user_id},
            ]
            if session_id:
                conditions.append({"session_id": session_id})
            base = _and(*conditions)
        elif scope in {RETRIEVAL_SCOPE_ALL_USER_UPLOADS, RETRIEVAL_SCOPE_USER_ALL_UPLOADS}:
            base = _and({"source_type": SOURCE_TYPE_USER_UPLOAD}, {"owner_user_id": user_id})
        elif scope == RETRIEVAL_SCOPE_USER_FILE_NAME:
            conditions = [
                {"source_type": SOURCE_TYPE_USER_UPLOAD},
                {"owner_user_id": user_id},
            ]
            if detected_filename:
                conditions.append({"filename": detected_filename})
            base = _and(*conditions)
        elif scope == RETRIEVAL_SCOPE_SYSTEM_DOCS:
            base = _and({"source_type": SOURCE_TYPE_SYSTEM}, {"visibility": VISIBILITY_GLOBAL})
        elif scope in {RETRIEVAL_SCOPE_HYBRID_SYSTEM_AND_USER, RETRIEVAL_SCOPE_MIXED}:
            system_conditions = [{"source_type": SOURCE_TYPE_SYSTEM}, {"visibility": VISIBILITY_GLOBAL}]
            user_conditions = [{"source_type": SOURCE_TYPE_USER_UPLOAD}, {"owner_user_id": user_id}]
            if detected_procedure_title:
                system_conditions.append({"procedure_title": detected_procedure_title})
            if detected_filename:
                user_conditions.append({"filename": detected_filename})
            system_filter = _and(*system_conditions)
            user_filter = _and(*user_conditions)
            base = _or(system_filter, user_filter)
        elif scope in {RETRIEVAL_SCOPE_GENERAL_QUERY, RETRIEVAL_SCOPE_NEED_CLARIFICATION}:
            base = {}
        else:
            base = {"source_type": SOURCE_TYPE_SYSTEM, "visibility": VISIBILITY_GLOBAL}

        if selected_document_ids:
            if base:
                return _and(base, {"document_id": {"$in": selected_document_ids}})
            return {"document_id": {"$in": selected_document_ids}}
        return base

    def resolve(
        self,
        question: str,
        user_id: str,
        session_id: str | None = None,
        scope: str = RETRIEVAL_SCOPE_AUTO,
        selected_document_ids: list[str] | None = None,
        conversation_state: dict[str, Any] | None = None,
    ) -> ScopeResolution:
        conversation_state = conversation_state or {}
        selected_document_ids = selected_document_ids or []
        normalized_question = _normalize_text(question)

        last_scope = conversation_state.get("last_scope")
        last_procedure_title = conversation_state.get("last_procedure_title")
        last_filename = conversation_state.get("last_filename")

        detected_filename = self._detect_filename(question)
        detected_procedure_title = self._detect_procedure_title(question)

        matched_rules: list[str] = []

        if scope != RETRIEVAL_SCOPE_AUTO:
            metadata_filter = self._build_filter_for_scope(
                scope=scope,
                user_id=user_id,
                session_id=session_id,
                selected_document_ids=selected_document_ids,
                detected_procedure_title=detected_procedure_title,
                detected_filename=detected_filename,
            )
            return ScopeResolution(
                scope=scope,
                metadata_filter=metadata_filter,
                should_retrieve=scope not in {RETRIEVAL_SCOPE_GENERAL_QUERY, RETRIEVAL_SCOPE_NEED_CLARIFICATION},
                detected_procedure_title=detected_procedure_title,
                detected_filename=detected_filename,
                matched_rules=["explicit_scope"],
                reason="explicit scope provided by request",
            )

        if self._contains_any(normalized_question, self._compare_patterns):
            scope_name = RETRIEVAL_SCOPE_HYBRID_SYSTEM_AND_USER
            matched_rules.append("compare_query")
        elif detected_filename:
            scope_name = RETRIEVAL_SCOPE_USER_FILE_NAME
            matched_rules.append("detected_filename")
        elif detected_procedure_title:
            scope_name = RETRIEVAL_SCOPE_SYSTEM_PROCEDURE
            matched_rules.append("detected_procedure_title")
        elif self._contains_any(normalized_question, self._current_upload_patterns):
            scope_name = RETRIEVAL_SCOPE_CURRENT_SESSION_UPLOADS
            matched_rules.append("current_session_upload")
        elif self._contains_any(normalized_question, self._user_history_patterns):
            scope_name = RETRIEVAL_SCOPE_USER_ALL_UPLOADS
            matched_rules.append("user_history_upload")
        elif self._contains_any(normalized_question, self._system_general_patterns):
            scope_name = RETRIEVAL_SCOPE_SYSTEM_DOCS
            matched_rules.append("system_general")
        elif last_scope and self._looks_like_follow_up(normalized_question):
            scope_name = last_scope
            matched_rules.append("follow_up")
            detected_procedure_title = detected_procedure_title or last_procedure_title
            detected_filename = detected_filename or last_filename
        elif self._contains_any(normalized_question, self._ambiguous_document_patterns):
            scope_name = RETRIEVAL_SCOPE_NEED_CLARIFICATION
            matched_rules.append("ambiguous_document_reference")
        elif not self._contains_any(normalized_question, self._system_general_patterns) and not self._contains_any(
            normalized_question,
            self._current_upload_patterns + self._user_history_patterns + self._compare_patterns + self._ambiguous_document_patterns,
        ):
            scope_name = RETRIEVAL_SCOPE_GENERAL_QUERY
            matched_rules.append("general_query")
        else:
            scope_name = RETRIEVAL_SCOPE_NEED_CLARIFICATION
            matched_rules.append("ambiguous")

        if scope_name == RETRIEVAL_SCOPE_SYSTEM_PROCEDURE and not detected_procedure_title and last_procedure_title:
            detected_procedure_title = last_procedure_title
        if scope_name == RETRIEVAL_SCOPE_USER_FILE_NAME and not detected_filename and last_filename:
            detected_filename = last_filename

        metadata_filter = self._build_filter_for_scope(
            scope=scope_name,
            user_id=user_id,
            session_id=session_id,
            selected_document_ids=selected_document_ids,
            detected_procedure_title=detected_procedure_title,
            detected_filename=detected_filename,
        )

        if scope_name == RETRIEVAL_SCOPE_GENERAL_QUERY:
            reason = "question does not appear to reference any document"
        elif scope_name == RETRIEVAL_SCOPE_NEED_CLARIFICATION:
            reason = "question is ambiguous and needs document clarification"
        elif scope_name == RETRIEVAL_SCOPE_SYSTEM_PROCEDURE and detected_procedure_title:
            reason = f"detected procedure title: {detected_procedure_title}"
        elif scope_name == RETRIEVAL_SCOPE_USER_FILE_NAME and detected_filename:
            reason = f"detected filename: {detected_filename}"
        else:
            reason = "resolved from query heuristics"

        should_retrieve = scope_name not in {RETRIEVAL_SCOPE_GENERAL_QUERY, RETRIEVAL_SCOPE_NEED_CLARIFICATION}
        return ScopeResolution(
            scope=scope_name,
            metadata_filter=metadata_filter,
            should_retrieve=should_retrieve,
            detected_procedure_title=detected_procedure_title,
            detected_filename=detected_filename,
            matched_rules=matched_rules,
            reason=reason,
        )



