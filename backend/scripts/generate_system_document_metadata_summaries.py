from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient
from openai import OpenAI


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


DEFAULT_MODEL = "google/gemini-2.5-flash-lite"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


SYSTEM_PROMPT = """Bạn là chuyên gia tóm tắt nội dung văn bản thủ tục hành chính cho hệ thống RAG.

Nhiệm vụ: đọc tài liệu markdown và viết một summary ngắn, tập trung vào nội dung cốt lõi của chính thủ tục, để lưu trực tiếp vào field summary của document.

Yêu cầu nội dung:
- Viết bằng tiếng Việt tự nhiên, rõ nghĩa, 3-4 câu.
- Câu 1 nêu thủ tục này dùng để làm gì và áp dụng cho ai/đối tượng nào nếu tài liệu có.
- Các câu tiếp theo tóm tắt thông tin thực chất người dùng hay cần tra cứu: hồ sơ/thành phần chính, điều kiện quan trọng, cách nộp, thời hạn giải quyết, cơ quan thực hiện, kết quả nhận được.
- Ưu tiên thông tin phân biệt tài liệu này với tài liệu khác; tránh viết chung chung kiểu "quy định trình tự, hồ sơ, thời hạn".
- Không tập trung kể lại quy trình nội bộ nếu không cần thiết.
- Không bịa thông tin ngoài tài liệu, không trích dẫn dài, không dùng markdown bullet.
- Trả về JSON hợp lệ, không giải thích ngoài JSON.

Schema bắt buộc:
{
  "summary": "đoạn tóm tắt 3-4 câu tập trung vào nội dung chính của thủ tục"
}
"""


def _load_backend_env() -> None:
    env_path = BACKEND_ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="cp1258", errors="replace")


def _extract_json_object(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


def _resolve_markdown_path(document: dict[str, Any]) -> Path | None:
    raw_path = document.get("markdown_storage_path")
    if raw_path:
        path = Path(str(raw_path))
        if not path.is_absolute():
            path = REPO_ROOT / path
        if path.exists():
            return path

    document_id = str(document.get("_id") or "")
    fallback = BACKEND_ROOT / "storage" / "markdown" / "system" / "system" / document_id / "document.md"
    if fallback.exists():
        return fallback
    return None


def _build_user_prompt(document: dict[str, Any], markdown_text: str, max_doc_chars: int) -> str:
    doc_text = markdown_text.strip()
    if len(doc_text) > max_doc_chars:
        doc_text = doc_text[:max_doc_chars].rstrip() + "\n...[document truncated]"

    return (
        "Hãy tạo summary cho system document sau.\n\n"
        f"document_id: {document.get('_id')}\n"
        f"title: {document.get('title') or ''}\n"
        f"filename: {document.get('filename') or ''}\n"
        f"procedure_title: {document.get('procedure_title') or ''}\n"
        f"source_type: {document.get('source_type') or ''}\n\n"
        "TOÀN BỘ FILE MARKDOWN:\n"
        "```markdown\n"
        f"{doc_text}\n"
        "```"
    )


def _build_openrouter_client() -> OpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY is missing. Add it to backend/.env or the environment.")

    default_headers = {}
    if os.getenv("OPENROUTER_SITE_URL"):
        default_headers["HTTP-Referer"] = os.getenv("OPENROUTER_SITE_URL", "")
    if os.getenv("OPENROUTER_APP_NAME"):
        default_headers["X-Title"] = os.getenv("OPENROUTER_APP_NAME", "")

    return OpenAI(
        api_key=api_key,
        base_url=os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL),
        default_headers=default_headers or None,
    )


def generate_summary(
    *,
    client: OpenAI,
    model: str,
    document: dict[str, Any],
    markdown_text: str,
    max_doc_chars: int,
    max_tokens: int,
    temperature: float,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(document, markdown_text, max_doc_chars)},
            ],
        )
        content = response.choices[0].message.content or "{}"
        try:
            payload = _extract_json_object(content)
            break
        except json.JSONDecodeError as exc:
            last_error = exc
            if attempt == 3:
                raise RuntimeError(f"LLM returned invalid JSON after 3 attempts: {content[:500]}") from last_error
    summary = str(payload.get("summary") or "").strip()
    if not summary:
        raise RuntimeError("LLM response did not include a non-empty summary.")
    return {"summary": summary}


async def list_system_documents(
    db: Any,
    *,
    document_id: str | None,
    limit: int | None,
    overwrite: bool,
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {
        "source_type": "system",
        "visibility": "global",
        "status": {"$ne": "deleted"},
    }
    if document_id:
        query["_id"] = document_id
    if not overwrite:
        query["summary"] = {"$exists": False}

    cursor = db.documents.find(query).sort("created_at", 1)
    if limit:
        cursor = cursor.limit(limit)
    return await cursor.to_list(None)


async def update_document_summary(
    db: Any,
    *,
    document_id: str,
    summary_payload: dict[str, Any],
    model: str,
    dry_run: bool,
) -> None:
    generated_at = datetime.now(timezone.utc)
    update_payload = {
        "summary": summary_payload["summary"],
        "updated_at": generated_at.replace(tzinfo=None),
    }
    if dry_run:
        print(json.dumps({"document_id": document_id, **summary_payload}, ensure_ascii=False, indent=2))
        return
    await db.documents.update_one({"_id": document_id}, {"$set": update_payload})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate and store metadata summaries for system documents using OpenRouter."
    )
    parser.add_argument("--document-id", default=None, help="Only process one system document.")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of documents to process.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--max-doc-chars", type=int, default=45000)
    parser.add_argument("--max-tokens", type=int, default=700)
    parser.add_argument("--overwrite", action="store_true", help="Regenerate summaries even when summary already exists.")
    parser.add_argument("--dry-run", action="store_true", help="Print generated summaries without updating MongoDB.")
    return parser.parse_args()


async def main_async() -> None:
    _load_backend_env()
    args = parse_args()

    mongo_uri = os.getenv("MONGODB_URI", "mongodb://mongodb:27017")
    db_name = os.getenv("MONGODB_DB_NAME", "rag_chatbot")
    mongo_client = AsyncIOMotorClient(mongo_uri)
    openrouter_client = _build_openrouter_client()

    try:
        db = mongo_client[db_name]
        documents = await list_system_documents(
            db,
            document_id=args.document_id,
            limit=args.limit,
            overwrite=args.overwrite,
        )
        print(f"documents_to_process={len(documents)}")

        for index, document in enumerate(documents, start=1):
            document_id = str(document.get("_id"))
            markdown_path = _resolve_markdown_path(document)
            if markdown_path is None:
                print(f"[{index}/{len(documents)}] skip {document_id}: markdown not found")
                continue

            print(f"[{index}/{len(documents)}] summarizing {document_id}")
            markdown_text = _read_text(markdown_path)
            summary_payload = generate_summary(
                client=openrouter_client,
                model=args.model,
                document=document,
                markdown_text=markdown_text,
                max_doc_chars=args.max_doc_chars,
                max_tokens=args.max_tokens,
                temperature=args.temperature,
            )
            await update_document_summary(
                db,
                document_id=document_id,
                summary_payload=summary_payload,
                model=args.model,
                dry_run=args.dry_run,
            )

        print("done")
    finally:
        mongo_client.close()


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
