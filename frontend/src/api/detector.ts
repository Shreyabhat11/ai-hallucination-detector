import { apiRequest } from "./client"
import type { AnalysisMode, AnalysisResponse, HealthResponse } from "../types/detector"

export function analyzeAnswer(prompt: string, mode: AnalysisMode): Promise<AnalysisResponse> {
  return apiRequest<AnalysisResponse>("/ask", {
    method: "POST",
    body: { prompt, mode },
  })
}

export function getHealth(): Promise<HealthResponse> {
  // Health checks should fail fast -- no need for the full 90s client timeout.
  return apiRequest<HealthResponse>("/health", { timeoutMs: 8_000 })
}
