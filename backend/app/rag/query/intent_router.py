from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import asdict, dataclass, field
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings


INTENT_ASK_QUESTION = "ask_question"
INTENT_SUMMARIZE_DOCUMENT = "summarize_document"
INTENT_COMPARE_DOCUMENTS = "compare_documents"
INTENT_FIND_INFORMATION = "find_information"
INTENT_GENERAL_QUERY = "general_query"
INTENT_NEED_CLARIFICATION = "need_clarification"
INTENT_UNSUPPORTED = "unsupported"

ANSWER_STYLE_SHORT = "short_answer"
ANSWER_STYLE_BULLET_LIST = "bullet_list"
ANSWER_STYLE_SUMMARY = "summary"
ANSWER_STYLE_COMPARISON = "comparison"
ANSWER_STYLE_STEPS = "steps"


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    stripped = "".join(char for char in normalized if not unicodedata.combining(char))
    stripped = stripped.replace("đ", "d")
    return re.sub(r"\s+", " ", stripped).strip()


@dataclass
class IntentResolution:
    intent: str
    answer_style: str = ANSWER_STYLE_SHORT
    is_follow_up: bool = False
    needs_retrieval: bool = True
    confidence: float = 0.75
    matched_rules: list[str] = field(default_factory=list)
    reason: str | None = None

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


