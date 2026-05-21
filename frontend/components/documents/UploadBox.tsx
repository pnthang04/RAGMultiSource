"use client";

import { useRef, useState, type ChangeEvent, type DragEvent } from "react";

import { apiClient } from "@/lib/api-client";

type Props = {
  onUploaded: () => Promise<void>;
};

export function UploadBox({ onUploaded }: Props) {
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [statusText, setStatusText] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const uploadFile = async (file: File) => {
    if (busy) return;
    setBusy(true);
    setStatusText("Uploading...");
    try {
      await apiClient.documents.upload(file);
      setStatusText("Done");
      await onUploaded();
      setTimeout(() => setStatusText(""), 1800);
    } catch (error) {
      console.error(error);
      setStatusText("Error");
      setTimeout(() => setStatusText(""), 2500);
    } finally {
      setBusy(false);
    }
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(true);
  };

  const handleDragLeave = () => {
    setDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) {
      const ext = droppedFile.name.split(".").pop()?.toLowerCase();
      if (ext && ["pdf", "docx"].includes(ext)) {
        void uploadFile(droppedFile);
      } else {
        setStatusText("Unsupported file");
        setTimeout(() => setStatusText(""), 2500);
      }
    }
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      void uploadFile(selectedFile);
    }
  };

  const triggerSelect = () => {
    if (fileInputRef.current && !busy) {
      fileInputRef.current.click();
    }
  };

  return (
    <div className="stack" style={{ width: "100%" }}>
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx"
        style={{ display: "none" }}
        onChange={handleFileChange}
      />
      <div
        className={`upload-zone ${dragging ? "dragging" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={triggerSelect}
        style={{ pointerEvents: busy ? "none" : "auto", opacity: busy ? 0.78 : 1 }}
      >
        <div className="upload-icon">
          {busy ? (
            <span>...</span>
          ) : (
            <svg width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5h10.5a2.25 2.25 0 002.25-2.25V6.75A2.25 2.25 0 0016.5 4.5H6.75a2.25 2.25 0 00-2.25 2.25v10.5A2.25 2.25 0 006.75 19.5z" />
            </svg>
          )}
        </div>
        <div>
          <strong>{busy ? "Uploading" : "Upload tài liệu"}</strong>
          <span>Kéo thả hoặc chọn file PDF, DOC, DOCX</span>
        </div>
      </div>
      {statusText ? (
        <div className="muted" style={{ textAlign: "center", fontSize: "12px", fontWeight: 600 }}>
          {statusText}
        </div>
      ) : null}
    </div>
  );
}
