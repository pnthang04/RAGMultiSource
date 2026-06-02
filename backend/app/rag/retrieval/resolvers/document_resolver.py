from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any

from app.core.constants import (
    RETRIEVAL_SCOPE_CURRENT_SESSION_UPLOADS,
    RETRIEVAL_SCOPE_CURRENT_UPLOAD,
    RETRIEVAL_SCOPE_HYBRID_SYSTEM_AND_USER,
    RETRIEVAL_SCOPE_SYSTEM_DOCS,
    RETRIEVAL_SCOPE_SYSTEM_PROCEDURE,
    RETRIEVAL_SCOPE_USER_ALL_UPLOADS,
    RETRIEVAL_SCOPE_USER_FILE_NAME,
    SOURCE_TYPE_SYSTEM,
    SOURCE_TYPE_USER_UPLOAD,
    VISIBILITY_GLOBAL,
)
from app.rag.embedding.bge_embedding import BGEEmbeddingService
from app.repositories.document_repository import DocumentRepository


def _and(*conditions: dict[str, Any]) -> dict[str, Any]:
    clean_conditions = [condition for condition in conditions if condition]
    if not clean_conditions:
        return {}
    if len(clean_conditions) == 1:
        return clean_conditions[0]
    return {"$and": clean_conditions}


def _normalize_text(text: str | None) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text.lower())
    stripped = "".join(char for char in normalized if not unicodedata.combining(char))
    stripped = stripped.replace("đ", "d")
    return re.sub(r"\s+", " ", stripped).strip()


def _token_set(text: str | None) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", _normalize_text(text)) if len(token) > 1}


@dataclass
class DocumentResolution:
    metadata_filter: dict[str, Any]
    selected_document_ids: list[str] = field(default_factory=list)
    resolved_documents: list[dict[str, Any]] = field(default_factory=list)
    needs_clarification: bool = False
    reason: str | None = None

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


