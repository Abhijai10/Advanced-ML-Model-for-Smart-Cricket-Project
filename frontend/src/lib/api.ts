import type { AnalysisResponse, Capabilities, FeedbackPayload, FeedbackResponse } from "../types";

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://127.0.0.1:8000";

export function resolveApiUrl(path: string): string {
  return `${apiBaseUrl.replace(/\/$/, "")}${path}`;
}

export async function getCapabilities(): Promise<Capabilities> {
  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/capabilities`);
  if (!response.ok) {
    throw new Error("Product capabilities could not be loaded.");
  }
  return (await response.json()) as Capabilities;
}

export async function refreshAudioUrl(artifactId: string): Promise<{ audio_url: string; expires_at: string }> {
  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/audio-artifacts/${encodeURIComponent(artifactId)}/signed-url`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error("Audio link could not be refreshed.");
  }
  return (await response.json()) as { audio_url: string; expires_at: string };
}

export async function analyzeVideo(
  blob: Blob,
  filename: string,
  accessToken?: string,
  retainEvidence = false,
): Promise<AnalysisResponse> {
  const formData = new FormData();
  formData.append("file", blob, filename);
  formData.append("retain_evidence", retainEvidence ? "true" : "false");

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

export async function submitAnalysisFeedback(
  payload: FeedbackPayload,
  accessToken?: string,
): Promise<FeedbackResponse> {
  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/feedback`, {
    method: "POST",
    body: JSON.stringify(payload),
    headers: {
      "content-type": "application/json",
      ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
  });

  if (!response.ok) {
    let message = "Feedback could not be submitted.";
    try {
      const body = await response.json();
      message = body?.detail?.detail ?? body?.detail ?? message;
    } catch {
      // Keep the friendly fallback.
    }
    throw new Error(String(message));
  }

  return (await response.json()) as FeedbackResponse;
}
