from pathlib import Path

from app.core.constants import DOCUMENT_STATUS_FAILED, DOCUMENT_STATUS_PROCESSING, DOCUMENT_STATUS_READY
from app.models.chunk import ChunkModel
from app.models.document import DocumentModel
from app.rag.chunking.markdown_chunker import MarkdownChunker
from app.rag.converter.docling_converter import DoclingMarkdownConverter
from app.rag.embedding.bge_embedding import BGEEmbeddingService
from app.rag.vectorstore.chroma_store import ChromaVectorStore
from app.repositories.chunk_repository import ChunkRepository
from app.repositories.document_repository import DocumentRepository
from app.utils.id_utils import generate_id


class IngestionPipeline:
    def __init__(self) -> None:
        self.converter = DoclingMarkdownConverter()
        self.chunker = MarkdownChunker()
        self.embedding_service = BGEEmbeddingService()
        self.vector_store = ChromaVectorStore()
        self.document_repository = DocumentRepository()
        self.chunk_repository = ChunkRepository()

    async def run(self, document: DocumentModel) -> None:
        await self.document_repository.update_document_status(document.id, DOCUMENT_STATUS_PROCESSING)
        try:
            markdown_path = document.markdown_storage_path or str(Path(document.raw_storage_path).with_suffix(".md"))
            markdown_path = self.converter.convert_to_markdown(document.raw_storage_path, markdown_path)
            await self.document_repository.update_markdown_path(document.id, markdown_path)

            with open(markdown_path, "r", encoding="utf-8") as f:
                markdown_text = f.read()

            base_metadata = {
                "document_id": document.id,
                "source_type": document.source_type,
                "owner_user_id": document.owner_user_id,
                "session_id": document.uploaded_in_session_id,
                "filename": document.filename,
                "visibility": document.visibility,
            }
            chunks = self.chunker.chunk(markdown_text, base_metadata)
            chunk_docs: list[dict] = []
            for chunk in chunks:
                chunk_id = generate_id("chunk")
                metadata = {
                    **chunk,
                    "chunk_id": chunk_id,
                    "page_number": chunk.get("page_number"),
                    "section_title": chunk.get("section_title"),
                    "token_count": chunk.get("token_count", 0),
                }
                chunk_docs.append(
                    {
                        "id": chunk_id,
                        **chunk,
                        "metadata": metadata,
                    }
                )

            embeddings = self.embedding_service.embed_texts([chunk["content"] for chunk in chunk_docs]) if chunk_docs else []
            await self.chunk_repository.insert_chunks(chunk_docs)
            self.vector_store.add_chunks(chunk_docs, embeddings)
            await self.document_repository.update_document_status(document.id, DOCUMENT_STATUS_READY)
            document.markdown_storage_path = markdown_path
            document.status = DOCUMENT_STATUS_READY
        except Exception:
            await self.document_repository.update_document_status(document.id, DOCUMENT_STATUS_FAILED)
            raise
