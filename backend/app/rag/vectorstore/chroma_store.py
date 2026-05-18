from typing import Any

from app.db.chromadb import get_chroma_collection


class ChromaVectorStore:
    def __init__(self) -> None:
        self.collection = get_chroma_collection()

    def add_chunks(self, chunks: list[dict[str, Any]], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        ids = [chunk["id"] for chunk in chunks]
        documents = [chunk["content"] for chunk in chunks]
        metadatas = []
        for chunk in chunks:
            metadata = chunk["metadata"]
            metadatas.append({key: value for key, value in metadata.items() if value is not None and key != "content"})
        self.collection.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    def search(self, query_embedding: list[float], where_filter: dict[str, Any] | None, top_k: int = 5) -> list[dict[str, Any]]:
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )
        items: list[dict[str, Any]] = []
        for idx, chunk_id in enumerate(result["ids"][0] if result.get("ids") else []):
            items.append(
                {
                    "id": chunk_id,
                    "content": result["documents"][0][idx],
                    "metadata": result["metadatas"][0][idx],
                    "distance": result["distances"][0][idx] if result.get("distances") else None,
                }
            )
        return items

    def delete_by_document_id(self, document_id: str) -> None:
        self.collection.delete(where={"document_id": document_id})
