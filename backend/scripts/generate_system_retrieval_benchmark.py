from __future__ import annotations

import argparse
import asyncio
from datetime import date, datetime
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient
from openai import OpenAI


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.rag.chunking.markdown_chunker import MarkdownChunker  # noqa: E402


DEFAULT_INPUT_DIR = BACKEND_ROOT / "storage" / "markdown" / "system" / "system"
DEFAULT_OUTPUT = BACKEND_ROOT / "tests" / "fixtures" / "system_retrieval_benchmark.jsonl"
DEFAULT_MODEL = "gpt-4o-mini"


SYSTEM_PROMPT = """Bạn là chuyên gia tạo benchmark đánh giá hệ thống RAG cho văn bản thủ tục hành chính Việt Nam.

Nhiệm vụ: đọc toàn bộ tài liệu markdown được cung cấp và tạo câu hỏi truy xuất tài liệu/chunk.

Yêu cầu chất lượng:
- Câu hỏi phải giống câu người dùng thật hỏi hệ thống RAG về thủ tục hành chính.
- Ưu tiên câu hỏi về: tên thủ tục, mã thủ tục, thời hạn giải quyết, cách thức nộp, thành phần hồ sơ, đối tượng thực hiện, cơ quan thực hiện, kết quả, căn cứ pháp lý, phí/lệ phí, yêu cầu/điều kiện.
- Câu hỏi phải đủ đặc trưng để truy xuất đúng tài liệu nguồn, không quá chung chung.
- Không hỏi thông tin không có trong tài liệu.
- Mỗi câu hỏi phải có ít nhất một chunk bằng chứng từ danh sách chunk được cung cấp.
- evidence_answer phải là câu trả lời ngắn được suy ra trực tiếp từ tài liệu.
- Trả về JSON hợp lệ, không markdown, không giải thích.

Schema bắt buộc:
{
  "items": [
    {
      "query": "câu hỏi tiếng Việt",
      "expected_answer": "câu trả lời ngắn",
      "evidence_chunks": [
        {
          "chunk_index": 0,
          "section_title": "tên mục hoặc null",
          "evidence_text": "trích đoạn ngắn nguyên văn hoặc gần nguyên văn trong chunk"
        }
      ]
    }
  ]
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
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="cp1258", errors="replace")


def _json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _extract_procedure_title(markdown_text: str) -> str | None:
    patterns = [
        r"^Tên thủ tục:\s*(.+)$",
        r"^TÃªn thá»§ tá»¥c:\s*(.+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, markdown_text, flags=re.MULTILINE | re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _extract_json_object(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(text[start : end + 1])


def _compact_chunk(chunk: dict[str, Any], max_chars: int) -> dict[str, Any]:
    content = str(chunk.get("content") or "").strip()
    if len(content) > max_chars:
        content = content[:max_chars].rstrip() + "\n...[truncated]"
    metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
    chunk_id = chunk.get("id") or chunk.get("_id") or metadata.get("chunk_id")
    return {
        "chunk_id": str(chunk_id) if chunk_id is not None else None,
        "chunk_index": chunk.get("chunk_index"),
        "section_title": chunk.get("section_title"),
        "heading_path": chunk.get("heading_path") or [],
        "content": content,
    }


def _build_user_prompt(
    *,
    document_id: str,
    procedure_title: str | None,
    markdown_text: str,
    chunks: list[dict[str, Any]],
    queries_per_doc: int,
    max_doc_chars: int,
    max_chunk_chars: int,
) -> str:
    compact_chunks = [_compact_chunk(chunk, max_chunk_chars) for chunk in chunks]
    doc_text = markdown_text.strip()
    if len(doc_text) > max_doc_chars:
        doc_text = doc_text[:max_doc_chars].rstrip() + "\n...[document truncated]"

    return (
        f"Hãy tạo đúng {queries_per_doc} câu hỏi benchmark cho tài liệu sau.\n\n"
        f"document_id: {document_id}\n"
        f"source_type: system\n"
        f"metadata_type: systemdoc\n"
        f"procedure_title: {procedure_title or ''}\n\n"
        "IMPORTANT: evidence_chunks must include the exact chunk_id from DANH SACH CHUNK UNG VIEN. Do not invent chunk_id.\n\n"
        "DANH SÁCH CHUNK ỨNG VIÊN:\n"
        f"{json.dumps(compact_chunks, ensure_ascii=False, indent=2)}\n\n"
        "TOÀN BỘ FILE MARKDOWN:\n"
        "```markdown\n"
        f"{doc_text}\n"
        "```"
    )


def _normalize_evidence_chunks(raw_chunks: Any, available_chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(raw_chunks, list):
        return []

    by_index = {chunk.get("chunk_index"): chunk for chunk in available_chunks}
    by_id: dict[str, dict[str, Any]] = {}
    for chunk in available_chunks:
        metadata = chunk.get("metadata") if isinstance(chunk.get("metadata"), dict) else {}
        chunk_id = chunk.get("id") or chunk.get("_id") or metadata.get("chunk_id")
        if chunk_id is not None:
            by_id[str(chunk_id)] = chunk

    normalized: list[dict[str, Any]] = []
    for raw in raw_chunks:
        if not isinstance(raw, dict):
            continue
        chunk_id = raw.get("chunk_id")
        source_chunk = by_id.get(str(chunk_id)) if chunk_id is not None else None
        if source_chunk is None:
            source_chunk = by_index.get(raw.get("chunk_index"))
        metadata = source_chunk.get("metadata") if isinstance(source_chunk, dict) and isinstance(source_chunk.get("metadata"), dict) else {}
        resolved_chunk_id = None
        if isinstance(source_chunk, dict):
            resolved_chunk_id = source_chunk.get("id") or source_chunk.get("_id") or metadata.get("chunk_id")
        normalized.append(
            {
                "chunk_id": str(resolved_chunk_id or chunk_id or ""),
                "document_id": metadata.get("document_id") or (source_chunk or {}).get("document_id"),
                "source_type": metadata.get("source_type") or (source_chunk or {}).get("source_type") or "system",
                "chunk_index": raw.get("chunk_index") if raw.get("chunk_index") is not None else (source_chunk or {}).get("chunk_index"),
                "section_title": raw.get("section_title") if raw.get("section_title") is not None else (source_chunk or {}).get("section_title"),
                "evidence_text": str(raw.get("evidence_text") or "").strip(),
            }
        )
    return normalized


def _normalize_items(
    *,
    raw_items: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    document_id: str,
    filename: str,
    procedure_title: str | None,
    markdown_path: Path,
    max_items: int,
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in raw_items[:max_items]:
        query = str(item.get("query") or "").strip()
        if not query:
            continue
        evidence_chunks = _normalize_evidence_chunks(item.get("evidence_chunks"), chunks)
        normalized.append(
            {
                "query": query,
                "expected_answer": str(item.get("expected_answer") or "").strip(),
                "expected_document": {
                    "document_id": document_id,
                    "source_type": "system",
                    "metadata_type": "systemdoc",
                    "filename": filename,
                    "procedure_title": procedure_title,
                    "markdown_path": str(markdown_path.relative_to(REPO_ROOT)),
                },
                "expected_chunk_ids": [chunk["chunk_id"] for chunk in evidence_chunks if chunk.get("chunk_id")],
                "evidence_chunks": evidence_chunks,
                "metadata": {
                    "benchmark_type": "retrieval",
                    "source_type": "system",
                    "metadata_type": "systemdoc",
                    "generator": "openai",
                },
            }
        )
    return normalized


async def fetch_stored_chunks(document_id: str) -> list[dict[str, Any]]:
    mongo_uri = os.getenv("MONGODB_URI", "mongodb://mongodb:27017")
    db_name = os.getenv("MONGODB_DB_NAME", "rag_chatbot")
    client = AsyncIOMotorClient(mongo_uri)
    try:
        cursor = (
            client[db_name]["chunks"]
            .find({"document_id": document_id, "source_type": "system"})
            .sort("chunk_index", 1)
        )
        chunks = await cursor.to_list(None)
    finally:
        client.close()
    return [_json_safe(chunk) for chunk in chunks]


def build_markdown_chunks(document_id: str, markdown_path: Path, markdown_text: str, procedure_title: str | None) -> list[dict[str, Any]]:
    chunker = MarkdownChunker()
    return chunker.chunk(
        markdown_text,
        {
            "document_id": document_id,
            "source_type": "system",
            "visibility": "global",
            "filename": markdown_path.name,
            "procedure_title": procedure_title,
        },
    )


def generate_for_document(
    *,
    client: OpenAI,
    model: str,
    document_path: Path,
    chunks: list[dict[str, Any]],
    queries_per_doc: int,
    temperature: float,
    max_doc_chars: int,
    max_chunk_chars: int,
) -> list[dict[str, Any]]:
    markdown_path = document_path / "document.md"
    markdown_text = _read_text(markdown_path)
    document_id = document_path.name
    procedure_title = _extract_procedure_title(markdown_text)

    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _build_user_prompt(
                    document_id=document_id,
                    procedure_title=procedure_title,
                    markdown_text=markdown_text,
                    chunks=chunks,
                    queries_per_doc=queries_per_doc,
                    max_doc_chars=max_doc_chars,
                    max_chunk_chars=max_chunk_chars,
                ),
            },
        ],
    )
    content = response.choices[0].message.content or "{}"
    payload = _extract_json_object(content)
    raw_items = payload.get("items") or []
    if not isinstance(raw_items, list):
        raw_items = []
    return _normalize_items(
        raw_items=raw_items,
        chunks=chunks,
        document_id=document_id,
        filename=markdown_path.name,
        procedure_title=procedure_title,
        markdown_path=markdown_path,
        max_items=queries_per_doc,
    )


def iter_document_dirs(input_dir: Path, limit: int) -> list[Path]:
    docs = sorted(path for path in input_dir.iterdir() if path.is_dir() and (path / "document.md").exists())
    return docs[:limit]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a system-document retrieval benchmark from markdown files using OpenAI."
    )
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--limit", type=int, default=10, help="Number of system documents to process.")
    parser.add_argument("--queries-per-doc", type=int, default=2, choices=[1, 2])
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", DEFAULT_MODEL))
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-doc-chars", type=int, default=30000)
    parser.add_argument("--max-chunk-chars", type=int, default=1800)
    parser.add_argument(
        "--chunk-source",
        choices=["stored", "markdown"],
        default="stored",
        help="Use chunks stored in MongoDB, or regenerate chunks from markdown.",
    )
    parser.add_argument(
        "--allow-markdown-fallback",
        action="store_true",
        help="When --chunk-source=stored has no Mongo chunks, regenerate chunks from markdown.",
    )
    return parser.parse_args()


async def main_async() -> None:
    _load_backend_env()
    args = parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("OPENAI_API_KEY is missing. Add it to backend/.env or the environment.")

    input_dir = args.input_dir.resolve()
    output = args.output.resolve()
    if not input_dir.exists():
        raise SystemExit(f"Input directory does not exist: {input_dir}")

    client = OpenAI(api_key=api_key)
    rows: list[dict[str, Any]] = []
    document_dirs = iter_document_dirs(input_dir, args.limit)
    for index, document_dir in enumerate(document_dirs, start=1):
        print(f"[{index}/{len(document_dirs)}] generating: {document_dir.name}")
        markdown_path = document_dir / "document.md"
        markdown_text = _read_text(markdown_path)
        procedure_title = _extract_procedure_title(markdown_text)
        if args.chunk_source == "stored":
            chunks = await fetch_stored_chunks(document_dir.name)
            if not chunks and args.allow_markdown_fallback:
                chunks = build_markdown_chunks(document_dir.name, markdown_path, markdown_text, procedure_title)
            elif not chunks:
                raise SystemExit(
                    f"No stored chunks found for {document_dir.name}. "
                    "Run ingestion first or pass --allow-markdown-fallback."
                )
        else:
            chunks = build_markdown_chunks(document_dir.name, markdown_path, markdown_text, procedure_title)

        rows.extend(
            generate_for_document(
                client=client,
                model=args.model,
                document_path=document_dir,
                chunks=chunks,
                queries_per_doc=args.queries_per_doc,
                temperature=args.temperature,
                max_doc_chars=args.max_doc_chars,
                max_chunk_chars=args.max_chunk_chars,
            )
        )
        write_jsonl(output, rows)

    print(f"done: wrote {len(rows)} benchmark rows to {output}")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
