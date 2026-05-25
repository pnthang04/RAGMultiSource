from __future__ import annotations

import argparse
import asyncio
from typing import Any

from app.db.mongodb import get_database, get_mongo_client
from app.rag.embedding.bge_embedding import BGEEmbeddingService
from app.rag.vectorstore.chroma_store import ChromaVectorStore


def _chunk_id(chunk: dict[str, Any]) -> str:
    metadata = chunk.get("metadata") or {}
    return str(chunk.get("id") or metadata.get("chunk_id") or chunk.get("_id"))


def _chunk_content(chunk: dict[str, Any]) -> str:
    return (chunk.get("content") or chunk.get("text") or "").strip()


def _chunk_metadata(chunk: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(chunk.get("metadata") or {})
    for key in (
        "document_id",
        "source_type",
        "owner_user_id",
        "session_id",
        "filename",
        "procedure_title",
        "visibility",
        "uploaded_at",
        "page_number",
        "section_title",
        "chunk_index",
    ):
        if metadata.get(key) is None and chunk.get(key) is not None:
            metadata[key] = chunk[key]
    metadata.setdefault("chunk_id", _chunk_id(chunk))
    return metadata


async def reindex(source_type: str | None, document_id: str | None, batch_size: int, replace: bool) -> None:
    db = get_database()
    vector_store = ChromaVectorStore()
    embedding_service = BGEEmbeddingService()

    query: dict[str, Any] = {}
    if source_type:
        query["source_type"] = source_type
    if document_id:
        query["document_id"] = document_id

    chunks = await db.chunks.find(query).to_list(None)
    prepared = [
        {
            "id": _chunk_id(chunk),
            "content": _chunk_content(chunk),
            "metadata": _chunk_metadata(chunk),
        }
        for chunk in chunks
        if _chunk_content(chunk)
    ]

    if replace:
        document_ids = sorted({item["metadata"].get("document_id") for item in prepared if item["metadata"].get("document_id")})
        for doc_id in document_ids:
            vector_store.delete_by_document_id(str(doc_id))

    inserted = 0
    for start in range(0, len(prepared), batch_size):
        batch = prepared[start : start + batch_size]
        embeddings = embedding_service.embed_texts([item["content"] for item in batch])
        vector_store.add_chunks(batch, embeddings)
        inserted += len(batch)
        print(f"indexed {inserted}/{len(prepared)} chunks")

    print(f"done: indexed={inserted}, source_type={source_type or 'all'}, document_id={document_id or 'all'}")
    get_mongo_client().close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Reindex Mongo chunks into Chroma.")
    parser.add_argument("--source-type", default="system", choices=["system", "user_upload", "all"])
    parser.add_argument("--document-id", default=None)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()

    source_type = None if args.source_type == "all" else args.source_type
    asyncio.run(reindex(source_type, args.document_id, args.batch_size, args.replace))


if __name__ == "__main__":
    main()
