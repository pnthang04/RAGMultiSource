from openai import OpenAI

from app.core.config import settings
from app.rag.generation.prompts import RAG_SYSTEM_PROMPT


class OpenAILLMService:
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY or None) if settings.OPENAI_API_KEY else None

    def generate_answer(self, question: str, contexts: list[dict]) -> str:
        context_text = "\n\n".join(
            [
                f"[{idx + 1}] {item.get('content', '')}\nMETADATA: {item.get('metadata', {})}"
                for idx, item in enumerate(contexts)
            ]
        )
        if self.client is None:
            if not contexts:
                return "Không tìm thấy thông tin trong tài liệu."
            return f"[TODO] OpenAI API key is not configured. Context available but generation is disabled.\n\n{context_text[:1200]}"
        response = self.client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": RAG_SYSTEM_PROMPT},
                {"role": "user", "content": f"Question: {question}\n\nContext:\n{context_text}"},
            ],
        )
        return response.choices[0].message.content or ""
