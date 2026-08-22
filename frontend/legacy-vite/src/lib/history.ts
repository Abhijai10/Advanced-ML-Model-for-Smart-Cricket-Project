import type { AnalysisResponse, AnalysisSession, ShotChartDatum } from "../types";

export function shotName(label: string | null | undefined): string {
  if (!label) return "Unknown";
  return label
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function segmentDurationSeconds(result: AnalysisResponse, fps = 30): number {
  if (typeof result.timing?.duration_seconds === "number") {
    return result.timing.duration_seconds;
  }
  const start = result.segmentation.start_frame;
  const end = result.segmentation.end_frame;
  if (typeof start === "number" && typeof end === "number" && end >= start) {
    return Number(((end - start + 1) / fps).toFixed(2));
  }
  return 0;
}

export function buildChartData(rows: AnalysisSession[]): ShotChartDatum[] {
  const map = new Map<string, ShotChartDatum>();
  for (const row of rows) {
    const key = row.predicted_shot ?? "unknown";
    const current = map.get(key) ?? { shot: shotName(key), count: 0, seconds: 0 };
    current.count += 1;
    current.seconds = Number((current.seconds + (row.shot_duration_seconds ?? 0)).toFixed(2));
    map.set(key, current);
  }
  return Array.from(map.values()).sort((a, b) => b.count - a.count);
}

export function fallbackHistory(): AnalysisSession[] {
  return [];
}
