from __future__ import annotations

from app.db.mongodb import get_database
from app.db.mongo_retry import retry_mongo_write
from app.models.retrieval_log import RetrievalLogModel


class RetrievalLogRepository:
    collection_name = "retrieval_logs"

    def _collection(self):
        return get_database()[self.collection_name]

    async def create_log(self, log: RetrievalLogModel) -> str:
        await retry_mongo_write(lambda: self._collection().insert_one(log.model_dump(by_alias=True)))
        return log.id
