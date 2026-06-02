import asyncio

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
from app.models.retrieval_log import RetrievalLogModel
from app.rag.pipeline import qa_pipeline
from app.rag.pipeline.qa_pipeline import LOGGABLE_RETRIEVAL_SCOPES, QAPipeline


class FakeGraphRunner:
    scope = "none"
    intent_resolution = {"intent": "general_query", "needs_retrieval": False}
    targets = []

    def __init__(self, pipeline):
        self.pipeline = pipeline

    async def run(self, initial_state):
        return {
            "answer": "Xin chao",
            "sources": [],
            "raw_contexts": [],
            "scope_resolution": {"scope": self.scope, "targets": self.targets},
            "intent_resolution": self.intent_resolution,
            "document_resolution": {},
        }


def _run_pipeline(monkeypatch, scope: str, intent_resolution: dict | None = None, targets: list[dict] | None = None) -> dict:
    class ScopedFakeGraphRunner(FakeGraphRunner):
        pass

    ScopedFakeGraphRunner.scope = scope
    if intent_resolution is not None:
        ScopedFakeGraphRunner.intent_resolution = intent_resolution
    if targets is not None:
        ScopedFakeGraphRunner.targets = targets
    monkeypatch.setattr(qa_pipeline, "RAGGraphRunner", ScopedFakeGraphRunner)
    return asyncio.run(
        QAPipeline().run(
            question="chao ban",
            user_id="user_1",
            session_id="sess_1",
            scope="auto",
            selected_document_ids=[],
            conversation_state={},
        )
    )


def test_pipeline_maps_internal_none_scope_to_general_query(monkeypatch):
    result = _run_pipeline(monkeypatch, "none")

    assert result["scope"] == RETRIEVAL_SCOPE_GENERAL_QUERY


def test_pipeline_maps_internal_intent_scopes_to_loggable_scopes(monkeypatch):
    cases = {
        "system_only": RETRIEVAL_SCOPE_SYSTEM_DOCS,
        "current_uploads_only": RETRIEVAL_SCOPE_CURRENT_SESSION_UPLOADS,
        "past_uploads_only": RETRIEVAL_SCOPE_USER_ALL_UPLOADS,
        "user_uploads_all": RETRIEVAL_SCOPE_USER_ALL_UPLOADS,
    }

    for internal_scope, expected_scope in cases.items():
        result = _run_pipeline(
            monkeypatch,
            internal_scope,
            {"intent": "ask_question", "needs_retrieval": True},
        )

        assert result["scope"] == expected_scope


def test_pipeline_keeps_public_scope_values(monkeypatch):
    public_scopes = [
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
    ]

    for public_scope in public_scopes:
        result = _run_pipeline(
            monkeypatch,
            public_scope,
            {"intent": "ask_question", "needs_retrieval": True},
        )

        assert result["scope"] == public_scope


def test_pipeline_falls_back_for_unknown_scopes_without_crashing(monkeypatch):
    assert _run_pipeline(
        monkeypatch,
        "llm_weird_direct",
        {"intent": "general_query", "needs_retrieval": False},
    )["scope"] == RETRIEVAL_SCOPE_GENERAL_QUERY
    assert _run_pipeline(
        monkeypatch,
        "llm_weird_compare",
        {"intent": "compare_documents", "needs_retrieval": True},
    )["scope"] == RETRIEVAL_SCOPE_HYBRID_SYSTEM_AND_USER
    assert _run_pipeline(
        monkeypatch,
        "llm_weird_current_upload",
        {"intent": "ask_question", "needs_retrieval": True},
        [{"source_type": SOURCE_TYPE_USER_UPLOAD, "session_scope": "current_session"}],
    )["scope"] == RETRIEVAL_SCOPE_CURRENT_SESSION_UPLOADS
    assert _run_pipeline(
        monkeypatch,
        "llm_weird_system",
        {"intent": "ask_question", "needs_retrieval": True},
        [{"source_type": SOURCE_TYPE_SYSTEM, "session_scope": None}],
    )["scope"] == RETRIEVAL_SCOPE_SYSTEM_DOCS

    result = _run_pipeline(
        monkeypatch,
        "totally_unknown",
        {"intent": "ask_question", "needs_retrieval": True},
    )

    assert result["scope"] == RETRIEVAL_SCOPE_NEED_CLARIFICATION


def test_all_normalized_scopes_are_valid_retrieval_log_values(monkeypatch):
    scopes_to_check = [
        "none",
        "system_only",
        "current_uploads_only",
        "past_uploads_only",
        "user_uploads_all",
        "totally_unknown",
        *sorted(LOGGABLE_RETRIEVAL_SCOPES),
    ]

    for scope in scopes_to_check:
        result = _run_pipeline(
            monkeypatch,
            scope,
            {"intent": "ask_question", "needs_retrieval": scope != "none"},
        )
        log = RetrievalLogModel(
            id=f"rlog_{scope}",
            user_id="user_1",
            session_id="sess_1",
            question="test",
            resolved_scope=result["scope"],
        )

        assert log.resolved_scope == result["scope"]
