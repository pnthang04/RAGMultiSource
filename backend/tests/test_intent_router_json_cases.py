import json
from pathlib import Path

from app.rag.query import IntentRouter


CASES_PATH = Path(__file__).parent / "fixtures" / "intent_router_cases.json"


def test_intent_router_json_cases():
    router = IntentRouter()

    for case in json.loads(CASES_PATH.read_text(encoding="utf-8")):
        result = router.route(case["question"], conversation_state=case.get("conversation_state"))

        assert result.intent == case["expected_intent"], case["id"]
        assert result.needs_retrieval is case["expected_needs_retrieval"], case["id"]
        if "expected_is_follow_up" in case:
            assert result.is_follow_up is case["expected_is_follow_up"], case["id"]
