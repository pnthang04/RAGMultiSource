from app.core.constants import SOURCE_TYPE_SYSTEM, SOURCE_TYPE_USER_UPLOAD
from app.rag.graph.nodes import RAGGraphNodes
from app.rag.pipeline.qa_pipeline import QAPipeline
from app.rag.retrieval.resolvers.conversation_state import ConversationStateManager
from app.rag.rewrite.rewrite_gate import RewriteGate


def _nodes() -> RAGGraphNodes:
    return RAGGraphNodes(QAPipeline())


def test_intent_router_directly_routes_document_questions_to_scope_resolver():
    nodes = _nodes()

    route = nodes.route_after_intent(
        {
            "intent_resolution": {"intent": "ask_question", "needs_retrieval": True},
        }
    )

    assert route == "scope_resolver"


def test_candidate_selector_clarifies_multiple_candidates():
    nodes = _nodes()

    result = nodes.candidate_selector_node(
        {
            "document_candidates": [
                {"document_id": "doc_1", "filename": "tam_tru_1.pdf"},
                {"document_id": "doc_2", "filename": "tam_tru_2.pdf"},
            ],
            "document_resolution": {"selected_document_ids": ["doc_1", "doc_2"]},
        }
    )

    assert result["candidate_selection"]["confident"] is False
    assert result["candidate_selection"]["needs_clarification"] is True


def test_candidate_selector_allows_multiple_upload_documents_for_time_scope():
    nodes = _nodes()

    result = nodes.candidate_selector_node(
        {
            "scope_resolution": {"scope": "user_all_uploads"},
            "document_candidates": [
                {"document_id": "doc_1", "filename": "week_1.pdf"},
                {"document_id": "doc_2", "filename": "week_2.pdf"},
            ],
            "document_resolution": {"selected_document_ids": ["doc_1", "doc_2"]},
        }
    )

    assert result["candidate_selection"]["confident"] is True
    assert result["candidate_selection"]["needs_clarification"] is False
    assert result["candidate_selection"]["selected_document_ids"] == ["doc_1", "doc_2"]


def test_mixed_evidence_validation_reports_missing_system_branch():
    nodes = _nodes()

    result = nodes.evidence_validation_node(
        {
            "retrieval_plan": {"mode": "hybrid_compare"},
            "branch_results": [
                {
                    "name": "system_chunks",
                    "metadata_filter": {"source_type": SOURCE_TYPE_SYSTEM},
                    "contexts": [],
                },
                {
                    "name": "user_upload_chunks",
                    "metadata_filter": {"source_type": SOURCE_TYPE_USER_UPLOAD, "owner_user_id": "user_1"},
                    "contexts": [
                        {
                            "id": "chunk_user_1",
                            "content": "File upload co le phi noi bo la 75.000 dong.",
                            "similarity": 0.9,
                            "metadata": {
                                "chunk_id": "chunk_user_1",
                                "document_id": "doc_1",
                                "source_type": SOURCE_TYPE_USER_UPLOAD,
                                "owner_user_id": "user_1",
                            },
                        }
                    ],
                },
            ],
        }
    )

    assert result["context_validation"]["should_answer"] is True
    assert result["mixed_branch_warnings"]


def test_scope_resolver_structured_reuses_last_context_when_safe():
    nodes = _nodes()

    result = nodes.scope_resolver_node(
        {
            "original_query": "can chuan bi gi?",
            "final_query": "Thu tuc dang ky ket hon can chuan bi giay to gi?",
            "was_rewritten": True,
            "retrieval_plan": {"action": "reuse_last_filter"},
            "runtime_context": {
                "last_resolved_context": {
                    "scope": "system_procedure",
                    "source_type": "system",
                    "procedure_title": "dang ky ket hon",
                    "filter": {"source_type": SOURCE_TYPE_SYSTEM, "procedure_title": "dang ky ket hon"},
                }
            },
        }
    )

    scope = result["scope_resolution"]
    assert scope["action"] == "reuse_last_filter"
    assert scope["scope"] == "system_procedure"
    assert scope["hints"]["procedure_title"] == "dang ky ket hon"


def test_scope_resolver_structured_blocks_reuse_when_switching_to_current_upload():
    nodes = _nodes()

    result = nodes.scope_resolver_node(
        {
            "original_query": "con trong file vua upload thi sao?",
            "final_query": "con trong file vua upload thi sao?",
            "was_rewritten": True,
            "retrieval_plan": {"action": "reuse_last_filter"},
            "runtime_context": {
                "last_resolved_context": {
                    "scope": "system_procedure",
                    "source_type": "system",
                    "procedure_title": "dang ky ket hon",
                    "filter": {"source_type": SOURCE_TYPE_SYSTEM, "procedure_title": "dang ky ket hon"},
                }
            },
        }
    )

    scope = result["scope_resolution"]
    assert scope["action"] in {"resolve_document", "need_clarification"}
    assert scope["scope"] in {"current_session_uploads", "need_clarification"}


def test_scope_resolver_structured_previous_upload_time_hint():
    nodes = _nodes()

    result = nodes.scope_resolver_node(
        {
            "original_query": "Thong tin nguoi dung trong file toi upload hom qua la gi?",
            "final_query": "Thong tin nguoi dung trong file toi upload hom qua la gi?",
            "retrieval_plan": {"action": "resolve_previous_upload"},
            "runtime_context": {},
        }
    )

    scope = result["scope_resolution"]
    assert scope["action"] == "resolve_document"
    assert scope["scope"] == "user_all_uploads"
    assert scope["hints"]["time"] == "yesterday"


