"use client";

import type { SessionItem } from "@/features/chat/types";

type Props = {
  sessions: SessionItem[];
  activeSessionId: string | null;
  onSelect: (session: SessionItem) => void;
  onEdit: (session: SessionItem) => void;
  onDelete: (session: SessionItem) => void;
};

export function SessionList({ sessions, activeSessionId, onSelect, onEdit, onDelete }: Props) {
  if (sessions.length === 0) {
    return <div className="muted" style={{ padding: "10px 2px", fontSize: "12px" }}>Chưa có phiên chat</div>;
  }

  return (
    <div className="session-list">
      {sessions.map((session) => {
        const active = session.id === activeSessionId;
        return (
          <div
            key={session.id}
            className={`item-card session-card ${active ? "active" : ""}`}
            role="button"
            tabIndex={0}
            onClick={() => onSelect(session)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelect(session);
              }
            }}
          >
            <div className="session-card-main">
              <div className="session-title">{session.title || "Phiên chưa đặt tên"}</div>
              {session.last_message_at ? (
                <div className="meta" style={{ marginTop: 4 }}>
                  Cập nhật gần nhất
                </div>
              ) : null}
            </div>
            <div className="session-card-actions">
              <button
                type="button"
                className="session-action-btn"
                onClick={(event) => {
                  event.stopPropagation();
                  onEdit(session);
                }}
                aria-label="Sửa phiên"
                title="Sửa"
              >
                ✎
              </button>
              <button
                type="button"
                className="session-action-btn danger"
                onClick={(event) => {
                  event.stopPropagation();
                  onDelete(session);
                }}
                aria-label="Xóa phiên"
                title="Xóa"
              >
                ×
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
