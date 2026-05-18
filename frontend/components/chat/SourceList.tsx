"use client";

import type { SourceItem } from "@/features/chat/types";

type Props = {
  sources: SourceItem[];
};

export function SourceList({ sources }: Props) {
  if (sources.length === 0) {
    return <div className="muted">No sources yet.</div>;
  }

  return (
    <div className="sources">
      {sources.map((source, index) => (
        <div key={`${source.chunk_id}-${index}`} className="source-item">
          <div>
            <strong>{source.filename}</strong>
          </div>
          <div className="meta">
            {source.source_type} | chunk {source.chunk_id} | doc {source.document_id}
          </div>
          <div className="meta">
            {source.section_title || "Untitled section"} {source.page_number ? `| page ${source.page_number}` : ""}
          </div>
        </div>
      ))}
    </div>
  );
}
