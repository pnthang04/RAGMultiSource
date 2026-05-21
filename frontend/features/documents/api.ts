import { apiClient } from "@/lib/api-client";
import type { DocumentItem, DocumentUploadResponse } from "./types";

export const documentsApi = {
  list: (): Promise<DocumentItem[]> => apiClient.get<DocumentItem[]>("/documents"),
  upload: (file: File, sessionId?: string): Promise<DocumentUploadResponse> =>
    apiClient.documents.upload(file, sessionId),
};
