from app.rag.embedding.bge_embedding import BGEEmbeddingService
from app.rag.vectorstore.chroma_store import ChromaVectorStore


class Retriever:
    def __init__(self) -> None:
        self.embedding_service = BGEEmbeddingService()
        self.vector_store = ChromaVectorStore()

    def retrieve(self, question: str, where_filter: dict | None, top_k: int = 5) -> list[dict]:
        query_embedding = self.embedding_service.embed_text(question)
        return self.vector_store.search(query_embedding=query_embedding, where_filter=where_filter, top_k=top_k)