class DocumentResolver:
    def __init__(self, document_repository: DocumentRepository | None = None) -> None:
        self.document_repository = document_repository or DocumentRepository()
        self.embedding_service = BGEEmbeddingService()
        self._system_doc_embedding_cache: dict[str, list[float]] = {}

    def _is_system_scope(self, scope: str) -> bool:
        return scope in {"system_only", RETRIEVAL_SCOPE_SYSTEM_PROCEDURE, RETRIEVAL_SCOPE_SYSTEM_DOCS}

    def _is_current_upload_scope(self, scope: str) -> bool:
        return scope in {"current_uploads_only", RETRIEVAL_SCOPE_CURRENT_SESSION_UPLOADS, RETRIEVAL_SCOPE_CURRENT_UPLOAD}

    def _is_past_upload_scope(self, scope: str) -> bool:
        return scope in {"past_uploads_only", "user_uploads_all", RETRIEVAL_SCOPE_USER_ALL_UPLOADS}

    def _is_mixed_scope(self, scope: str) -> bool:
        return scope in {"mixed", RETRIEVAL_SCOPE_HYBRID_SYSTEM_AND_USER}

    def _with_document_filter(self, metadata_filter: dict[str, Any], document_ids: list[str]) -> dict[str, Any]:
        document_ids = [document_id for document_id in document_ids if document_id]
        if not document_ids:
            return metadata_filter
        document_filter = {"document_id": {"$in": document_ids}}
        if metadata_filter:
            return _and(metadata_filter, document_filter)
        return document_filter

    def _serialize_docs(self, documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "document_id": doc.get("_id"),
                "filename": doc.get("filename"),
                "source_type": doc.get("source_type"),
                "owner_user_id": doc.get("owner_user_id"),
                "session_id": doc.get("uploaded_in_session_id"),
                "procedure_title": doc.get("procedure_title"),
                "summary": doc.get("summary"),
                "visibility": doc.get("visibility"),
                "created_at": doc.get("created_at"),
            }
            for doc in documents
        ]

    def _system_document_match_text(self, document: dict[str, Any]) -> str:
        parts = [
            document.get("procedure_title"),
            document.get("summary"),
            document.get("title"),
            document.get("filename"),
        ]
        return "\n".join(str(part).strip() for part in parts if part and str(part).strip())

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right:
            return 0.0
        import math

        dot_product = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot_product / (left_norm * right_norm)

    def _token_overlap_score(self, query: str, document: dict[str, Any]) -> float:
        query_tokens = _token_set(query)
        doc_tokens = _token_set(self._system_document_match_text(document))
        if not query_tokens or not doc_tokens:
            return 0.0
        return len(query_tokens & doc_tokens) / len(query_tokens)

    def _system_doc_embedding(self, document: dict[str, Any]) -> list[float]:
        document_id = str(document.get("_id") or "")
        text = self._system_document_match_text(document)
        cache_key = f"{document_id}:{hash(text)}"
        if cache_key not in self._system_doc_embedding_cache:
            self._system_doc_embedding_cache[cache_key] = self.embedding_service.embed_text(text)
        return self._system_doc_embedding_cache[cache_key]

    def _is_authorized_selected_document(
        self,
        document: dict[str, Any],
        scope: str,
        user_id: str,
        session_id: str | None,
    ) -> bool:
        source_type = document.get("source_type")
        if source_type == SOURCE_TYPE_SYSTEM:
            return document.get("visibility") == VISIBILITY_GLOBAL

        if source_type != SOURCE_TYPE_USER_UPLOAD or document.get("owner_user_id") != user_id:
            return False

        # Explicit selected_document_ids come from a user action in the UI
        # (for example, asking about an attached upload). Ownership is the
        # security boundary; requiring the current session to match here makes
        # valid attachments fail if the active session state changes client-side.
        return True

    async def _resolve_selected_documents(
        self,
        scope: str,
        user_id: str,
        session_id: str | None,
        selected_document_ids: list[str],
    ) -> list[dict[str, Any]]:
        documents: list[dict[str, Any]] = []
        for document_id in dict.fromkeys([doc_id for doc_id in selected_document_ids if doc_id]):
            document = await self.document_repository.get_document_by_id(document_id)
            if document and self._is_authorized_selected_document(document, scope, user_id, session_id):
                documents.append(document)
        return documents

    async def _find_system_documents_by_procedure_hint(self, procedure_title: str) -> list[dict[str, Any]]:
        documents = await self.document_repository.find_system_documents_by_procedure_title(procedure_title)
        if documents:
            return documents

        if not hasattr(self.document_repository, "list_system_ready_documents"):
            return []

        hint_tokens = _token_set(procedure_title)
        if not hint_tokens:
            return []

        system_documents = await self.document_repository.list_system_ready_documents()
        scored: list[tuple[float, dict[str, Any]]] = []
        for document in system_documents:
            title = document.get("procedure_title") or document.get("title") or document.get("filename")
            title_tokens = _token_set(title)
            if not title_tokens:
                continue
            overlap = hint_tokens & title_tokens
            score = len(overlap) / len(hint_tokens)
            if score >= 0.6:
                scored.append((score, document))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [document for _, document in scored[:5]]

    async def _find_system_documents_by_query(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        if not query.strip() or not hasattr(self.document_repository, "list_system_ready_documents"):
            return []

        system_documents = await self.document_repository.list_system_ready_documents()
        if not system_documents:
            return []

        query_embedding = self.embedding_service.embed_text(query)
        scored: list[tuple[float, float, float, dict[str, Any]]] = []
        for document in system_documents:
            overlap_score = self._token_overlap_score(query, document)
            semantic_score = self._cosine_similarity(query_embedding, self._system_doc_embedding(document))
            combined_score = (semantic_score * 0.75) + (overlap_score * 0.25)
            scored.append((combined_score, semantic_score, overlap_score, document))

        scored.sort(key=lambda item: item[0], reverse=True)
        if not scored:
            return []

        best_score = scored[0][0]
        selected = [
            document
            for combined_score, semantic_score, overlap_score, document in scored[:limit]
            if combined_score >= 0.28 and combined_score >= best_score - 0.08
        ]
        return selected or [scored[0][3]]

    async def resolve(
        self,
        scope: str,
        metadata_filter: dict[str, Any],
        user_id: str,
        session_id: str | None = None,
        detected_filename: str | None = None,
        detected_procedure_title: str | None = None,
        time_hint: str | None = None,
        selected_document_ids: list[str] | None = None,
        conversation_state: dict[str, Any] | None = None,
        query_text: str | None = None,
    ) -> DocumentResolution:
        conversation_state = conversation_state or {}
        selected_document_ids = selected_document_ids or []

        if selected_document_ids:
            documents = await self._resolve_selected_documents(scope, user_id, session_id, selected_document_ids)
            authorized_document_ids = [doc["_id"] for doc in documents if doc.get("_id")]
            return DocumentResolution(
                metadata_filter=self._with_document_filter(metadata_filter, authorized_document_ids),
                selected_document_ids=authorized_document_ids,
                resolved_documents=self._serialize_docs(documents),
                needs_clarification=not authorized_document_ids,
                reason="explicit selected document ids after authorization check",
            )

        if self._is_system_scope(scope) and detected_procedure_title:
            documents = await self._find_system_documents_by_procedure_hint(detected_procedure_title)
            document_ids = [doc["_id"] for doc in documents if doc.get("_id")]
            return DocumentResolution(
                metadata_filter=self._with_document_filter(metadata_filter, document_ids),
                selected_document_ids=document_ids,
                resolved_documents=self._serialize_docs(documents),
                needs_clarification=len(documents) > 1,
                reason="matched system procedure title",
            )

        if self._is_system_scope(scope) and query_text:
            documents = await self._find_system_documents_by_query(query_text)
            document_ids = [doc["_id"] for doc in documents if doc.get("_id")]
            return DocumentResolution(
                metadata_filter=self._with_document_filter(metadata_filter, document_ids),
                selected_document_ids=document_ids,
                resolved_documents=self._serialize_docs(documents),
                needs_clarification=False,
                reason="matched system documents by procedure_title and summary",
            )

        if scope == RETRIEVAL_SCOPE_USER_FILE_NAME and detected_filename:
            documents = await self.document_repository.find_user_documents_by_filename(user_id, detected_filename)
            document_ids = [doc["_id"] for doc in documents if doc.get("_id")]
            return DocumentResolution(
                metadata_filter=self._with_document_filter(metadata_filter, document_ids),
                selected_document_ids=document_ids,
                resolved_documents=self._serialize_docs(documents),
                needs_clarification=len(documents) > 1,
                reason="matched uploaded filename",
            )

        if self._is_current_upload_scope(scope) and session_id:
            documents = await self.document_repository.list_user_documents_by_session(user_id, session_id)
            if not documents and conversation_state.get("current_session_docs"):
                document_ids = [doc_id for doc_id in conversation_state["current_session_docs"] if doc_id]
                return DocumentResolution(
                    metadata_filter=self._with_document_filter(metadata_filter, document_ids),
                    selected_document_ids=document_ids,
                    reason="used current session docs from conversation state",
                )
            document_ids = [doc["_id"] for doc in documents if doc.get("_id")]
            return DocumentResolution(
                metadata_filter=self._with_document_filter(metadata_filter, document_ids),
                selected_document_ids=document_ids,
                resolved_documents=self._serialize_docs(documents),
                needs_clarification=len(documents) > 1,
                reason="matched current session uploads",
            )

        if self._is_past_upload_scope(scope):
            if time_hint:
                documents = await self.document_repository.list_user_documents_by_time_hint(
                    user_id,
                    time_hint,
                    filename=detected_filename,
                )
                document_ids = [doc["_id"] for doc in documents if doc.get("_id")]
                if documents:
                    return DocumentResolution(
                        metadata_filter=self._with_document_filter(metadata_filter, document_ids),
                        selected_document_ids=document_ids,
                        resolved_documents=self._serialize_docs(documents),
                        reason=f"matched uploads by time hint: {time_hint}",
                    )
            last_document = conversation_state.get("last_referenced_doc") or {}
            last_document_id = last_document.get("document_id") if isinstance(last_document, dict) else None
            if last_document_id:
                return DocumentResolution(
                    metadata_filter=self._with_document_filter(metadata_filter, [last_document_id]),
                    selected_document_ids=[last_document_id],
                    reason="used last referenced document",
                )
            documents = await self.document_repository.list_user_ready_documents(user_id)
            document_ids = [doc["_id"] for doc in documents[:1] if doc.get("_id")]
            return DocumentResolution(
                metadata_filter=self._with_document_filter(metadata_filter, document_ids),
                selected_document_ids=document_ids,
                resolved_documents=self._serialize_docs(documents[:1]),
                reason="used latest user upload",
            )

        if self._is_mixed_scope(scope):
            system_documents: list[dict[str, Any]] = []
            user_documents: list[dict[str, Any]] = []
            if detected_procedure_title:
                system_documents = await self._find_system_documents_by_procedure_hint(detected_procedure_title)
            if detected_filename:
                user_documents = await self.document_repository.find_user_documents_by_filename(user_id, detected_filename)
            elif time_hint:
                user_documents = await self.document_repository.list_user_documents_by_time_hint(
                    user_id,
                    time_hint,
                    filename=detected_filename,
                )
            elif session_id:
                user_documents = await self.document_repository.list_user_documents_by_session(user_id, session_id)
            else:
                latest_user_documents = await self.document_repository.list_user_ready_documents(user_id)
                user_documents = latest_user_documents[:1]

            documents = system_documents + [doc for doc in user_documents if doc not in system_documents]
            document_ids = [doc["_id"] for doc in documents if doc.get("_id")]
            return DocumentResolution(
                metadata_filter=self._with_document_filter(metadata_filter, document_ids),
                selected_document_ids=document_ids,
                resolved_documents=self._serialize_docs(documents),
                needs_clarification=len(documents) > 1,
                reason="resolved mixed system and user-upload scope",
            )

        return DocumentResolution(metadata_filter=metadata_filter, reason="scope does not require a specific document")
