export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

export type SourceItem = {
  document_id: string;
  chunk_id: string;
  filename: string;
  source_type: string;
  page_number?: number | null;
  section_title?: string | null;
  score?: number | null;
  visibility?: string | null;
  owner_user_id?: string | null;
  session_id?: string | null;
};

export type ChatRequest = {
  question: string;
  session_id: string | null;
  scope: string;
  selected_document_ids: string[];
};

export type ChatResponse = {
  answer: string;
  sources: SourceItem[];
  raw_contexts: unknown[];
};
