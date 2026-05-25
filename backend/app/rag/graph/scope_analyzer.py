# -*- coding: utf-8 -*-
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
from app.core.constants import (
    RETRIEVAL_SCOPE_CURRENT_SESSION_UPLOADS,
    RETRIEVAL_SCOPE_GENERAL_QUERY,
    RETRIEVAL_SCOPE_HYBRID_SYSTEM_AND_USER,
    RETRIEVAL_SCOPE_NEED_CLARIFICATION,
    RETRIEVAL_SCOPE_SYSTEM_DOCS,
    RETRIEVAL_SCOPE_SYSTEM_PROCEDURE,
    RETRIEVAL_SCOPE_USER_ALL_UPLOADS,
    RETRIEVAL_SCOPE_USER_FILE_NAME,
    SOURCE_TYPE_SYSTEM,
    SOURCE_TYPE_USER_UPLOAD,
)


SCOPE_VALUES = {
    RETRIEVAL_SCOPE_SYSTEM_DOCS,
    RETRIEVAL_SCOPE_SYSTEM_PROCEDURE,
    RETRIEVAL_SCOPE_CURRENT_SESSION_UPLOADS,
    RETRIEVAL_SCOPE_USER_ALL_UPLOADS,
    RETRIEVAL_SCOPE_USER_FILE_NAME,
    RETRIEVAL_SCOPE_HYBRID_SYSTEM_AND_USER,
    RETRIEVAL_SCOPE_GENERAL_QUERY,
    RETRIEVAL_SCOPE_NEED_CLARIFICATION,
}

RESOLUTION_MODES = {
    "reuse_last_context",
    "switch_scope",
    "resolve_new_procedure",
    "resolve_current_upload",
    "resolve_previous_upload",
    "resolve_by_filename",
    "resolve_by_time_hint",
    "semantic_document_search",
    "mixed",
    "need_clarification",
}


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    stripped = "".join(char for char in normalized if not unicodedata.combining(char))
    stripped = stripped.replace("đ", "d")
    return re.sub(r"\s+", " ", stripped).strip()


@dataclass
class StructuredScopeResolution:
    action: str = "resolve_document"
    scope: str = RETRIEVAL_SCOPE_NEED_CLARIFICATION
    hints: dict[str, Any] = field(default_factory=dict)
    branches: list[dict[str, Any]] = field(default_factory=list)
    clarification_question: str | None = None
    confidence: float = 0.0
    should_reuse_last_filter: bool = False
    source_type: str = "none"
    procedure_title_hint: str | None = None
    document_name_hint: str | None = None
    document_id_hint: str | None = None
    time_hint: str | None = None
    document_topic_hint: str | None = None
    resolution_mode: str = "need_clarification"
    needs_clarification: bool = False
    reason: str = ""
    used_llm: bool = False

    def model_dump(self) -> dict[str, Any]:
        scope = self.scope
        if scope == RETRIEVAL_SCOPE_SYSTEM_DOCS:
            scope = RETRIEVAL_SCOPE_SYSTEM_PROCEDURE
        action = self.action
        if self.should_reuse_last_filter:
            action = "reuse_last_filter"
        elif scope == RETRIEVAL_SCOPE_HYBRID_SYSTEM_AND_USER or self.resolution_mode == "mixed":
            action = "mixed_retrieval"
        elif self.needs_clarification or scope == RETRIEVAL_SCOPE_NEED_CLARIFICATION:
            action = "need_clarification"
        elif action not in {"reuse_last_filter", "resolve_document", "mixed_retrieval", "need_clarification"}:
            action = "resolve_document"
        hints = {
            "procedure_title": self.hints.get("procedure_title") or self.procedure_title_hint,
            "time": self.hints.get("time") or self.time_hint,
        }
        return {
            "action": action,
            "scope": scope,
            "hints": hints,
            "branches": self.branches,
            "clarification_question": self.clarification_question,
            "confidence": self.confidence,
        }