class IntentRouter:
    _document_terms = (
        "file",
        "tai lieu",
        "van ban",
        "thu tuc",
        "ho so",
        "quy dinh",
        "quy trinh",
        "le phi",
        "thoi han",
        "giay to",
        "trinh tu",
        "cach thuc",
        "thuc hien",
        "nop ho so",
        "co quan",
    )
    _ambiguous_terms = ("tai lieu do", "file do", "van ban do", "cai do")

    def __init__(self) -> None:
        self.chain = None
        if settings.INTENT_ROUTER_USE_LLM and settings.OPENROUTER_API_KEY:
            prompt = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        (
                            "You are an intent router for a Vietnamese administrative-document RAG system.\n"
                            "Choose exactly one intent: ask_question, summarize_document, compare_documents, "
                            "find_information, general_query, need_clarification, unsupported.\n"
                            "Choose answer_style: short_answer, bullet_list, summary, comparison, steps.\n"
                            "Use needs_retrieval=true for questions about administrative procedures, documents, fees, "
                            "deadlines, dossiers, required papers, regulations, uploaded files, or system documents.\n"
                            "Use general_query only for greetings or questions about the chatbot itself.\n"
                            "Do not use a follow_up intent; the query was already rewritten when needed.\n"
                            "Return valid JSON only, no markdown, no explanation.\n"
                            "Schema: {\"intent\":\"...\",\"answer_style\":\"...\",\"needs_retrieval\":true,"
                            "\"confidence\":0.0,\"reason\":\"...\"}"
                        ),
                    ),
                    ("human", "Query: {question}"),
                ]
            )
            default_headers = {}
            if settings.OPENROUTER_SITE_URL:
                default_headers["HTTP-Referer"] = settings.OPENROUTER_SITE_URL
            if settings.OPENROUTER_APP_NAME:
                default_headers["X-Title"] = settings.OPENROUTER_APP_NAME
            llm = ChatOpenAI(
                model=settings.OPENROUTER_INTENT_MODEL,
                api_key=settings.OPENROUTER_API_KEY,
                base_url=settings.OPENROUTER_BASE_URL,
                temperature=0,
                default_headers=default_headers or None,
            )
            self.chain = prompt | llm | StrOutputParser()

    def _contains_any(self, text: str, terms: tuple[str, ...]) -> bool:
        return any(term in text for term in terms)

    def _answer_style(self, text: str, intent: str) -> str:
        if intent == INTENT_COMPARE_DOCUMENTS:
            return ANSWER_STYLE_COMPARISON
        if intent == INTENT_SUMMARIZE_DOCUMENT:
            return ANSWER_STYLE_SUMMARY
        if any(term in text for term in ("cac buoc", "quy trinh", "cach thuc")):
            return ANSWER_STYLE_STEPS
        if any(term in text for term in ("liet ke", "danh sach", "gom nhung gi", "can ho so", "ho so gi", "giay to gi")):
            return ANSWER_STYLE_BULLET_LIST
        return ANSWER_STYLE_SHORT

    def _route_with_llm(self, question: str) -> IntentResolution | None:
        if self.chain is None:
            return None
        try:
            raw = self.chain.invoke({"question": question}).strip()
            if raw.startswith("```"):
                raw = raw.strip("`")
                raw = raw.removeprefix("json").strip()
            payload = json.loads(raw)
        except Exception:
            return None

        allowed_intents = {
            INTENT_ASK_QUESTION,
            INTENT_SUMMARIZE_DOCUMENT,
            INTENT_COMPARE_DOCUMENTS,
            INTENT_FIND_INFORMATION,
            INTENT_GENERAL_QUERY,
            INTENT_NEED_CLARIFICATION,
            INTENT_UNSUPPORTED,
        }
        intent = payload.get("intent")
        if intent not in allowed_intents:
            return None
        answer_style = payload.get("answer_style") or ANSWER_STYLE_SHORT
        if answer_style not in {
            ANSWER_STYLE_SHORT,
            ANSWER_STYLE_BULLET_LIST,
            ANSWER_STYLE_SUMMARY,
            ANSWER_STYLE_COMPARISON,
            ANSWER_STYLE_STEPS,
        }:
            answer_style = ANSWER_STYLE_SHORT
        return IntentResolution(
            intent=intent,
            answer_style=answer_style,
            is_follow_up=False,
            needs_retrieval=bool(payload.get("needs_retrieval", intent not in {INTENT_GENERAL_QUERY, INTENT_NEED_CLARIFICATION, INTENT_UNSUPPORTED})),
            confidence=float(payload.get("confidence", 0.75)),
            matched_rules=["llm_intent_router"],
            reason=payload.get("reason") or "Resolved by OpenRouter intent router.",
        )

    def _route_by_rules(self, question: str, conversation_state: dict[str, Any] | None = None) -> IntentResolution:
        conversation_state = conversation_state or {}
        text = _normalize_text(question)
        matched_rules: list[str] = []
        _ = conversation_state

        if self._contains_any(text, self._ambiguous_terms):
            return IntentResolution(
                intent=INTENT_NEED_CLARIFICATION,
                needs_retrieval=False,
                confidence=0.9,
                matched_rules=["ambiguous_reference_without_state"],
                reason="Question references a document ambiguously without conversation state.",
            )

        if any(term in text for term in ("ve tranh", "tao anh", "viet code", "lap trinh", "dat ve", "mua hang")):
            return IntentResolution(
                intent=INTENT_UNSUPPORTED,
                needs_retrieval=False,
                confidence=0.82,
                matched_rules=["unsupported_non_rag_task"],
                reason="Question is outside the supported document QA scope.",
            )

        if any(term in text for term in ("so sanh", "doi chieu", "khac nhau", "giong nhau", "dap ung")):
            intent = INTENT_COMPARE_DOCUMENTS
            matched_rules.append("compare")
        elif any(term in text for term in ("tom tat", "noi dung chinh", "tong quan")):
            intent = INTENT_SUMMARIZE_DOCUMENT
            matched_rules.append("summarize")
        elif any(term in text for term in ("tim", "tra cuu", "cho biet", "kiem tra")):
            intent = INTENT_FIND_INFORMATION
            matched_rules.append("find_information")
        elif self._contains_any(text, self._document_terms):
            intent = INTENT_ASK_QUESTION
            matched_rules.append("document_question")
        else:
            return IntentResolution(
                intent=INTENT_GENERAL_QUERY,
                needs_retrieval=False,
                confidence=0.82,
                matched_rules=["no_document_signal"],
                reason="Question does not appear to target documents.",
            )

        return IntentResolution(
            intent=intent,
            answer_style=self._answer_style(text, intent),
            is_follow_up=False,
            needs_retrieval=True,
            confidence=0.8,
            matched_rules=matched_rules,
            reason="Resolved by deterministic query rules.",
        )

    def route(self, question: str, conversation_state: dict[str, Any] | None = None) -> IntentResolution:
        rule_result = self._route_by_rules(question, conversation_state=conversation_state)
        llm_result = self._route_with_llm(question)
        if llm_result is None:
            return rule_result

        # Deterministic rules are the safety rail: never let the LLM classify a
        # clear administrative/document question as a non-retrieval query.
        if rule_result.needs_retrieval and not llm_result.needs_retrieval:
            rule_result.matched_rules.append("llm_false_negative_guard")
            rule_result.reason = "Rule-based guard kept a document/admin question in the RAG path."
            return rule_result

        if llm_result.confidence < 0.7 and rule_result.confidence >= llm_result.confidence:
            rule_result.matched_rules.append("low_confidence_llm_fallback")
            return rule_result

        return llm_result
