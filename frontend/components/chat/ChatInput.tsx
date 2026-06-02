"use client";

import { useRef, useState, type ChangeEvent, type FormEvent, type KeyboardEvent } from "react";

type UploadedAttachment = {
  document_id: string;
  filename: string;
  type: "document";
};

type Props = {
  onSend: (question: string, attachment?: UploadedAttachment | null) => Promise<void>;
  onUpload: (file: File) => Promise<UploadedAttachment>;
  disabled?: boolean;
};

export function ChatInput({ onSend, onUpload, disabled = false }: Props) {
  const [question, setQuestion] = useState("");
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  const [attachedFile, setAttachedFile] = useState<UploadedAttachment | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const value = question.trim();
    if (!value || sending || disabled) return;
    const attachment = attachedFile;
    setSending(true);
    try {
      await onSend(value, attachment);
      setQuestion("");
      setAttachedFile(null);
      setUploadStatus("");
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
    setUploadStatus(`Dang tai ${file.name}...`);
    try {
      const attachment = await onUpload(file);
      setAttachedFile(attachment);
      setUploadStatus("");
    } catch (error) {
      console.error(error);
      setUploadStatus("Tai file that bai");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  return (
    <form className="chat-composer" onSubmit={(event) => void handleSubmit(event)}>
      <input ref={fileInputRef} type="file" accept=".pdf,.docx" hidden onChange={(event) => void handleFileChange(event)} />

      <button
        type="button"
        className="composer-icon-btn"
        onClick={() => fileInputRef.current?.click()}
        disabled={sending || uploading || disabled}
        aria-label="Upload tai lieu"
        title="Upload tai lieu"
      >
        <span>{uploading ? "..." : "+"}</span>
      </button>

      {attachedFile ? (
        <div className="composer-attachment" title={attachedFile.filename}>
          <div className="attachment-icon" aria-hidden="true" />
          <div className="attachment-copy">
            <div className="attachment-name">{attachedFile.filename}</div>
            <div className="attachment-type">Document</div>
          </div>
        </div>
      ) : null}

      <textarea
        className="chat-input"
        value={question}
        placeholder="Nhap cau hoi. Enter de gui, Shift+Enter xuong dong."
        onChange={(event) => setQuestion(event.target.value)}
        onKeyDown={handleKeyDown}
        disabled={sending || disabled}
      />

      <button className="composer-send-btn" type="submit" disabled={!question.trim() || sending || disabled}>
        Gui
      </button>

      {uploadStatus ? <div className="composer-status">{uploadStatus}</div> : null}
    </form>
  );
}
