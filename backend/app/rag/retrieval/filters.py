from app.core.constants import (
    RETRIEVAL_SCOPE_ALL_USER_UPLOADS,
    RETRIEVAL_SCOPE_CURRENT_UPLOAD,
    RETRIEVAL_SCOPE_MIXED,
    RETRIEVAL_SCOPE_SYSTEM_DOCS,
    SOURCE_TYPE_SYSTEM,
    SOURCE_TYPE_USER_UPLOAD,
    VISIBILITY_GLOBAL,
)


def build_retrieval_filter(
    scope: str,
    user_id: str,
    session_id: str | None = None,
    selected_document_ids: list[str] | None = None,
) -> dict:
    selected_document_ids = selected_document_ids or []

    if scope == RETRIEVAL_SCOPE_CURRENT_UPLOAD:
        base = {
            "source_type": SOURCE_TYPE_USER_UPLOAD,
            "owner_user_id": user_id,
        }
        if session_id:
            base["session_id"] = session_id
    elif scope == RETRIEVAL_SCOPE_ALL_USER_UPLOADS:
        base = {"source_type": SOURCE_TYPE_USER_UPLOAD, "owner_user_id": user_id}
    elif scope == RETRIEVAL_SCOPE_SYSTEM_DOCS:
        base = {"source_type": SOURCE_TYPE_SYSTEM, "visibility": VISIBILITY_GLOBAL}
    else:
        base = {
            "$or": [
                {"source_type": SOURCE_TYPE_SYSTEM, "visibility": VISIBILITY_GLOBAL},
                {"source_type": SOURCE_TYPE_USER_UPLOAD, "owner_user_id": user_id},
            ]
        }

    if selected_document_ids:
        selection_filter = {"document_id": {"$in": selected_document_ids}}
        if "$or" in base:
            return {"$and": [base, selection_filter]}
        return {"$and": [base, selection_filter]}

    return base
