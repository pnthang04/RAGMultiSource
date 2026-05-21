import type { ChatRequest, ChatResponse, SessionItem, SessionMessageItem } from "@/features/chat/types";
import type { AuthCredentials, AuthResponse, AuthUser } from "@/features/auth/types";
import type { DocumentItem } from "@/features/documents/types";
import type { DocumentUploadResponse } from "@/features/documents/types";

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const AUTH_TOKEN_KEY = "rag_chatbot_auth_token";

function readAuthToken() {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(AUTH_TOKEN_KEY);
}

export function setAuthToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) {
    window.localStorage.setItem(AUTH_TOKEN_KEY, token);
  } else {
    window.localStorage.removeItem(AUTH_TOKEN_KEY);
  }
}

function authHeaders(): Record<string, string> {
  const token = readAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      ...authHeaders(),
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
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  auth: {
    register: (payload: AuthCredentials) =>
      request<AuthResponse>("/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
    login: (payload: AuthCredentials) =>
      request<AuthResponse>("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
    me: () => request<AuthUser>("/auth/me"),
    logout: () => request<{ success: boolean }>("/auth/logout", { method: "POST" }),
  },
  chat: {
    ask: (payload: ChatRequest) => request<ChatResponse>("/chat", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  },
  sessions: {
    list: () => request<SessionItem[]>("/sessions"),
    create: (payload: { title?: string | null; description?: string | null }) =>
      request<SessionItem>("/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
    update: (sessionId: string, payload: { title?: string | null; description?: string | null; status?: string | null }) =>
      request<SessionItem>(`/sessions/${encodeURIComponent(sessionId)}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }),
    delete: (sessionId: string) => request<{ success: boolean; session_id: string }>(`/sessions/${encodeURIComponent(sessionId)}`, { method: "DELETE" }),
    messages: (sessionId: string) => request<SessionMessageItem[]>(`/sessions/${encodeURIComponent(sessionId)}/messages`),
  },
  documents: {
    list: () => request<DocumentItem[]>("/documents"),
    upload: async (file: File, sessionId?: string) => {
      const formData = new FormData();
      formData.append("file", file);
      if (sessionId) {
        formData.append("session_id", sessionId);
      }
      return request<DocumentUploadResponse>("/documents/upload", { method: "POST", body: formData });
    },
  },
};
