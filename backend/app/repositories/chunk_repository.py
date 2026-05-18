from typing import Any

from app.db.mongodb import get_database


class ChunkRepository:
    collection_name = "chunks"

    def _collection(self):
        return get_database()[self.collection_name]

    async def insert_chunks(self, chunks: list[dict[str, Any]]) -> None:
        if not chunks:
            return
        await self._collection().insert_many(chunks)

    async def get_chunks_by_document_id(self, document_id: str) -> list[dict[str, Any]]:
        cursor = self._collection().find({"document_id": document_id})
        return [chunk async for chunk in cursor]

    async def delete_chunks_by_document_id(self, document_id: str) -> None:
        await self._collection().delete_many({"document_id": document_id})
