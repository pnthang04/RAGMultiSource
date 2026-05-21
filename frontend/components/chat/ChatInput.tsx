"use client";

import { useRef, useState, type ChangeEvent, type FormEvent, type KeyboardEvent } from "react";

type Props = {
  onSend: (question: string) => Promise<void>;
  onUpload: (file: File) => Promise<void>;
  disabled?: boolean;
};

export function ChatInput({ onSend, onUpload, disabled = false }: Props) {
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const value = question.trim();
    if (!value || sending || disabled) return;
    setSending(true);
    try {
      await onSend(value);
      setQuestion("");
    } finally {
      setSending(false);
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  };

  const handleFileChange = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadStatus(`Đang tải ${file.name}...`);
    try {
      await onUpload(file);
      setUploadStatus(`Đã tải ${file.name}`);
      setTimeout(() => setUploadStatus(""), 2000);
    } catch (error) {
      console.error(error);
      setUploadStatus("Tải file thất bại");
      setTimeout(() => setUploadStatus(""), 2500);
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  return (
    <form className="chat-composer" onSubmit={(e) => void handleSubmit(e)}>
      <input ref={fileInputRef} type="file" accept=".pdf,.docx" hidden onChange={(e) => void handleFileChange(e)} />

      <button
        type="button"
        className="composer-icon-btn"
        onClick={() => fileInputRef.current?.click()}
        disabled={sending || uploading || disabled}
        aria-label="Upload tài liệu"
        title="Upload tài liệu"
      >
        <span>{uploading ? "..." : "+"}</span>
      </button>

      <textarea
        className="chat-input"
        value={question}
        placeholder="Nhập câu hỏi. Enter để gửi, Shift+Enter xuống dòng."
        onChange={(event) => setQuestion(event.target.value)}
        onKeyDown={handleKeyDown}
        disabled={sending || disabled}
      />

      <button className="composer-send-btn" type="submit" disabled={!question.trim() || sending || disabled}>
        Gửi
      </button>

      {uploadStatus ? <div className="composer-status">{uploadStatus}</div> : null}
    </form>
  );
}
