"use client";

import { useEffect, useMemo, useState } from "react";

import { useAuth } from "@/components/auth/AuthProvider";
import { ChatInput } from "@/components/chat/ChatInput";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { SessionList } from "@/components/chat/SessionList";
import { ApiError, apiClient } from "@/lib/api-client";
import { defaultScope } from "@/lib/constants";
import type { ChatMessage, SessionItem, SessionMessageItem } from "@/features/chat/types";

function getApiErrorDetail(error: unknown): string | null {
  if (!(error instanceof ApiError)) {
    return null;
  }
  if (typeof error.detail === "string") {
    return error.detail;
  }
  if (error.detail && typeof error.detail === "object" && "detail" in error.detail) {
    const detail = (error.detail as { detail?: unknown }).detail;
    return typeof detail === "string" ? detail : null;
  }
  return null;
}

function isSessionNotFoundError(error: unknown): error is ApiError {
  return error instanceof ApiError && error.status === 404 && getApiErrorDetail(error)?.toLowerCase().includes("session not found") === true;
}

function mapSessionMessages(messages: SessionMessageItem[]): ChatMessage[] {
  return messages
    .filter((message) => message.role === "user" || message.role === "assistant")
    .map((message) => ({
      role: message.role as "user" | "assistant",
      content: message.content,
      sources: message.sources,
      created_at: message.created_at ?? null,
    }));
}

