import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { FeedbackPanel } from "./FeedbackPanel";
import type { AnalysisResponse } from "../types";

const mocks = vi.hoisted(() => ({
  submitAnalysisFeedback: vi.fn(async () => ({
    status: "accepted",
    feedback_id: "feedback-1",
    accepted_for_review: true,
    stored: false,
    duplicate_clip_hash: false,
    request_id: "request-1",
    message: "Feedback queued.",
  })),
}));

vi.mock("../lib/api", async () => {
  const actual = await vi.importActual<typeof import("../lib/api")>("../lib/api");
  return {
    ...actual,
    submitAnalysisFeedback: mocks.submitAnalysisFeedback,
  };
});

const result: AnalysisResponse = {
  predicted_shot: "cover_drive",
  shot_confidence: 0.82,
  technique_match_score: 74,
  detected_issues: [],
  coaching_tips: ["Keep the head still."],
  detailed_feedback: "Good shape.",
  spoken_feedback: "Keep the head still.",
  analysis_quality: { status: "ok", reasons: ["Input quality and model confidence meet thresholds."] },
  debug_metadata: { model_version: "phase8-best" },
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
  api_metadata: { clip_hash: "a".repeat(64), pipeline_version: "phase12" },
};

describe("FeedbackPanel", () => {
  it("renders result details and submits safe feedback payload", async () => {
    const user = userEvent.setup();
    render(<FeedbackPanel result={result} accessToken="token" />);

    expect(screen.getAllByText(/cover drive/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/audio unavailable/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "incorrect" }));
    await user.selectOptions(screen.getByLabelText(/correct shot/i), "pull_shot");
    await user.click(screen.getByLabelText(/share this clip result/i));
    await user.click(screen.getByRole("button", { name: /send feedback/i }));

    await waitFor(() => expect(mocks.submitAnalysisFeedback).toHaveBeenCalled());
    expect(mocks.submitAnalysisFeedback).toHaveBeenCalledWith(
      expect.objectContaining({
        clip_hash: "a".repeat(64),
        predicted_shot: "cover_drive",
        prediction_was_correct: "incorrect",
        corrected_shot: "pull_shot",
        consent_to_model_improvement: true,
      }),
      "token",
    );
  });
});
