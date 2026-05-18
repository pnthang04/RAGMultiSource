"use client";

import { useState } from "react";

import { ChatInput } from "@/components/chat/ChatInput";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { SourceList } from "@/components/chat/SourceList";
import { apiClient } from "@/lib/api-client";
import { defaultScope, RetrievalScope } from "@/lib/constants";
import type { ChatMessage, ChatResponse } from "@/features/chat/types";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sources, setSources] = useState<ChatResponse["sources"]>([]);
  const [loading, setLoading] = useState(false);

  async function handleSend(question: string, scope: RetrievalScope) {
    setMessages((current) => [...current, { role: "user", content: question }]);
    setLoading(true);
    try {
      const response = await apiClient.chat.ask({
        question,
        scope,
        session_id: null,
        selected_document_ids: [],
      });
      setMessages((current) => [...current, { role: "assistant", content: response.answer }]);
      setSources(response.sources);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page-shell">
      <div className="topbar">
        <div>
          <div className="brand">Chat</div>
          <div className="muted">Scope-aware retrieval with source citations</div>
        </div>
      </div>
      <div className="grid">
        <section className="card stack">
          <ChatWindow messages={messages} loading={loading} />
          <ChatInput onSend={handleSend} defaultScope={defaultScope} />
        </section>
        <section className="card">
          <h2>Sources</h2>
          <SourceList sources={sources} />
        </section>
      </div>
    </main>
  );
}
