import type { ChatRequest, ChatResponse } from "@/features/chat/types";
import type { DocumentItem } from "@/features/documents/types";

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export const apiClient = {
  post: <T>(path: string, body: unknown) =>
    request<T>(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  get: <T>(path: string) => request<T>(path),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  chat: {
    ask: (payload: ChatRequest) => request<ChatResponse>("/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  },
  documents: {
    list: () => request<DocumentItem[]>("/documents"),
    upload: async (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return request("/documents/upload", { method: "POST", body: formData });
    },
  },
};
