"use client";

import type { DocumentItem } from "@/features/documents/types";

export function DocumentCard({ document }: { document: DocumentItem }) {
  return (
    <div className="message">
      <div>
        <strong>{document.filename}</strong>
      </div>
      <div className="meta">
        {document.status} | {document.source_type} | {document.visibility}
      </div>
      <div className="meta">Document ID: {document.id}</div>
    </div>
  );
}
