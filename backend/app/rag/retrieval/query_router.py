from app.core.constants import (
    RETRIEVAL_SCOPE_ALL_USER_UPLOADS,
    RETRIEVAL_SCOPE_CURRENT_UPLOAD,
    RETRIEVAL_SCOPE_MIXED,
    RETRIEVAL_SCOPE_SYSTEM_DOCS,
)


class QueryRouter:
    def route(self, question: str) -> str:
        text = question.lower()
        if any(token in text for token in ["file này", "tài liệu này", "vừa upload"]):
            return RETRIEVAL_SCOPE_CURRENT_UPLOAD
        if any(token in text for token in ["hôm trước", "đã upload", "file cũ"]):
            return RETRIEVAL_SCOPE_ALL_USER_UPLOADS
        if any(token in text for token in ["hệ thống", "quy định", "chính sách", "hướng dẫn"]):
            return RETRIEVAL_SCOPE_SYSTEM_DOCS
        if any(token in text for token in ["so sánh", "đối chiếu", "có đáp ứng"]):
            return RETRIEVAL_SCOPE_MIXED
        return RETRIEVAL_SCOPE_MIXED