class ScopeAnalyzer:
    source_switch_terms = (
        "vua upload",
        "vua up",
        "toi vua upload",
        "toi vua up",
        "file toi",
        "tai lieu cua toi",
        "theo tai lieu cua toi",
        "file vua upload",
        "file vua gui",
        "tai lieu vua gui",
        "file toi upload hom qua",
        "file hom qua toi upload",
        "hom truoc",
        "tuan truoc",
        "tuan sau",
        "hom kia",
        "ngay ",
        "lan truoc",
        "tai lieu cu",
        "file da tung upload",
        "so sanh",
        "doi chieu",
        "voi quy dinh he thong",
    )
    system_document_terms = (
        "le phi",
        "phi",
        "cap lai",
        "thong bao",
        "van ban buu chinh",
        "buu chinh",
        "thoi han",
        "giay to",
        "ho so",
        "co quan",
        "noi nop",
        "quy dinh",
    )

    def __init__(self) -> None:
        self.chain = None
        if settings.SCOPE_RESOLVER_USE_LLM and settings.OPENROUTER_API_KEY:
            default_headers = {}
            if settings.OPENROUTER_SITE_URL:
                default_headers["HTTP-Referer"] = settings.OPENROUTER_SITE_URL
            if settings.OPENROUTER_APP_NAME:
                default_headers["X-Title"] = settings.OPENROUTER_APP_NAME
            llm = ChatOpenAI(
                model=settings.OPENROUTER_SCOPE_MODEL,
                api_key=settings.OPENROUTER_API_KEY,
                base_url=settings.OPENROUTER_BASE_URL,
                temperature=0,
                max_tokens=settings.OPENROUTER_SCOPE_MAX_TOKENS,
                default_headers=default_headers or None,
            )
            self.chain = self._prompt() | llm | StrOutputParser()

    def _prompt(self) -> ChatPromptTemplate:
        system_prompt = """B\u1ea1n l\u00e0 chuy\u00ean gia ph\u00e2n lo\u1ea1i scope cho h\u1ec7 th\u1ed1ng h\u1ecfi \u0111\u00e1p t\u00e0i li\u1ec7u h\u00e0nh ch\u00ednh Vi\u1ec7t Nam.
Nhi\u1ec7m v\u1ee5 duy nh\u1ea5t c\u1ee7a b\u1ea1n l\u00e0 x\u00e1c \u0111\u1ecbnh scope truy h\u1ed3i. Kh\u00f4ng tr\u1ea3 l\u1eddi c\u00e2u h\u1ecfi c\u1ee7a ng\u01b0\u1eddi d\u00f9ng.
Kh\u00f4ng t\u1ea1o metadata filter. Kh\u00f4ng ch\u1ecdn document_id. Kh\u00f4ng quy\u1ebft \u0111\u1ecbnh quy\u1ec1n truy c\u1eadp.

Tr\u1ea3 v\u1ec1 \u0111\u00fang M\u1ed8T object JSON h\u1ee3p l\u1ec7. Kh\u00f4ng markdown. Kh\u00f4ng gi\u1ea3i th\u00edch. Kh\u00f4ng th\u00eam key kh\u00e1c.

Schema b\u1eaft bu\u1ed9c:
{
  "action": "reuse_last_filter | resolve_document | mixed_retrieval | need_clarification",
  "scope": "system_procedure | current_session_uploads | user_all_uploads | hybrid_system_and_user",
  "hints": {
    "procedure_title": null,
    "time": null
  },
  "branches": [],
  "clarification_question": null,
  "confidence": 0.0
}

\u00dd ngh\u0129a c\u1ee7a action:
- reuse_last_filter: c\u00e2u follow-up an to\u00e0n, c\u00f3 th\u1ec3 d\u00f9ng l\u1ea1i filter \u0111\u00e3 resolve tr\u01b0\u1edbc \u0111\u00f3.
- resolve_document: c\u1ea7n resolve m\u1ed9t t\u00e0i li\u1ec7u h\u1ec7 th\u1ed1ng ho\u1eb7c t\u00e0i li\u1ec7u ng\u01b0\u1eddi d\u00f9ng m\u1edbi.
- mixed_retrieval: c\u1ea7n truy h\u1ed3i c\u1ea3 t\u00e0i li\u1ec7u h\u1ec7 th\u1ed1ng v\u00e0 t\u00e0i li\u1ec7u ng\u01b0\u1eddi d\u00f9ng.
- need_clarification: ch\u1ec9 d\u00f9ng khi ngu\u1ed3n ho\u1eb7c t\u00e0i li\u1ec7u th\u1eadt s\u1ef1 m\u01a1 h\u1ed3.

Quy t\u1eafc scope:
- system_procedure: c\u00e2u h\u1ecfi v\u1ec1 th\u1ee7 t\u1ee5c h\u00e0nh ch\u00ednh, l\u1ec7 ph\u00ed, gi\u1ea5y t\u1edd c\u1ea7n chu\u1ea9n b\u1ecb, th\u1eddi h\u1ea1n, n\u01a1i n\u1ed9p, quy \u0111\u1ecbnh.
- current_session_uploads: ng\u01b0\u1eddi d\u00f9ng h\u1ecfi file ho\u1eb7c t\u00e0i li\u1ec7u v\u1eeba upload, ho\u1eb7c t\u00e0i li\u1ec7u \u0111ang n\u1eb1m trong session hi\u1ec7n t\u1ea1i.
- user_all_uploads: ng\u01b0\u1eddi d\u00f9ng h\u1ecfi file ho\u1eb7c t\u00e0i li\u1ec7u \u0111\u00e3 upload tr\u01b0\u1edbc \u0111\u00f3, h\u00f4m qua, h\u00f4m tr\u01b0\u1edbc, tu\u1ea7n tr\u01b0\u1edbc, ho\u1eb7c m\u1ed9t m\u1ed1c ng\u00e0y c\u1ee5 th\u1ec3.
- hybrid_system_and_user: ng\u01b0\u1eddi d\u00f9ng so s\u00e1nh ho\u1eb7c \u0111\u1ed1i chi\u1ebfu file upload v\u1edbi quy \u0111\u1ecbnh h\u1ec7 th\u1ed1ng.

Quy t\u1eafc quy\u1ebft \u0111\u1ecbnh:
- N\u1ebfu was_rewritten=true, has_last_filter=true, v\u00e0 c\u00e2u h\u1ecfi kh\u00f4ng chuy\u1ec3n sang ngu\u1ed3n upload, ngu\u1ed3n c\u0169, ho\u1eb7c mixed, ch\u1ecdn reuse_last_filter.
- N\u1ebfu c\u00e2u h\u1ecfi nh\u1eafc \u0111\u1ebfn file v\u1eeba upload, t\u00e0i li\u1ec7u v\u1eeba g\u1eedi, file c\u1ee7a t\u00f4i, file hi\u1ec7n t\u1ea1i, ch\u1ecdn resolve_document + current_session_uploads.
- N\u1ebfu c\u00e2u h\u1ecfi nh\u1eafc \u0111\u1ebfn file c\u0169, t\u00e0i li\u1ec7u h\u00f4m qua, h\u00f4m tr\u01b0\u1edbc, tu\u1ea7n tr\u01b0\u1edbc, ho\u1eb7c c\u00f3 m\u1ed1c ng\u00e0y, ch\u1ecdn resolve_document + user_all_uploads v\u00e0 \u0111i\u1ec1n hints.time.
- N\u1ebfu c\u00e2u h\u1ecfi v\u1ec1 th\u1ee7 t\u1ee5c h\u00e0nh ch\u00ednh m\u00e0 kh\u00f4ng c\u00f3 t\u00edn hi\u1ec7u upload, ch\u1ecdn resolve_document + system_procedure.
- N\u1ebfu c\u00e2u h\u1ecfi so s\u00e1nh file upload v\u1edbi quy \u0111\u1ecbnh h\u1ec7 th\u1ed1ng, ch\u1ecdn mixed_retrieval + hybrid_system_and_user.
- Ch\u1ec9 d\u00f9ng need_clarification khi th\u1eadt s\u1ef1 kh\u00f4ng th\u1ec3 ph\u00e2n bi\u1ec7t \u0111\u01b0\u1ee3c gi\u1eefa c\u00e1c ngu\u1ed3n. Trong h\u1ec7 th\u1ed1ng n\u00e0y, need_clarification ph\u1ea3i r\u1ea5t hi\u1ebfm.

Quy t\u1eafc cho hints:
- hints.procedure_title: ch\u1ec9 \u0111i\u1ec1n khi c\u00e2u h\u1ecfi n\u00f3i r\u00f5 ho\u1eb7c ng\u1ee5 \u00fd r\u00f5 m\u1ed9t th\u1ee7 t\u1ee5c h\u00e0nh ch\u00ednh c\u1ee5 th\u1ec3.
- hints.time: ch\u1ec9 \u0111i\u1ec1n khi c\u00e2u h\u1ecfi c\u00f3 t\u00edn hi\u1ec7u th\u1eddi gian nh\u01b0 h\u00f4m qua, h\u00f4m tr\u01b0\u1edbc, tu\u1ea7n tr\u01b0\u1edbc, ho\u1eb7c m\u1ed9t ng\u00e0y c\u1ee5 th\u1ec3.
- N\u1ebfu kh\u00f4ng ch\u1eafc, d\u00f9ng null.
- confidence ph\u1ea3i n\u1eb1m trong kho\u1ea3ng 0 \u0111\u1ebfn 1.

V\u00ed d\u1ee5 h\u00e0nh vi mong \u0111\u1ee3i:
- "file t\u00f4i v\u1eeba up n\u00f3i g\u00ec?" -> current_session_uploads, resolve_document.
- "t\u00e0i li\u1ec7u t\u00f4i up tu\u1ea7n tr\u01b0\u1edbc n\u00f3i g\u00ec?" -> user_all_uploads, resolve_document, hints.time = "last_week".
- "l\u1ec7 ph\u00ed khi c\u1ea5p l\u1ea1i th\u00f4ng b\u00e1o v\u0103n b\u1ea3n b\u01b0u ch\u00ednh l\u00e0 bao nhi\u00eau?" -> system_procedure, resolve_document, confidence cao.
- "\u0111\u1ed1i chi\u1ebfu file t\u00f4i upload v\u1edbi quy \u0111\u1ecbnh h\u1ec7 th\u1ed1ng" -> hybrid_system_and_user, mixed_retrieval.
- "c\u1ea7n chu\u1ea9n b\u1ecb g\u00ec?" khi c\u00f3 last_filter v\u00e0 l\u00e0 follow-up an to\u00e0n -> reuse_last_filter.
"""

        return ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                (
                    "human",
                    "Ph\u00e2n lo\u1ea1i state sau \u0111\u00e2y:\n{state_json}\n\nCh\u1ec9 tr\u1ea3 JSON.",
                ),
                (
                    "human",
                    "V\u00ed d\u1ee5 1: T\u00f4i v\u1eeba upload file n\u00e0y, n\u00f3 n\u00f3i g\u00ec?",
                ),
                (
                    "ai",
                    '{"action":"resolve_document","scope":"current_session_uploads","hints":{"procedure_title":null,"time":null},"branches":[],"clarification_question":null,"confidence":0.92}',
                ),
                (
                    "human",
                    "V\u00ed d\u1ee5 2: T\u00e0i li\u1ec7u t\u00f4i up tu\u1ea7n tr\u01b0\u1edbc c\u00f3 n\u1ed9i dung g\u00ec?",
                ),
                (
                    "ai",
                    '{"action":"resolve_document","scope":"user_all_uploads","hints":{"procedure_title":null,"time":"last_week"},"branches":[],"clarification_question":null,"confidence":0.9}',
                ),
                (
                    "human",
                    "V\u00ed d\u1ee5 3: L\u1ec7 ph\u00ed khi c\u1ea5p l\u1ea1i th\u00f4ng b\u00e1o v\u0103n b\u1ea3n b\u01b0u ch\u00ednh l\u00e0 bao nhi\u00eau th\u1ebf b\u1ea1n?",
                ),
                (
                    "ai",
                    '{"action":"resolve_document","scope":"system_procedure","hints":{"procedure_title":"c?p l?i th?ng b?o v?n b?n b?u ch?nh","time":null},"branches":[],"clarification_question":null,"confidence":0.95}',
                ),
                (
                    "human",
                    "V\u00ed d\u1ee5 4: \u0110\u1ed1i chi\u1ebfu file t\u00f4i upload v\u1edbi quy \u0111\u1ecbnh h\u1ec7 th\u1ed1ng",
                ),
                (
                    "ai",
                    '{"action":"mixed_retrieval","scope":"hybrid_system_and_user","hints":{"procedure_title":null,"time":null},"branches":[{"branch_name":"system","scope":"system_procedure"},{"branch_name":"user_upload","scope":"current_session_uploads"}],"clarification_question":null,"confidence":0.9}',
                ),
                (
                    "human",
                    "V\u00ed d\u1ee5 5: C\u1ea7n chu\u1ea9n b\u1ecb g\u00ec?",
                ),
                (
                    "ai",
                    '{"action":"reuse_last_filter","scope":"system_procedure","hints":{"procedure_title":"??ng k? k?t h?n","time":null},"branches":[],"clarification_question":null,"confidence":0.88}',
                ),
            ]
        )
    def _has_source_switch_signal(self, query: str) -> bool:
        normalized = _normalize_text(query)
        return any(term in normalized for term in self.source_switch_terms) or bool(
            re.search(r"\b[a-z0-9][a-z0-9_\-\s().\[\]]*\.(?:pdf|docx?|xlsx?|pptx?|txt|md)\b", normalized)
        )

    def _has_system_document_signal(self, query: str) -> bool:
        normalized = _normalize_text(query)
        return any(term in normalized for term in self.system_document_terms)

    def _filename_hint(self, query: str) -> str | None:
        match = re.search(r"\b([a-z0-9][a-z0-9_\-().\[\]]*\.(?:pdf|docx?|xlsx?|pptx?|txt|md))\b", query, re.I)
        return match.group(0).strip() if match else None

    def _procedure_hint(self, query: str) -> str | None:
        match = re.search(r"(?i)(?:thủ tục|thu tuc)\s+(.+?)(?:\s+cần|\s+can|\s+gồm|\s+gom|\s+là|\s+la|\?|$)", query)
        if not match:
            return None
        candidate = match.group(1).strip(" .,:;?")
        if _normalize_text(candidate) in {"gi", "nao", "nhu nao", "gi vay", "gi the"}:
            return None
        return candidate or None

    def _topic_hint(self, query: str) -> str | None:
        match = re.search(r"(?i)(?:upload về|upload ve|tài liệu.*về|tai lieu.*ve)\s+(.+?)(?:\s+có|\s+co|\s+nói|\s+noi|\?|$)", query)
        if not match:
            return None
        return match.group(1).strip(" .,:;?") or None

    def _time_hint(self, query: str) -> str | None:
        normalized = _normalize_text(query)
        if "hom qua" in normalized:
            return "yesterday"
        if "hom truoc" in normalized:
            return "yesterday"
        if "hom kia" in normalized:
            return "two_days_ago"
        if "tuan truoc" in normalized or "last week" in normalized:
            return "last_week"
        if "tuan sau" in normalized or "next week" in normalized:
            return "next_week"
        match = re.search(r"(?i)ngày\s+(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)", query)
        if match:
            return match.group(1)
        return None

    def _fallback(self, state: dict[str, Any], reason: str = "Resolved by deterministic fallback.") -> StructuredScopeResolution:
        query = state.get("final_query") or state.get("original_query") or ""
        normalized = _normalize_text(query)
        action = state.get("retrieval_plan", {}).get("action")
        last_context = (state.get("runtime_context") or {}).get("last_resolved_context") or {}
        filename = self._filename_hint(query)
        procedure = self._procedure_hint(query)
        topic = self._topic_hint(query)
        time_hint = self._time_hint(query)

        if action == "reuse_last_filter" and last_context.get("filter") and not self._has_source_switch_signal(query):
            return StructuredScopeResolution(
                scope=last_context.get("scope") or RETRIEVAL_SCOPE_NEED_CLARIFICATION,
                resolution_mode="reuse_last_context",
                should_reuse_last_filter=True,
                source_type=last_context.get("source_type") or "none",
                procedure_title_hint=last_context.get("procedure_title"),
                document_name_hint=last_context.get("filename"),
                document_id_hint=last_context.get("document_id"),
                confidence=0.9,
                reason="Safe follow-up reused last resolved context.",
            )
        if any(term in normalized for term in ("so sanh", "doi chieu", "khac nhau", "giong nhau", "dap ung")):
            return StructuredScopeResolution(
                scope=RETRIEVAL_SCOPE_HYBRID_SYSTEM_AND_USER,
                resolution_mode="mixed",
                source_type="hybrid",
                branches=[
                    {"branch_name": "system", "scope": RETRIEVAL_SCOPE_SYSTEM_DOCS},
                    {"branch_name": "user_upload", "scope": RETRIEVAL_SCOPE_CURRENT_SESSION_UPLOADS},
                ],
                confidence=0.84,
                reason=reason,
            )
        if filename:
            return StructuredScopeResolution(
                scope=RETRIEVAL_SCOPE_USER_FILE_NAME,
                resolution_mode="resolve_by_filename",
                source_type=SOURCE_TYPE_USER_UPLOAD,
                document_name_hint=filename,
                confidence=0.88,
                reason=reason,
            )
        if any(
            term in normalized
            for term in (
                "vua upload",
                "vua up",
                "toi vua upload",
                "toi vua up",
                "file vua upload",
                "tai lieu vua upload",
                "file vua gui",
                "tai lieu vua gui",
                "file nay",
                "tai lieu nay",
                "file cua toi",
                "tai lieu cua toi",
                "theo tai lieu cua toi",
            )
        ):
            return StructuredScopeResolution(
                scope=RETRIEVAL_SCOPE_CURRENT_SESSION_UPLOADS,
                resolution_mode="resolve_current_upload",
                source_type=SOURCE_TYPE_USER_UPLOAD,
                confidence=0.86,
                reason=reason,
            )
        if time_hint:
            return StructuredScopeResolution(
                scope=RETRIEVAL_SCOPE_USER_ALL_UPLOADS,
                resolution_mode="resolve_by_time_hint",
                source_type=SOURCE_TYPE_USER_UPLOAD,
                time_hint=time_hint,
                confidence=0.84,
                reason=reason,
            )
        if topic and "upload" in normalized:
            return StructuredScopeResolution(
                scope=RETRIEVAL_SCOPE_USER_ALL_UPLOADS,
                resolution_mode="semantic_document_search",
                source_type=SOURCE_TYPE_USER_UPLOAD,
                document_topic_hint=topic,
                confidence=0.76,
                reason=reason,
            )
        if procedure:
            return StructuredScopeResolution(
                scope=RETRIEVAL_SCOPE_SYSTEM_PROCEDURE,
                resolution_mode="resolve_new_procedure",
                source_type=SOURCE_TYPE_SYSTEM,
                procedure_title_hint=procedure,
                confidence=0.82,
                reason=reason,
            )
        if any(
            term in normalized
            for term in (
                "le phi",
                "phi",
                "cap lai",
                "dang ky",
                "thong bao",
                "van ban buu chinh",
                "buu chinh",
                "ho so",
                "giay to",
                "thoi han",
                "noi nop",
                "co quan",
            )
        ):
            return StructuredScopeResolution(
                scope=RETRIEVAL_SCOPE_SYSTEM_DOCS,
                resolution_mode="resolve_new_procedure",
                source_type=SOURCE_TYPE_SYSTEM,
                confidence=0.7,
                reason="Administrative document question without upload signal; defaulted to system docs.",
            )
        if action == "general_query":
            return StructuredScopeResolution(
                scope=RETRIEVAL_SCOPE_GENERAL_QUERY,
                resolution_mode="need_clarification",
                source_type="none",
                confidence=0.8,
                reason="Intent does not require retrieval.",
            )
        if action == "resolve_system_procedure":
            return StructuredScopeResolution(
                scope=RETRIEVAL_SCOPE_SYSTEM_PROCEDURE,
                resolution_mode="resolve_new_procedure",
                source_type=SOURCE_TYPE_SYSTEM,
                procedure_title_hint=procedure,
                confidence=0.72,
                reason=reason,
            )
        if action == "resolve_current_upload":
            return StructuredScopeResolution(
                scope=RETRIEVAL_SCOPE_CURRENT_SESSION_UPLOADS,
                resolution_mode="resolve_current_upload",
                source_type=SOURCE_TYPE_USER_UPLOAD,
                confidence=0.72,
                reason=reason,
            )
        if action == "resolve_previous_upload":
            return StructuredScopeResolution(
                scope=RETRIEVAL_SCOPE_USER_ALL_UPLOADS,
                resolution_mode="resolve_previous_upload",
                source_type=SOURCE_TYPE_USER_UPLOAD,
                confidence=0.72,
                reason=reason,
            )
        return StructuredScopeResolution(
            scope=RETRIEVAL_SCOPE_NEED_CLARIFICATION,
            resolution_mode="need_clarification",
            source_type="none",
            needs_clarification=True,
            clarification_question="Bạn muốn hỏi tài liệu hệ thống, file vừa upload, file cũ, hay một file cụ thể?",
            confidence=0.45,
            reason=reason,
        )

    def _build_llm_input(self, state: dict[str, Any]) -> dict[str, Any]:
        runtime_context = state.get("runtime_context") or {}
        last_context = runtime_context.get("last_resolved_context") or {}
        current_session_docs = runtime_context.get("current_session_docs", []) or []
        active_document_ids = runtime_context.get("active_document_ids", []) or []
        selected_document_ids = state.get("selected_document_ids", []) or []
        return {
            "query": state.get("final_query") or state.get("original_query"),
            "original_query": state.get("original_query"),
            "was_rewritten": bool(state.get("was_rewritten")),
            "intent": (state.get("intent_resolution") or {}).get("intent"),
            "needs_retrieval": (state.get("intent_resolution") or {}).get("needs_retrieval"),
            "planner_target_scope": (state.get("retrieval_plan") or {}).get("target_scope"),
            "requested_scope": state.get("requested_scope"),
            "has_last_filter": bool(last_context.get("filter")),
            "last_scope": last_context.get("scope") or runtime_context.get("last_scope"),
            "last_source_type": last_context.get("source_type"),
            "last_procedure_title": last_context.get("procedure_title") or runtime_context.get("last_procedure_title"),
            "last_filename": last_context.get("filename") or runtime_context.get("last_filename"),
            "last_document_id": last_context.get("document_id"),
            "current_session_doc_count": len(current_session_docs),
            "active_document_count": len(active_document_ids),
            "selected_document_count": len(selected_document_ids),
            "candidate_count": len(state.get("document_candidates") or []),
        }

    def _clean_payload(self, payload: dict[str, Any]) -> StructuredScopeResolution:
        action = str(payload.get("action") or payload.get("mode") or "resolve_document")
        scope = str(payload.get("scope") or RETRIEVAL_SCOPE_NEED_CLARIFICATION)
        if scope not in SCOPE_VALUES:
            scope = RETRIEVAL_SCOPE_NEED_CLARIFICATION
        mode = str(payload.get("resolution_mode") or payload.get("mode") or "need_clarification")
        if mode not in RESOLUTION_MODES:
            mode = "need_clarification"
        source_type = str(payload.get("source_type") or payload.get("source") or "none")
        hint = payload.get("hint")
        if source_type == SOURCE_TYPE_USER_UPLOAD:
            document_name_hint = payload.get("document_name_hint") or hint
            procedure_title_hint = payload.get("procedure_title_hint")
        elif source_type == SOURCE_TYPE_SYSTEM:
            procedure_title_hint = payload.get("procedure_title_hint") or hint
            document_name_hint = payload.get("document_name_hint")
        else:
            procedure_title_hint = payload.get("procedure_title_hint")
            document_name_hint = payload.get("document_name_hint")
        hints = payload.get("hints") if isinstance(payload.get("hints"), dict) else {}
        if hints:
            procedure_title_hint = hints.get("procedure_title") or procedure_title_hint
            time_hint = hints.get("time") or payload.get("time_hint") or payload.get("time")
        else:
            time_hint = payload.get("time_hint") or payload.get("time")
        return StructuredScopeResolution(
            action=action,
            scope=scope,
            resolution_mode=mode,
            should_reuse_last_filter=bool(payload.get("should_reuse_last_filter") or payload.get("reuse")),
            source_type=source_type,
            procedure_title_hint=procedure_title_hint,
            document_name_hint=document_name_hint,
            document_id_hint=payload.get("document_id_hint"),
            time_hint=time_hint,
            document_topic_hint=payload.get("document_topic_hint") or payload.get("topic"),
            branches=payload.get("branches") if isinstance(payload.get("branches"), list) else [],
            needs_clarification=bool(payload.get("needs_clarification") or payload.get("clarify")),
            clarification_question=payload.get("clarification_question"),
            confidence=float(payload.get("confidence") or 0.0),
            reason=str(payload.get("reason") or "Resolved by scope LLM."),
            used_llm=True,
        )

    def _apply_security_guards(self, resolution: StructuredScopeResolution, state: dict[str, Any]) -> StructuredScopeResolution:
        query = state.get("final_query") or state.get("original_query") or ""
        last_context = (state.get("runtime_context") or {}).get("last_resolved_context") or {}
        if resolution.should_reuse_last_filter:
            if not last_context.get("filter") or self._has_source_switch_signal(query):
                resolution.should_reuse_last_filter = False
                resolution.resolution_mode = "need_clarification"
                resolution.scope = RETRIEVAL_SCOPE_NEED_CLARIFICATION
                resolution.needs_clarification = True
                resolution.clarification_question = "Câu hỏi có dấu hiệu đổi nguồn tài liệu. Bạn muốn hỏi file upload hay tài liệu hệ thống?"
                resolution.reason = "Reuse last filter blocked by source-switch/security guard."
        if resolution.scope == RETRIEVAL_SCOPE_HYBRID_SYSTEM_AND_USER and not resolution.branches:
            resolution.branches = [
                {"branch_name": "system", "scope": RETRIEVAL_SCOPE_SYSTEM_DOCS},
                {"branch_name": "user_upload", "scope": RETRIEVAL_SCOPE_CURRENT_SESSION_UPLOADS},
            ]
        return resolution

    def _apply_administrative_guards(
        self, resolution: StructuredScopeResolution, state: dict[str, Any]
    ) -> StructuredScopeResolution:
        query = state.get("final_query") or state.get("original_query") or ""
        normalized_query = _normalize_text(query)
        if self._has_source_switch_signal(query) or not self._has_system_document_signal(query):
            return resolution
        if resolution.scope not in {RETRIEVAL_SCOPE_NEED_CLARIFICATION, RETRIEVAL_SCOPE_GENERAL_QUERY}:
            return resolution

        procedure = self._procedure_hint(query)
        if procedure or any(term in normalized_query for term in ("thu tuc", "quy trinh", "dang ky")):
            resolution.scope = RETRIEVAL_SCOPE_SYSTEM_PROCEDURE
            resolution.resolution_mode = "resolve_new_procedure"
            resolution.source_type = SOURCE_TYPE_SYSTEM
            resolution.procedure_title_hint = procedure or resolution.procedure_title_hint
            resolution.needs_clarification = False
            resolution.clarification_question = None
            resolution.confidence = max(resolution.confidence, 0.82)
            resolution.reason = "Strong administrative signal; routed to system procedure."
            return resolution

        resolution.scope = RETRIEVAL_SCOPE_SYSTEM_DOCS
        resolution.resolution_mode = "switch_scope"
        resolution.source_type = SOURCE_TYPE_SYSTEM
        resolution.needs_clarification = False
        resolution.clarification_question = None
        resolution.confidence = max(resolution.confidence, 0.8)
        resolution.reason = "Strong administrative signal; routed to system docs."
        return resolution

    def resolve(self, state: dict[str, Any]) -> StructuredScopeResolution:
        if self.chain is None:
            resolution = self._fallback(state, reason="Scope LLM unavailable; used deterministic fallback.")
            return self._apply_administrative_guards(resolution, state)
        try:
            raw = self.chain.invoke(
                {"state_json": json.dumps(self._build_llm_input(state), ensure_ascii=False, default=str)}
            ).strip()
            if raw.startswith("```"):
                raw = raw.strip("`")
                raw = raw.removeprefix("json").strip()
            resolution = self._clean_payload(json.loads(raw))
        except Exception:
            resolution = self._fallback(state, reason="Scope LLM failed; used deterministic fallback.")
        resolution = self._apply_security_guards(resolution, state)
        return self._apply_administrative_guards(resolution, state)
