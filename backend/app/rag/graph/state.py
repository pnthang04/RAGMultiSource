from __future__ import annotations

from typing import Any, TypedDict


class RAGState(TypedDict, total=False):
    user_id: str
    session_id: str | None
    requested_scope: str
    selected_document_ids: list[str]
    runtime_context: dict[str, Any]

    original_query: str
    final_query: str
    rewritten_query: str | None
    was_rewritten: bool
    rewrite_gate: dict[str, Any]
    query_rewrite: dict[str, Any]

    intent_resolution: dict[str, Any]
    scope_resolution: dict[str, Any]
    document_resolution: dict[str, Any]
    retrieval_plan: dict[str, Any]

    document_candidates: list[dict[str, Any]]
    candidate_selection: dict[str, Any]
    metadata_filter: dict[str, Any]
    branch_results: list[dict[str, Any]]
    raw_contexts: list[dict[str, Any]]
    context_validation: dict[str, Any]
    mixed_branch_warnings: list[str]

    answer: str
    sources: list[dict[str, Any]]
    route: str
