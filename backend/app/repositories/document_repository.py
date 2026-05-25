from datetime import datetime, time, timedelta
from typing import Any, Optional

from app.db.mongodb import get_database
from app.models.document import DocumentModel


class DocumentRepository:
    collection_name = "documents"

    def _collection(self):
        return get_database()[self.collection_name]

    async def create_document(self, document: DocumentModel) -> str:
        payload = document.model_dump(by_alias=True)
        await self._collection().insert_one(payload)
        return document.id

    async def get_document_by_id(self, document_id: str) -> Optional[dict[str, Any]]:
        return await self._collection().find_one({"_id": document_id})

    async def list_documents(self, owner_user_id: str | None = None) -> list[dict[str, Any]]:
        query: dict[str, Any] = {}
        if owner_user_id is not None:
            query["owner_user_id"] = owner_user_id
        cursor = self._collection().find(query)
        return [doc async for doc in cursor]

    async def list_user_documents(self, user_id: str) -> list[dict[str, Any]]:
        return await self.list_documents(owner_user_id=user_id)

    async def list_user_documents_by_session(self, user_id: str, session_id: str) -> list[dict[str, Any]]:
        cursor = self._collection().find(
            {
                "owner_user_id": user_id,
                "uploaded_in_session_id": session_id,
                "status": {"$ne": "deleted"},
            }
        ).sort("created_at", -1)
        return [doc async for doc in cursor]

    def _time_range_for_hint(self, time_hint: str) -> tuple[datetime, datetime] | None:
        normalized = (time_hint or "").strip().lower()
        now = datetime.utcnow()
        today = now.date()

        if normalized in {"yesterday", "hom qua", "hom qua nay"}:
            start_date = today - timedelta(days=1)
            end_date = today
            return datetime.combine(start_date, time.min), datetime.combine(end_date, time.min)

        if normalized in {"two_days_ago", "hom kia"}:
            start_date = today - timedelta(days=2)
            end_date = today - timedelta(days=1)
            return datetime.combine(start_date, time.min), datetime.combine(end_date, time.min)

        if normalized in {"last_week", "tuan truoc"}:
            start_date = today - timedelta(days=7)
            end_date = today
            return datetime.combine(start_date, time.min), datetime.combine(end_date, time.min)

        if normalized in {"next_week", "tuan sau"}:
            start_date = today
            end_date = today + timedelta(days=7)
            return datetime.combine(start_date, time.min), datetime.combine(end_date, time.min)

        date_formats = ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d/%m/%y", "%d/%m")
        for fmt in date_formats:
            try:
                parsed = datetime.strptime(normalized, fmt)
            except ValueError:
                continue
            if fmt == "%d/%m":
                parsed = parsed.replace(year=today.year)
            start = datetime.combine(parsed.date(), time.min)
            end = start + timedelta(days=1)
            return start, end

        return None

    async def list_user_documents_by_time_hint(
        self,
        user_id: str,
        time_hint: str,
        filename: str | None = None,
    ) -> list[dict[str, Any]]:
        window = self._time_range_for_hint(time_hint)
        if window is None:
            return []

        start, end = window
        query: dict[str, Any] = {
            "owner_user_id": user_id,
            "status": {"$ne": "deleted"},
            "created_at": {"$gte": start, "$lt": end},
        }
        if filename:
            query["filename"] = filename

        cursor = self._collection().find(query).sort("created_at", -1)
        return [doc async for doc in cursor]

    async def list_user_ready_documents(self, user_id: str) -> list[dict[str, Any]]:
        cursor = self._collection().find(
            {
                "owner_user_id": user_id,
                "status": {"$ne": "deleted"},
            }
        ).sort("created_at", -1)
        return [doc async for doc in cursor]

    async def list_system_ready_documents(self) -> list[dict[str, Any]]:
        cursor = self._collection().find(
            {
                "source_type": "system",
                "visibility": "global",
                "status": {"$ne": "deleted"},
            }
        ).sort("created_at", -1)
        return [doc async for doc in cursor]

    async def find_user_documents_by_filename(self, user_id: str, filename: str) -> list[dict[str, Any]]:
        cursor = self._collection().find(
            {
                "owner_user_id": user_id,
                "filename": filename,
                "status": {"$ne": "deleted"},
            }
        ).sort("created_at", -1)
        return [doc async for doc in cursor]

    async def find_system_documents_by_procedure_title(self, procedure_title: str) -> list[dict[str, Any]]:
        cursor = self._collection().find(
            {
                "source_type": "system",
                "visibility": "global",
                "procedure_title": procedure_title,
                "status": {"$ne": "deleted"},
            }
        ).sort("created_at", -1)
        return [doc async for doc in cursor]

    async def update_document_status(self, document_id: str, status: str) -> None:
        await self._collection().update_one(
            {"_id": document_id},
            {"$set": {"status": status, "updated_at": datetime.utcnow()}},
        )

    async def update_markdown_path(self, document_id: str, markdown_path: str) -> None:
        await self._collection().update_one(
            {"_id": document_id},
            {"$set": {"markdown_storage_path": markdown_path, "updated_at": datetime.utcnow()}},
        )

    async def update_document_fields(self, document_id: str, **fields: Any) -> None:
        payload = dict(fields)
        payload["updated_at"] = datetime.utcnow()
        await self._collection().update_one({"_id": document_id}, {"$set": payload})

    async def soft_delete_document(self, document_id: str) -> None:
        await self._collection().update_one(
            {"_id": document_id},
            {"$set": {"status": "deleted", "updated_at": datetime.utcnow()}},
        )