def test_scope_resolver_structured_topic_hint_for_old_upload():
    nodes = _nodes()

    result = nodes.scope_resolver_node(
        {
            "original_query": "Tai lieu toi tung upload ve tam tru co thong tin gi?",
            "final_query": "Tai lieu toi tung upload ve tam tru co thong tin gi?",
            "retrieval_plan": {"action": "semantic_document_search"},
            "runtime_context": {},
        }
    )

    scope = result["scope_resolution"]
    assert scope["action"] == "resolve_document"
    assert scope["scope"] == "user_all_uploads"


def test_build_filter_node_builds_deterministic_filter_after_scope_resolution():
    nodes = _nodes()

    result = nodes.build_filter_node(
        {
            "user_id": "user_1",
            "session_id": "sess_1",
            "scope_resolution": {
                "scope": "current_session_uploads",
                "should_reuse_last_filter": False,
            },
            "document_resolution": {"selected_document_ids": ["doc_1"]},
        }
    )

    assert result["metadata_filter"]["$and"][0]["$and"] == [
        {"source_type": SOURCE_TYPE_USER_UPLOAD},
        {"owner_user_id": "user_1"},
        {"session_id": "sess_1"},
    ]
    assert result["metadata_filter"]["$and"][1] == {"document_id": {"$in": ["doc_1"]}}


def test_scope_reuse_routes_directly_to_build_filter():
    nodes = _nodes()

    route = nodes.route_after_scope_resolution(
        {
            "scope_resolution": {
                "scope": "system_procedure",
                "action": "reuse_last_filter",
            }
        }
    )

    assert route == "build_filter"


def test_scope_non_reuse_routes_to_document_resolver():
    nodes = _nodes()

    route = nodes.route_after_scope_resolution(
        {
            "scope_resolution": {
                "scope": "system_procedure",
                "action": "resolve_document",
            }
        }
    )

    assert route == "document_resolver"


def test_scope_resolver_defaults_admin_fee_question_to_system_docs():
    nodes = _nodes()

    result = nodes.scope_resolver_node(
        {
            "original_query": "le phi khi cap lai thong bao van ban buu chinh co le phi la bao nhieu the ban",
            "final_query": "le phi khi cap lai thong bao van ban buu chinh co le phi la bao nhieu the ban",
            "retrieval_plan": {"action": "need_clarification"},
            "runtime_context": {},
        }
    )

    assert result["scope_resolution"]["action"] == "resolve_document"
    assert result["scope_resolution"]["scope"] == "system_procedure"


def test_intent_router_guard_keeps_admin_fee_question_in_rag_path(monkeypatch):
    from app.rag.query.intent_router import IntentResolution, IntentRouter

    router = IntentRouter()

    def fake_llm(_question):
        return IntentResolution(
            intent="general_query",
            needs_retrieval=False,
            confidence=0.82,
            matched_rules=["llm_intent_router"],
            reason="LLM false negative.",
        )

    monkeypatch.setattr(router, "_route_with_llm", fake_llm)

    result = router.route("le phi khi cap lai thong bao van ban buu chinh la bao nhieu")

    assert result.intent == "ask_question"
    assert result.needs_retrieval is True
    assert "llm_false_negative_guard" in result.matched_rules


def test_rewrite_gate_fallback_detects_procedure_follow_up_without_llm(monkeypatch):
    gate = RewriteGate()
    monkeypatch.setattr(gate, "chain", None)

    result = gate.decide(
        "the trinh tu thuc hien nhu nao",
        {
            "last_resolved_context": {
                "scope": "system_procedure",
                "filter": {"source_type": "system", "procedure_title": "Cap lai van ban xac nhan thong bao hoat dong buu chinh"},
            },
            "last_procedure_title": "Cap lai van ban xac nhan thong bao hoat dong buu chinh",
        },
    )

    assert result.needs_rewrite is True
    assert "fallback_follow_up" in result.matched_rules


def test_rewrite_gate_fallback_detects_procedure_subject_follow_up_without_llm(monkeypatch):
    gate = RewriteGate()
    monkeypatch.setattr(gate, "chain", None)

    result = gate.decide(
        "doi tuong thuc hien ?",
        conversation_state={
            "last_resolved_context": {
                "filter": {
                    "source_type": "system",
                    "procedure_title": "Cap lai van ban xac nhan thong bao hoat dong buu chinh",
                }
            },
            "last_procedure_title": "Cap lai van ban xac nhan thong bao hoat dong buu chinh",
        },
    )

    assert result.needs_rewrite is True
    assert "fallback_follow_up" in result.matched_rules


def test_intent_router_treats_procedure_sequence_as_document_question():
    from app.rag.query.intent_router import IntentRouter

    result = IntentRouter()._route_by_rules("the trinh tu thuc hien nhu nao")

    assert result.intent == "ask_question"
    assert result.needs_retrieval is True


def test_conversation_state_preserves_last_context_on_general_query():
    manager = ConversationStateManager()
    previous_context = {
        "scope": "system_procedure",
        "source_type": "system",
        "procedure_title": "Cap lai van ban xac nhan thong bao hoat dong buu chinh",
        "document_id": "sysdoc_1",
        "filter": {"source_type": "system", "document_id": {"$in": ["sysdoc_1"]}},
    }

    result = manager.update_after_answer(
        state={"last_resolved_context": previous_context},
        intent="general_query",
        scope="general_query",
        sources=[],
        selected_document_ids=[],
        rewritten_question="the trinh tu thuc hien nhu nao",
        retrieval_filter={},
    )

    assert result["last_resolved_context"] == previous_context
