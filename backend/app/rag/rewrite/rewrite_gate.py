from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.utils.text_utils import count_tokens_rough


@dataclass
class RewriteGateDecision:
    needs_rewrite: bool
    reason: str
    matched_rules: list[str] = field(default_factory=list)
    used_llm: bool = False

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


class RewriteGate:
    max_history_tokens = 600

    def __init__(self) -> None:
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    (
                        "Bạn là Rewrite Gate cho hệ thống RAG tiếng Việt.\n"
                        "Nhiệm vụ: quyết định query hiện tại có cần rewrite thành standalone query trước intent routing hay không.\n"
                        "Chỉ trả JSON hợp lệ, không markdown, không giải thích ngoài JSON.\n\n"
                        "needs_rewrite=true khi câu hỏi là follow-up/mơ hồ và cần lịch sử để hiểu đúng, ví dụ: "
                        "'còn lệ phí thì sao?', 'thế thời hạn bao lâu?', 'nó yêu cầu giấy tờ gì?', 'file này thì sao?'.\n"
                        "needs_rewrite=false khi câu hỏi đã rõ nghĩa, là chào hỏi, hoặc không có đủ context lịch sử.\n"
                        "Không quyết định scope, không trả lời câu hỏi.\n\n"
                        "Schema JSON:\n"
                        "{\"needs_rewrite\": true|false, \"reason\": \"...\", \"matched_rules\": [\"...\"]}"
                    ),
                ),
                (
                    "human",
                    (
                        "original_query: còn thời hạn thì sao?\n"
                        "active_document: ho_so_alpha.pdf\n"
                        "active_procedure: \n"
                        "recent_messages:\n"
                        "user: File ho_so_alpha.pdf nói gì về lệ phí?\n"
                        "assistant: Theo file ho_so_alpha.pdf, lệ phí nội bộ là 75.000 đồng."
                    ),
                ),
                (
                    "ai",
                    "{\"needs_rewrite\": true, \"reason\": \"Câu hỏi nối tiếp cần file trước đó để hiểu đúng.\", \"matched_rules\": [\"follow_up\", \"active_document\", \"has_history\"]}",
                ),
                (
                    "human",
                    (
                        "original_query: Chào bạn\n"
                        "active_document: ho_so_alpha.pdf\n"
                        "active_procedure: \n"
                        "recent_messages:\n"
                        "user: File ho_so_alpha.pdf nói gì?\n"
                        "assistant: File nói về hồ sơ Alpha."
                    ),
                ),
                (
                    "ai",
                    "{\"needs_rewrite\": false, \"reason\": \"Câu chào hỏi không cần rewrite để retrieval.\", \"matched_rules\": [\"general_query\"]}",
                ),
                (
                    "human",
                    (
                        "original_query: {original_query}\n"
                        "active_document: {active_document}\n"
                        "active_procedure: {active_procedure}\n"
                        "recent_messages:\n{recent_messages}"
                    ),
                ),
            ]
        )
        self.chain = None
        if settings.OPENROUTER_API_KEY:
            default_headers = {}
            if settings.OPENROUTER_SITE_URL:
                default_headers["HTTP-Referer"] = settings.OPENROUTER_SITE_URL
            if settings.OPENROUTER_APP_NAME:
                default_headers["X-Title"] = settings.OPENROUTER_APP_NAME
            llm = ChatOpenAI(
                model=settings.OPENROUTER_REWRITE_GATE_MODEL,
                api_key=settings.OPENROUTER_API_KEY,
                base_url=settings.OPENROUTER_BASE_URL,
                temperature=0,
                default_headers=default_headers or None,
            )
            self.chain = self.prompt | llm | StrOutputParser()

    def _format_recent_messages(self, conversation_state: dict[str, Any]) -> str:
        history = conversation_state.get("recent_chat_history") or []
        selected_lines: list[str] = []
        token_count = 0
        for item in reversed(history):
            role = str(item.get("role", "user")).strip()
            content = str(item.get("content", "")).strip()
            if not content:
                continue
            line = f"{role}: {content}"
            line_tokens = count_tokens_rough(line)
            if selected_lines and token_count + line_tokens > self.max_history_tokens:
                break
            selected_lines.append(line)
            token_count += line_tokens
        return "\n".join(reversed(selected_lines))

    def _active_document(self, conversation_state: dict[str, Any]) -> str:
        last_doc = conversation_state.get("last_referenced_doc") or {}
        filename = conversation_state.get("last_filename")
        if not filename and isinstance(last_doc, dict):
            filename = last_doc.get("filename")
        return filename or ""

    def _active_procedure(self, conversation_state: dict[str, Any]) -> str:
        last_doc = conversation_state.get("last_referenced_doc") or {}
        procedure_title = conversation_state.get("last_procedure_title")
        if not procedure_title and isinstance(last_doc, dict):
            procedure_title = last_doc.get("procedure_title")
        return procedure_title or ""

    def _fallback_decision(self) -> RewriteGateDecision:
        return RewriteGateDecision(
            needs_rewrite=False,
            reason="Rewrite gate LLM is unavailable or returned invalid JSON; defaulted to no rewrite.",
            matched_rules=["llm_unavailable"],
            used_llm=False,
        )

    def decide(
        self,
        original_query: str,
        conversation_state: dict[str, Any] | None = None,
    ) -> RewriteGateDecision:
        conversation_state = conversation_state or {}
        if self.chain is None:
            return self._fallback_decision()

        try:
            raw = self.chain.invoke(
                {
                    "original_query": original_query,
                    "active_document": self._active_document(conversation_state),
                    "active_procedure": self._active_procedure(conversation_state),
                    "recent_messages": self._format_recent_messages(conversation_state),
                }
            ).strip()
            if raw.startswith("```"):
                raw = raw.strip("`")
                raw = raw.removeprefix("json").strip()
            payload = json.loads(raw)
        except Exception:
            return self._fallback_decision()

        return RewriteGateDecision(
            needs_rewrite=bool(payload.get("needs_rewrite")),
            reason=str(payload.get("reason") or "Resolved by OpenRouter rewrite gate."),
            matched_rules=[str(item) for item in payload.get("matched_rules", []) if item],
            used_llm=True,
        )
