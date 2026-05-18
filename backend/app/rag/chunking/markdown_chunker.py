from app.rag.chunking.chunk_utils import extract_heading
from app.utils.text_utils import count_tokens_rough, normalize_whitespace


class MarkdownChunker:
    def chunk(self, markdown_text: str, base_metadata: dict) -> list[dict]:
        lines = markdown_text.splitlines()
        chunks: list[dict] = []
        buffer: list[str] = []
        current_heading = None

        def flush() -> None:
            nonlocal buffer
            if not buffer:
                return
            content = normalize_whitespace("\n".join(buffer))
            if content:
                chunk_index = len(chunks)
                chunks.append(
                    {
                        "content": content,
                        **base_metadata,
                        "chunk_index": chunk_index,
                        "section_title": current_heading,
                        "token_count": count_tokens_rough(content),
                    }
                )
            buffer = []

        for line in lines:
            heading = extract_heading(line)
            if heading:
                flush()
                current_heading = heading
                buffer.append(line)
            else:
                buffer.append(line)

            if len(" ".join(buffer)) > 1200:
                flush()

        flush()

        if chunks:
            return chunks

        text = normalize_whitespace(markdown_text)
        if not text:
            return []

        step = 800
        for start in range(0, len(text), step):
            slice_text = text[start : start + step]
            chunks.append(
                {
                    "content": slice_text,
                    **base_metadata,
                    "chunk_index": len(chunks),
                    "section_title": None,
                    "token_count": count_tokens_rough(slice_text),
                }
            )
        return chunks