export default function ChatPage() {
  const { user, ready, logout } = useAuth();
  const [sessions, setSessions] = useState<SessionItem[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [booting, setBooting] = useState(true);
  const [sessionBusy, setSessionBusy] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const activeSession = useMemo(
    () => sessions.find((session) => session.id === activeSessionId) ?? null,
    [activeSessionId, sessions],
  );

  async function refreshSessions(nextActiveSessionId?: string | null) {
    const result = await apiClient.sessions.list();
    setSessions(result);
    if (nextActiveSessionId !== undefined) {
      setActiveSessionId(nextActiveSessionId);
    }
    return result;
  }

  async function loadSessionMessages(sessionId: string) {
    const result = await apiClient.sessions.messages(sessionId);
    setMessages(mapSessionMessages(result));
  }

  async function ensureSession() {
    if (activeSessionId) {
      return activeSessionId;
    }
    const session = await apiClient.sessions.create({});
    const sessionId = session.id;
    await refreshSessions(sessionId);
    setMessages([]);
    return sessionId;
  }

  async function startNewChat() {
    if (loading || sessionBusy) return;
    setSessionBusy(true);
    setActiveSessionId(null);
    setMessages([]);
    try {
      const session = await apiClient.sessions.create({});
      const sessionId = session.id;
      await refreshSessions(sessionId);
    } catch (error) {
      console.error(error);
      setMessages([
        {
          role: "assistant",
          content: "Không tạo được phiên chat mới. Vui lòng thử lại.",
        },
      ]);
    } finally {
      setSessionBusy(false);
    }
  }

  async function handleSelectSession(session: SessionItem) {
    setActiveSessionId(session.id);
    await loadSessionMessages(session.id);
  }

  async function handleEditSession(session: SessionItem) {
    const nextTitle = window.prompt("Sửa tên phiên chat", session.title || "");
    if (nextTitle === null) return;
    const trimmed = nextTitle.trim();
    const updated = await apiClient.sessions.update(session.id, { title: trimmed || null });
    setSessions((current) => current.map((item) => (item.id === session.id ? updated : item)));
  }

  async function handleDeleteSession(session: SessionItem) {
    const confirmed = window.confirm(`Xóa phiên chat "${session.title || "Phiên chưa đặt tên"}"?`);
    if (!confirmed) return;
    await apiClient.sessions.delete(session.id);
    const nextSessions = await refreshSessions();
    if (nextSessions.length > 0) {
      const nextActive = nextSessions[0].id;
      setActiveSessionId(nextActive);
      await loadSessionMessages(nextActive);
    } else {
      setActiveSessionId(null);
      setMessages([]);
    }
  }

  async function handleSend(question: string, attachment?: ChatMessage["attachment"]) {
    const sessionId = await ensureSession();
    setActiveSessionId(sessionId);
    const selectedDocumentIds = attachment?.document_id ? [attachment.document_id] : [];
    setMessages((current) => [...current, { role: "user", content: question, attachment }]);
    setLoading(true);
    try {
      let activeId = sessionId;
      let response;
      try {
        response = await apiClient.chat.ask({
          question,
          scope: selectedDocumentIds.length > 0 ? "current_upload" : defaultScope,
          session_id: activeId,
          selected_document_ids: selectedDocumentIds,
        });
      } catch (error) {
        if (!isSessionNotFoundError(error)) {
          throw error;
        }
        const freshSession = await apiClient.sessions.create({});
        activeId = freshSession.id;
        setActiveSessionId(activeId);
        await refreshSessions(activeId);
        response = await apiClient.chat.ask({
          question,
          scope: selectedDocumentIds.length > 0 ? "current_upload" : defaultScope,
          session_id: activeId,
          selected_document_ids: selectedDocumentIds,
        });
      }
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: response.answer,
          sources: response.sources,
        },
      ]);
      await refreshSessions(activeId);
    } catch (error) {
      console.error(error);
      const detail = getApiErrorDetail(error);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          content: detail || "Không gửi được câu hỏi. Vui lòng thử lại.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function handleUpload(file: File) {
    const sessionId = await ensureSession();
    const response = await apiClient.documents.upload(file, sessionId);
    return { document_id: response.document_id, filename: response.filename, type: "document" as const };
    setMessages((current) => [
      ...current,
      {
        role: "assistant",
        content: `Đã upload "${response.filename}". File đã được đưa vào hàng đợi xử lý; khi worker chạy xong bạn có thể hỏi nội dung file trong session này.`,
      },
    ]);
  }

  useEffect(() => {
    if (!ready || !user) {
      return;
    }

    let mounted = true;

    async function bootstrap() {
      try {
        const loadedSessions = await apiClient.sessions.list();
        if (!mounted) return;
        setSessions(loadedSessions);
        if (loadedSessions.length > 0) {
          const nextActive = loadedSessions[0].id;
          setActiveSessionId(nextActive);
          await loadSessionMessages(nextActive);
        }
      } finally {
        if (mounted) {
          setBooting(false);
        }
      }
    }

    void bootstrap();
    return () => {
      mounted = false;
    };
  }, [ready, user]);

  return (
    <main className={`chat-shell ${sidebarCollapsed ? "collapsed" : ""}`}>
      <aside className="chat-sidebar panel">
        <div className="chat-sidebar-head">
          <div>
            <div className="eyebrow">Chat</div>
            <div className="sidebar-title">Lịch sử</div>
          </div>
          <button
            type="button"
            className="sidebar-toggle"
            onClick={() => setSidebarCollapsed((value) => !value)}
            aria-label={sidebarCollapsed ? "Mở sidebar" : "Thu gọn sidebar"}
            title={sidebarCollapsed ? "Mở sidebar" : "Thu gọn sidebar"}
          >
            {sidebarCollapsed ? ">" : "<"}
          </button>
        </div>

        <button className="button chat-new-btn" type="button" onClick={() => void startNewChat()} disabled={loading || sessionBusy}>
          + New chat
        </button>

        {!sidebarCollapsed ? (
          <>
            <div className="chat-sidebar-body">
              <div className="scroll-area">
                {booting ? (
                  <div className="muted" style={{ padding: "10px 2px", fontSize: "13px" }}>
                    Đang tải...
                  </div>
                ) : (
                  <SessionList
                    sessions={sessions}
                    activeSessionId={activeSessionId}
                    onSelect={(session) => void handleSelectSession(session)}
                    onEdit={(session) => void handleEditSession(session)}
                    onDelete={(session) => void handleDeleteSession(session)}
                  />
                )}
              </div>
            </div>

            {ready && user ? (
              <div className="auth-user-card">
                <div className="auth-user-avatar">{user.name?.trim().charAt(0).toUpperCase() || "U"}</div>
                <div className="auth-user-copy">
                  <div className="auth-user-name">{user.name}</div>
                  <div className="auth-user-email">{user.email}</div>
                </div>
                <button className="auth-user-logout" type="button" onClick={() => void logout()}>
                  Đăng xuất
                </button>
              </div>
            ) : null}
          </>
        ) : null}
      </aside>

      <section className="chat-main">
        <header className="chat-header">
          <div>
            <div className="chat-kicker">RAG chatbot</div>
            <h1 className="chat-title">{activeSession?.title || "Chat"}</h1>
          </div>
        </header>

        <ChatWindow messages={messages} loading={loading} />

        <div className="chat-footer">
          <ChatInput onSend={handleSend} onUpload={handleUpload} disabled={booting || loading || sessionBusy || !ready || !user} />
        </div>
      </section>
    </main>
  );
}
