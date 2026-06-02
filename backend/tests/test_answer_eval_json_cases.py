import json
from pathlib import Path

from app.rag.generation.openai_llm import OpenAILLMService
from app.rag.generation.source_formatter import SourceFormatter
from app.rag.retrieval.context_validator import FALLBACK_NO_CONTEXT


CASES_PATH = Path(__file__).parent / "fixtures" / "answer_eval_cases.json"


def test_answer_eval_source_formatting_json_cases():
    formatter = SourceFormatter()

    for case in json.loads(CASES_PATH.read_text(encoding="utf-8")):
        formatted = formatter.format_answer(case["answer"], case["sources"])
        if "expected_prefix" in case:
            assert formatted.startswith(case["expected_prefix"]), case["id"]
        if "expected_contains" in case:
            assert case["expected_contains"] in formatted, case["id"]


def test_answer_eval_empty_context_fallback():
    llm = OpenAILLMService()

    answer = llm.generate_answer("Ho so gom gi?", contexts=[])

    assert answer == FALLBACK_NO_CONTEXT


def test_answer_eval_replaces_clarification_request_with_fallback():
    llm = OpenAILLMService()

    class FakeChain:
        def invoke(self, payload):
            _ = payload
            return "Ban co the cung cap them thong tin ve su kien de minh xac dinh chinh xac hon khong?"

    llm.chain = FakeChain()
    answer = llm.generate_answer(
        "so nguoi tham du sinh nhat",
        contexts=[
            {
                "content": "Nhom chuan bi gom 6 thanh vien.",
                "metadata": {"source_type": "user_upload", "filename": "plan.docx"},
            }
        ],
    )

    assert answer == FALLBACK_NO_CONTEXT
