export type RetrievalScope = "auto" | "current_upload" | "all_user_uploads" | "system_docs" | "mixed";

export const retrievalScopes: RetrievalScope[] = [
  "auto",
  "current_upload",
  "all_user_uploads",
  "system_docs",
  "mixed",
];

export const defaultScope: RetrievalScope = "auto";
