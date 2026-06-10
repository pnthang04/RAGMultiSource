import os
import base64
import requests
from backend.app.core.config import settings

PROMPT = """Trích xuất nội dung ảnh sang Markdown theo các quy tắc sau:
1. Văn bản: Giữ nguyên text, định dạng tiêu đề (#), danh sách.
2. Bảng biểu: Chuyển thành Markdown table (|---|).
3. Biểu đồ: Trích xuất dữ liệu thành bảng/danh sách. Tóm tắt xu hướng.
4. Sơ đồ/Lưu đồ: Mô tả cấu trúc và quy trình.
5. Công thức: Dùng định dạng LaTeX ($$ công thức $$).
6. Infographic/UI/Ảnh chụp: Trích xuất toàn bộ text, số liệu và mô tả ngắn gọn đối tượng chính.
CHỈ xuất nội dung Markdown (giữ nguyên ngôn ngữ gốc của ảnh). Không giải thích thêm."""

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_image(path: str) -> str:
    api_key = settings.OPENROUTER_API_KEY
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not set in environment variables.")

    base64_image = encode_image(path)
    ext = os.path.splitext(path)[-1].lower().replace('.', '')
    mime_type = f"image/{ext}" if ext in ["png", "jpeg", "webp", "gif"] else "image/jpeg"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    if settings.OPENROUTER_SITE_URL:
        headers["HTTP-Referer"] = settings.OPENROUTER_SITE_URL
    if settings.OPENROUTER_APP_NAME:
        headers["X-Title"] = settings.OPENROUTER_APP_NAME

    model = getattr(settings, "OPENROUTER_IMAGE_MODEL", "google/gemini-2.5-flash")
    
    base_url = settings.OPENROUTER_BASE_URL.rstrip('/')
    url = f"{base_url}/chat/completions"
    
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": PROMPT
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}"
                        }
                    }
                ]
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content'].strip()
    else:
        raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")

def read_image(path: str, to_markdown=True) -> str:
    return extract_image(path)
