from __future__ import annotations

import re
from typing import Any

from app.core.constants import SOURCE_TYPE_SYSTEM, SOURCE_TYPE_USER_UPLOAD


class SourceFormatter:
    def source_prefix(self, sources: list[dict[str, Any]]) -> str:
        source_types = {source.get("source_type") for source in sources if source.get("source_type")}
        if source_types == {SOURCE_TYPE_SYSTEM}:
            return "Theo tài liệu hệ thống:"
        if source_types == {SOURCE_TYPE_USER_UPLOAD}:
            return "Theo tài liệu bạn upload:"
        if SOURCE_TYPE_SYSTEM in source_types and SOURCE_TYPE_USER_UPLOAD in source_types:
            return "Theo các nguồn được tìm thấy từ tài liệu hệ thống và tài liệu bạn upload:"
        return ""

    def short_source_label(self, sources: list[dict[str, Any]]) -> str:
        labels: list[str] = []
        seen: set[str] = set()
        for source in sources:
            label = source.get("procedure_title") or source.get("filename") or source.get("document_id")
            if label and label not in seen:
                seen.add(label)
                labels.append(str(label))
            if len(labels) >= 2:
                break
        if not labels:
            return ""
        return "Nguồn: " + "; ".join(labels)

    def strip_llm_source_suffix(self, answer: str) -> str:
        # The formatter owns source display. Remove verbose citations if the LLM
        # still emits them despite the prompt.
        cleaned = re.sub(r"\s*\(?Nguồn:\s*[^)\n]+(?:\)|$)", "", answer, flags=re.IGNORECASE).strip()
        return cleaned

    def format_answer(self, answer: str, sources: list[dict[str, Any]]) -> str:
        answer = self.strip_llm_source_suffix(answer)
        prefix = self.source_prefix(sources)
        source_label = self.short_source_label(sources)
        parts: list[str] = []
        if prefix and not answer.strip().startswith(prefix):
            parts.append(prefix)
        parts.append(answer.strip())
        if source_label and source_label not in answer:
            parts.append(source_label)
        return "\n".join(part for part in parts if part)
