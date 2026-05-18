import { apiClient } from "@/lib/api-client";
import type { DocumentItem, DocumentUploadResponse } from "./types";

export const documentsApi = {
  list: (): Promise<DocumentItem[]> => apiClient.get<DocumentItem[]>("/documents"),
  upload: (file: File): Promise<DocumentUploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);
    return fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/documents/upload`, {
      method: "POST",
      body: formData,
    }).then(async (response) => {
      if (!response.ok) throw new Error(`Upload failed: ${response.status}`);
      return (await response.json()) as DocumentUploadResponse;
    });
  },
};
