"use client";

import type { ChatMessage } from "@/features/chat/types";

export function MessageBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const hasAttachment = isUser && Boolean(message.attachment);

  return (
    <div className={`message ${isUser ? "user" : "assistant"} ${hasAttachment ? "has-attachment" : ""}`}>
      <div className="message-head">
        <span>{isUser ? "Ban" : "Tro ly"}</span>
        {!isUser && message.sources?.length ? <span>{message.sources.length} nguon</span> : null}
      </div>

      {hasAttachment && message.attachment ? (
        <div className="message-attachment" title={message.attachment.filename}>
          <div className="attachment-icon" aria-hidden="true" />
          <div className="attachment-copy">
            <div className="attachment-name">{message.attachment.filename}</div>
            <div className="attachment-type">Document</div>
          </div>
        </div>
      ) : null}

      <div className="message-content">{message.content}</div>

      {!isUser && message.sources?.length ? (
        <div className="message-sources">
          {message.sources.slice(0, 3).map((source, index) => (
            <div key={`${source.chunk_id}-${index}`} className="source-pill">
              <strong>{source.filename}</strong>
              {source.page_number ? <div className="meta">Trang {source.page_number}</div> : null}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}
