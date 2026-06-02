export type SourceItem = {
  document_id: string;
  chunk_id: string;
  filename: string;
  source_type: string;
  procedure_title?: string | null;
  page_number?: number | null;
  page_source?: string | null;
  section_title?: string | null;
  score?: number | null;
  visibility?: string | null;
  owner_user_id?: string | null;
  session_id?: string | null;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  attachment?: {
    document_id: string;
    filename: string;
    type: "document";
  } | null;
  sources?: SourceItem[];
  created_at?: string | null;
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

export type SessionItem = {
  id: string;
  owner_user_id: string;
  title?: string | null;
  description?: string | null;
  status: string;
  last_message_at?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type SessionMessageItem = {
  id: string;
  session_id: string;
  owner_user_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sources?: SourceItem[];
  llm_model_name?: string | null;
  metadata?: Record<string, unknown>;
  created_at?: string;
  updated_at?: string;
};
