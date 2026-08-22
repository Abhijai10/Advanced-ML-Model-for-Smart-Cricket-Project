import type { AnalysisResponse } from './api';

export type ShotType = 'cover_drive' | 'defensive' | 'pull' | 'sweep';

export type StoredAnalysisSession = {
  id: string;
  user_id: string;
  video_file_name: string;
  predicted_shot: string | null;
  shot_confidence: number | null;
  technique_match_score: number | null;
  shot_duration_seconds: number | null;
  coaching_tips: string[] | null;
  full_result: AnalysisResponse | null;
  created_at: string;
};

export function toShotType(value: string | null | undefined): ShotType | null {
  if (value === 'cover_drive' || value === 'defensive_shot') return value === 'defensive_shot' ? 'defensive' : value;
  if (value === 'pull_shot') return 'pull';
  if (value === 'sweep_shot') return 'sweep';
  return null;
}

export function shotLabel(value: string | null | undefined): string {
  return (value || 'Unknown').replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function durationLabel(seconds: number | null): string {
  if (!seconds || seconds <= 0) return '—';
  return seconds >= 60 ? `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s` : `${Math.round(seconds)}s`;
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat('en-AU', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }).format(new Date(value));
}

export function practiceStreak(rows: StoredAnalysisSession[]): number | null {
  if (!rows.length) return null;
  const days = new Set(rows.map((row) => new Date(row.created_at).toISOString().slice(0, 10)));
  let cursor = new Date();
  let count = 0;
  while (true) {
    const key = cursor.toISOString().slice(0, 10);
    if (!days.has(key)) break;
    count += 1;
    cursor.setUTCDate(cursor.getUTCDate() - 1);
  }
  return count || null;
}

export function detectedIssues(rows: StoredAnalysisSession[]): { shot: string; note: string }[] {
  return rows.flatMap((row) => {
    const issues = row.full_result?.detected_issues || [];
    return issues.slice(0, 1).map((issue) => ({
      shot: shotLabel(row.predicted_shot),
      note: String(issue.description || issue.issue || row.coaching_tips?.[0] || 'Review the coaching feedback for this analysis.'),
    }));
  }).slice(0, 3);
}
