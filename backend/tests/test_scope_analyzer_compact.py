from app.core.constants import SOURCE_TYPE_SYSTEM, SOURCE_TYPE_USER_UPLOAD
from app.rag.graph.scope_analyzer import ScopeAnalyzer


def test_scope_analyzer_builds_compact_llm_input():
    analyzer = ScopeAnalyzer()

    payload = analyzer._build_llm_input(
        {
            "original_query": "lệ phí bao nhiêu?",
            "final_query": "lệ phí cấp lại văn bản bưu chính là bao nhiêu?",
            "was_rewritten": False,
            "intent_resolution": {"intent": "ask_question", "needs_retrieval": True},
            "retrieval_plan": {"action": "need_clarification", "target_scope": "need_clarification"},
            "runtime_context": {
                "recent_chat_history": [{"role": "user", "content": "long history should not be sent"}],
                "last_resolved_context": {
                    "scope": "system_procedure",
                    "source_type": SOURCE_TYPE_SYSTEM,
                    "procedure_title": "Cấp lại văn bản bưu chính",
                    "filter": {"source_type": SOURCE_TYPE_SYSTEM, "procedure_title": "Cấp lại văn bản bưu chính"},
                },
                "current_session_docs": [{"document_id": "doc_1"}, {"document_id": "doc_2"}],
            },
            "document_candidates": [{"document_id": "cand_1"}],
        }
    )

    assert payload["query"] == "lệ phí cấp lại văn bản bưu chính là bao nhiêu?"
    assert payload["intent"] == "ask_question"
    assert payload["has_last_filter"] is True
    assert payload["last_scope"] == "system_procedure"
    assert payload["last_procedure_title"] == "Cấp lại văn bản bưu chính"
    assert payload["current_session_doc_count"] == 2
    assert payload["candidate_count"] == 1
    assert "recent_chat_history" not in payload
    assert "retrieval_plan" not in payload
    assert "last_resolved_context" not in payload


def test_scope_analyzer_maps_compact_system_output_to_full_resolution():
    analyzer = ScopeAnalyzer()

    resolution = analyzer._clean_payload(
        {
            "scope": "system_procedure",
            "mode": "resolve_new_procedure",
            "reuse": False,
            "source": SOURCE_TYPE_SYSTEM,
            "hint": "cấp lại văn bản bưu chính",
            "topic": "lệ phí hành chính",
            "clarify": False,
            "confidence": 0.91,
            "reason": "system procedure fee",
        }
    )

    assert resolution.scope == "system_procedure"
    assert resolution.resolution_mode == "resolve_new_procedure"
    assert resolution.source_type == SOURCE_TYPE_SYSTEM
    assert resolution.procedure_title_hint == "cấp lại văn bản bưu chính"
    assert resolution.document_topic_hint == "lệ phí hành chính"
    assert resolution.confidence == 0.91
    assert resolution.used_llm is True


def test_scope_analyzer_maps_compact_upload_output_to_filename_hint():
    analyzer = ScopeAnalyzer()

    resolution = analyzer._clean_payload(
        {
            "scope": "user_file_name",
            "mode": "resolve_by_filename",
            "source": SOURCE_TYPE_USER_UPLOAD,
            "hint": "hop_dong.pdf",
            "confidence": 0.9,
        }
    )

    assert resolution.scope == "user_file_name"
    assert resolution.source_type == SOURCE_TYPE_USER_UPLOAD
    assert resolution.document_name_hint == "hop_dong.pdf"


def test_scope_analyzer_routes_clear_administrative_question_to_system_docs(monkeypatch):
    analyzer = ScopeAnalyzer()

    class FakeChain:
        def invoke(self, _payload):
            return (
                '{"scope":"need_clarification","mode":"need_clarification","reuse":false,'
                '"source":"none","hint":null,"time":null,"topic":null,"clarify":true,'
                '"confidence":0.4,"reason":"Need more context."}'
            )

    monkeypatch.setattr(analyzer, "chain", FakeChain())

    result = analyzer.resolve(
        {
            "original_query": "le phi khi cap lai thong bao van ban buu chinh co le phi la bao nhieu the ban",
            "final_query": "le phi khi cap lai thong bao van ban buu chinh co le phi la bao nhieu the ban",
            "runtime_context": {},
        }
    )

    assert result.scope == "system_docs"
    assert result.source_type == SOURCE_TYPE_SYSTEM
    assert result.needs_clarification is False
