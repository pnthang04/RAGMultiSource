import { apiClient } from "@/lib/api-client";
import type { ChatRequest, ChatResponse } from "./types";

export const chatApi = {
  ask: (payload: ChatRequest): Promise<ChatResponse> => apiClient.post<ChatResponse>("/chat", payload),
};
