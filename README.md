# RAG Chatbot Monorepo

Monorepo scaffold for a metadata-driven RAG chatbot.

## Cấu Trúc Dự Án

```text
rag-chatbot/
├── backend/                # FastAPI backend
│   ├── app/                # Source code chính
│   │   ├── api/            # Lớp route + dependency injection
│   │   ├── core/           # Config, constants, logging, security
│   │   ├── db/             # Kết nối MongoDB và Chroma
│   │   ├── models/         # Pydantic models cho dữ liệu nội bộ
│   │   ├── schemas/        # Request/response schemas cho API
│   │   ├── repositories/   # Truy cập dữ liệu MongoDB
│   │   ├── services/       # Business logic
│   │   ├── rag/            # Toàn bộ pipeline RAG
│   │   ├── workers/        # Worker placeholder cho ingestion async
│   │   └── utils/          # Helper functions
│   ├── storage/            # File raw, markdown, temp
│   ├── tests/              # Test skeleton
│   ├── requirements.txt    # Python dependencies
│   ├── Dockerfile          # Image backend
│   └── .env.example        # Mẫu biến môi trường backend
├── frontend/               # Next.js + TypeScript
│   ├── app/                # App Router pages
│   ├── components/         # UI components tái sử dụng
│   ├── features/           # Tổ chức theo domain: chat, documents
│   ├── hooks/              # Custom hooks dùng chung
│   ├── lib/                # API client và constants
│   ├── types/              # Types dùng chung
│   ├── public/             # Static assets
│   ├── package.json        # Node dependencies
│   └── .env.local.example  # Mẫu biến môi trường frontend
├── docker-compose.yml      # Chạy MongoDB, Chroma, backend, frontend
├── README.md               # Tài liệu dự án
└── .gitignore              # File ignore cho Git
```

### Vai Trò Từng Phần

- `backend/app/api/`: chỉ xử lý request/response, không chứa business logic.
- `backend/app/services/`: điều phối luồng nghiệp vụ như upload, chat, session.
- `backend/app/repositories/`: đọc/ghi MongoDB.
- `backend/app/rag/`: xử lý converter, chunking, embedding, retrieval, generation và pipeline.
- `backend/app/db/`: khởi tạo client MongoDB và Chroma.
- `frontend/app/`: các trang chính của Next.js.
- `frontend/components/`: UI components dùng lại giữa các trang.
- `frontend/features/`: gom API, types và hooks theo từng tính năng.
- `frontend/lib/`: lớp gọi API và hằng số dùng chung.

## Architecture

- `frontend/`: Next.js + TypeScript UI.
- `backend/`: FastAPI backend using a layered architecture:
  - API routes
  - services
  - repositories
  - database/vectorstore/RAG modules
- `mongodb`: stores document, session, message, and chunk metadata.
- `chroma`: stores chunk embeddings and retrieval metadata for filters.

## Document Flow

1. PDF or DOCX is uploaded.
2. Docling converts the file to Markdown.
3. Markdown is chunked by heading where possible, with fallback window chunking.
4. Each chunk gets metadata such as:
   - `document_id`
   - `chunk_id`
   - `source_type`
   - `owner_user_id`
   - `session_id`
   - `filename`
   - `page_number`
   - `section_title`
   - `visibility`
5. Chunks are embedded with BGE-base.
6. Metadata and embeddings are stored in Chroma.
7. MongoDB stores the document, session, message, and chunk records.

## Retrieval Scopes

- `auto`: route the question first, then retrieve.
- `current_upload`: current session uploads only.
- `all_user_uploads`: all uploads owned by the current user.
- `system_docs`: global system documents only.
- `mixed`: system docs plus user uploads owned by the current user.

Retrieval permissions are enforced through metadata filters in Chroma. Prompts do not decide permissions.

## Running Locally

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Docker

```bash
docker compose up --build
```

Services:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:3000`
- MongoDB: `mongodb://localhost:27017`
- Chroma: `http://localhost:8001`

## Environment Variables

### Backend

- `MONGODB_URI`: connection string MongoDB, ví dụ `mongodb://localhost:27017` hoặc MongoDB Atlas URI.
- `MONGODB_DB_NAME`: tên database, ví dụ `rag_chatbot`.
- `CHROMA_PERSIST_DIR`: thư mục lưu Chroma persistent data.
- `CHROMA_COLLECTION_NAME`: tên collection Chroma, mặc định `rag_chunks`.
- `OPENAI_API_KEY`: khóa OpenAI để tạo câu trả lời.
- `OPENAI_MODEL`: model OpenAI dùng cho generation.
- `UPLOAD_DIR`: thư mục lưu file gốc đã upload.
- `MARKDOWN_DIR`: thư mục lưu file Markdown sau khi convert.
- `CORS_ORIGINS`: danh sách origin được phép gọi API backend.

### Frontend

- `NEXT_PUBLIC_API_BASE_URL`: URL backend FastAPI, ví dụ `http://localhost:8000`.

### Kết Nối MongoDB Cần Gì?

Để backend kết nối MongoDB, tối thiểu bạn cần:

- `MONGODB_URI`
- `MONGODB_DB_NAME`

Nếu dùng MongoDB local với Docker, URI thường chỉ cần:

```text
mongodb://mongodb:27017
```

Nếu dùng MongoDB Atlas hoặc server có xác thực, URI sẽ cần thêm:

- username
- password
- host/cluster
- database name
- `authSource` hoặc các tham số xác thực khác nếu cần
- TLS/SSL nếu môi trường yêu cầu

## Notes

- Authentication is stubbed for MVP with `demo_user_001`.
- Hybrid retrieval and reranking are intentionally out of scope for now.
- TODO: add background ingestion jobs, file validation, and richer document/session UX.
