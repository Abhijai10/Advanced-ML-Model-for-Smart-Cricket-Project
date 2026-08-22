import axe from "axe-core";
import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CameraAnalysis } from "./CameraAnalysis";
import { FeedbackPanel } from "./FeedbackPanel";
import type { AnalysisResponse } from "../types";

const result: AnalysisResponse = {
  predicted_shot: "cover_drive",
  shot_confidence: 0.82,
  technique_match_score: 74,
  detected_issues: [],
  coaching_tips: ["Keep the head still."],
  detailed_feedback: "Good shape.",
  spoken_feedback: "Keep the head still.",
  analysis_quality: { status: "ok", reasons: ["Input quality and model confidence meet thresholds."] },
  debug_metadata: {},
  source_metadata: {},
  prediction: { class_probabilities: { cover_drive: 0.82, pull_shot: 0.18 } },
  segmentation: {
    start_frame: 6,
    end_frame: 30,
    peak_frame: 18,
    prediction_trigger_frame: 30,
    completed: true,
    completion_reason: "test",
    trigger_count: 1,
  },
  timing: { duration_seconds: 1.25 },
  voice_output: {
    available: false,
    provider: "unavailable",
    audio_path: "",
    audio_url: null,
    audio_format: "none",
    audio_bytes: 0,
    is_spoken_tts: false,
  },
  api_metadata: {
    analysis_session_id: "11111111-1111-1111-1111-111111111111",
    analysis_persistence: { attempted: true, stored: true, storage_status: "stored" },
    evidence_retention: { requested: false, retained: false, status: "not_requested" },
  },
};

describe("accessibility smoke checks", () => {
  it("camera and feedback surfaces have no automated axe violations", async () => {
    const { container } = render(
      <>
        <CameraAnalysis onResult={async () => undefined} accessToken="token" />
        <FeedbackPanel result={result} accessToken="token" />
      </>,
    );

    const report = await axe.run(container);
    expect(report.violations).toEqual([]);
  });
});
