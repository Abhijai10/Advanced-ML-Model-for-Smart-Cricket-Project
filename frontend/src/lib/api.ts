import type { AnalysisResponse } from "../types";

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://127.0.0.1:8000";

export function resolveApiUrl(path: string): string {
  return `${apiBaseUrl.replace(/\/$/, "")}${path}`;
}

export async function analyzeVideo(blob: Blob, filename: string, accessToken?: string): Promise<AnalysisResponse> {
  const formData = new FormData();
  formData.append("file", blob, filename);

  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/analyze`, {
    method: "POST",
    body: formData,
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  });

  if (!response.ok) {
    let message = "Analysis failed. Check the camera view and try again.";
    try {
      const payload = await response.json();
      message = payload?.detail?.detail ?? payload?.detail ?? message;
    } catch {
      // Keep the friendly fallback.
    }
    throw new Error(String(message));
  }

  return (await response.json()) as AnalysisResponse;
}
