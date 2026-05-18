"use client";

import type { ChatMessage } from "@/features/chat/types";

export function MessageBubble({ message }: { message: ChatMessage }) {
  return (
    <div className={`message ${message.role}`}>
      <div className="meta">{message.role}</div>
      <div>{message.content}</div>
    </div>
  );
}
