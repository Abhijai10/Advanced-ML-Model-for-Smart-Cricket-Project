export type AnalysisResponse = {
  predicted_shot: string;
  shot_confidence: number;
  technique_match_score: number;
  detected_issues: Record<string, unknown>[];
  coaching_tips: string[];
  detailed_feedback: string;
  spoken_feedback: string;
  timing?: { duration_seconds?: number | null };
  segmentation: { start_frame?: number | null; end_frame?: number | null };
  voice_output?: { status?: string; url?: string | null; mime_type?: string | null };
  api_metadata?: { analysis_session_id?: string; analysis_persistence?: { stored?: boolean } };
  landmarks?: { x: number; y: number; visibility: number }[];
};

export type AnalysisJob = {
  job_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  result: AnalysisResponse | null;
  error_code: string | null;
  detail: string | null;
};

export class ApiError extends Error {
  constructor(message: string, readonly code?: string) {
    super(message);
  }
}

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

export async function analyzeVideo(file: Blob, filename: string, accessToken?: string): Promise<AnalysisResponse> {
  const payload = new FormData();
  payload.append('file', file, filename);
  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: 'POST',
    body: payload,
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  });
  const body = await response.json().catch(() => null) as AnalysisResponse | { detail?: { detail?: string; error_code?: string } } | null;
  if (!response.ok) {
    const detail = body && 'detail' in body && typeof body.detail === 'object' ? body.detail : undefined;
    throw new ApiError(detail?.detail || 'Analysis could not be completed.', detail?.error_code);
  }
  return body as AnalysisResponse;
}

async function apiJson<T>(path: string, options: RequestInit, accessToken?: string): Promise<T> {
  const headers = new Headers(options.headers);
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
  const response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  const body = await response.json().catch(() => null) as T | { detail?: { detail?: string; error_code?: string } } | null;
  if (!response.ok) {
    const detail = body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'object' ? body.detail : undefined;
    throw new ApiError(detail?.detail || 'Analysis could not be completed.', detail?.error_code);
  }
  return body as T;
}

export async function createAnalysisJob(file: Blob, filename: string, accessToken?: string): Promise<Pick<AnalysisJob, 'job_id' | 'status'>> {
  const payload = new FormData();
  payload.append('file', file, filename);
  return apiJson('/analysis/jobs', { method: 'POST', body: payload }, accessToken);
}

export function getAnalysisJob(jobId: string, accessToken?: string): Promise<AnalysisJob> {
  return apiJson(`/analysis/jobs/${encodeURIComponent(jobId)}`, { method: 'GET' }, accessToken);
}

export function getAnalytics<T>(path: string, accessToken?: string): Promise<T> {
  return apiJson<T>(`/analytics/${path.replace(/^\//, '')}`, { method: 'GET' }, accessToken);
}
