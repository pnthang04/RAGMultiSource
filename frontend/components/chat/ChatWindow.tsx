"use client";

import type { ChatMessage } from "@/features/chat/types";
import { MessageBubble } from "./MessageBubble";

type Props = {
  messages: ChatMessage[];
  loading: boolean;
};

export function ChatWindow({ messages, loading }: Props) {
  return (
    <div className="stack">
      {messages.length === 0 ? <div className="muted">Ask a question to start a retrieval session.</div> : null}
      {messages.map((message, index) => (
        <MessageBubble key={index} message={message} />
      ))}
      {loading ? <div className="muted">Thinking...</div> : null}
    </div>
  );
}
