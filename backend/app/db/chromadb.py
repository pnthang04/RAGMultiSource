from functools import lru_cache
from typing import Any

import chromadb

from app.core.config import settings


@lru_cache
def get_chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)


def get_chroma_collection() -> Any:
    client = get_chroma_client()
    return client.get_or_create_collection(name=settings.CHROMA_COLLECTION_NAME)
