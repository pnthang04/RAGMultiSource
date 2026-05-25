# LangSmith Traces Reader Script

Script này giúp bạn đọc, tìm kiếm, và quản lý LangSmith traces từ project RAGMultiDocs.

## 📋 Yêu cầu

1. Cài đặt dependencies (đã có trong `requirements.txt`):
   ```bash
   pip install langsmith
   ```

2. Cấu hình LangSmith API key trong `.env` file:
   ```env
   LANGSMITH_API_KEY=your_api_key_here
   LANGSMITH_PROJECT=RAGMultiDocs
   LANGSMITH_ENDPOINT=https://api.smith.langchain.com
   ```

## 🚀 Cách sử dụng

### 1. Liệt kê traces gần đây
```bash
# Lấy 10 traces gần nhất trong 24 giờ qua
python backend/scripts/read_langsmith_traces.py list

# Lấy 20 traces trong 48 giờ qua
python backend/scripts/read_langsmith_traces.py list --limit 20 --hours 48

# Lấy chỉ LLM traces
python backend/scripts/read_langsmith_traces.py list --run-type llm

# Lấy chỉ chain traces
python backend/scripts/read_langsmith_traces.py list --run-type chain

# Lấy chỉ tool traces
python backend/scripts/read_langsmith_traces.py list --run-type tool
```

### 2. Lấy chi tiết một trace cụ thể
```bash
python backend/scripts/read_langsmith_traces.py details <trace_id>

# Ví dụ:
python backend/scripts/read_langsmith_traces.py details "abc123def456"
```

### 3. Tìm kiếm traces theo từ khóa
```bash
# Tìm traces chứa từ "error"
python backend/scripts/read_langsmith_traces.py search --query "error"

# Tìm traces chứa "RAG" với 20 results
python backend/scripts/read_langsmith_traces.py search --query "RAG" --limit 20

# Tìm traces chứa "embedding"
python backend/scripts/read_langsmith_traces.py search --query "embedding"
```

### 4. Export traces thành JSON
```bash
# Export 100 traces gần nhất thành JSON file
python backend/scripts/read_langsmith_traces.py export

# Export với custom output file
python backend/scripts/read_langsmith_traces.py export --output my_traces.json

# Export 500 traces
python backend/scripts/read_langsmith_traces.py export --limit 500 --output traces_500.json
```

## 📊 Output

Script sẽ hiển thị:
- **ID**: ID của trace (dùng để lấy chi tiết)
- **Name**: Tên của trace (function/step name)
- **Run Type**: Loại run (chain, llm, tool, retriever, etc.)
- **Status**: Trạng thái (success, error)
- **Start Time**: Thời gian bắt đầu
- **Duration**: Thời gian thực thi (tính bằng giây)
- **Inputs**: Dữ liệu đầu vào
- **Outputs**: Dữ liệu đầu ra
- **Error**: Thông báo lỗi nếu có
- **Tags**: Tags gắn với trace

## 🔍 Các run types phổ biến

- `llm` - LLM calls (OpenAI, OpenRouter, etc.)
- `chain` - LangChain chains
- `tool` - Tool/function calls
- `retriever` - Retrieval operations
- `prompt` - Prompt templates
- `embedding` - Embedding operations

## 💡 Tips

1. **Nhìn duration để debug performance**:
   ```bash
   python backend/scripts/read_langsmith_traces.py list --limit 50
   ```
   So sánh duration của các traces để tìm bottleneck.

2. **Tìm errors nhanh**:
   ```bash
   python backend/scripts/read_langsmith_traces.py search --query "error"
   ```

3. **Analyze LLM calls**:
   ```bash
   python backend/scripts/read_langsmith_traces.py list --run-type llm --hours 24
   ```

4. **Export để phân tích sau**:
   ```bash
   python backend/scripts/read_langsmith_traces.py export --output analysis.json
   ```
   Rồi bạn có thể dùng Python/jq để phân tích file JSON.

## 🐛 Troubleshooting

### "LANGSMITH_API_KEY không được set"
- Kiểm tra `.env` file có `LANGSMITH_API_KEY` không
- Hoặc set environment variable: 
  ```bash
  export LANGSMITH_API_KEY=your_key
  ```

### "Không tìm thấy traces"
- Kiểm tra `LANGSMITH_PROJECT` name có đúng không
- Kiểm tra có traces trong project không (vào https://smith.langchain.com để check)
- Trace có thể đã bị xóa nếu quá cũ (tuỳ vào retention policy)

### "Connection error"
- Kiểm tra internet connection
- Kiểm tra `LANGSMITH_ENDPOINT` có chính xác không

## 📝 Examples

### Tìm tất cả failed traces:
```bash
python backend/scripts/read_langsmith_traces.py search --query "status" --limit 50
```

### Analyze query rewriting performance:
```bash
python backend/scripts/read_langsmith_traces.py search --query "query_rewriter" --limit 20
```

### Check retrieval operations:
```bash
python backend/scripts/read_langsmith_traces.py list --run-type retriever --hours 24 --limit 10
```
