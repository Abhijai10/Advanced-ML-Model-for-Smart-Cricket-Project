import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FeedbackPanel } from "./FeedbackPanel";
import type { AnalysisResponse } from "../types";

const mocks = vi.hoisted(() => ({
  submitAnalysisFeedback: vi.fn(async () => ({
    status: "stored",
    storage_status: "stored",
    feedback_id: "feedback-1",
    accepted_for_review: true,
    stored: true,
    duplicate_clip_hash: false,
    request_id: "request-1",
    message: "Feedback saved and queued for human review.",
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
  api_metadata: {
    analysis_session_id: "11111111-1111-1111-1111-111111111111",
    clip_hash: "a".repeat(64),
    pipeline_version: "phase12",
  },
};

describe("FeedbackPanel", () => {
  beforeEach(() => {
    mocks.submitAnalysisFeedback.mockClear();
  });

  it("renders result details and submits safe feedback payload", async () => {
    const user = userEvent.setup();
    render(<FeedbackPanel result={result} accessToken="token" />);

    expect(screen.getAllByText(/cover drive/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/audio unavailable/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "incorrect" }));
    await user.selectOptions(screen.getByLabelText(/correct shot/i), "pull_shot");
    await user.click(screen.getByLabelText(/share this clip result/i));
    await user.click(screen.getByRole("button", { name: /save feedback/i }));

    await waitFor(() => expect(mocks.submitAnalysisFeedback).toHaveBeenCalled());
    expect(mocks.submitAnalysisFeedback).toHaveBeenCalledWith(
      expect.objectContaining({
        analysis_session_id: "11111111-1111-1111-1111-111111111111",
        prediction_was_correct: "incorrect",
        corrected_shot: "pull_shot",
        consent_to_model_improvement: true,
      }),
      "token",
    );
    expect(await screen.findByRole("button", { name: /feedback saved/i })).toBeDisabled();
  });

  it("does not show saved when feedback persistence fails", async () => {
    mocks.submitAnalysisFeedback.mockRejectedValueOnce(new Error("Feedback could not be saved durably."));
    const user = userEvent.setup();
    render(<FeedbackPanel result={result} accessToken="token" />);

    await user.click(screen.getByRole("button", { name: /save feedback/i }));

    expect(await screen.findByText(/could not be saved durably/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /feedback saved/i })).not.toBeInTheDocument();
  });

  it("shows an idempotent duplicate outcome distinctly", async () => {
    mocks.submitAnalysisFeedback.mockResolvedValueOnce({
      status: "duplicate",
      storage_status: "duplicate",
      feedback_id: "feedback-1",
      accepted_for_review: true,
      stored: false,
      duplicate_clip_hash: true,
      request_id: "request-1",
      message: "This feedback candidate was already saved for review.",
    });
    const user = userEvent.setup();
    render(<FeedbackPanel result={result} accessToken="token" />);

    await user.click(screen.getByRole("button", { name: /save feedback/i }));

    expect(await screen.findByText(/already saved for review/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /already saved/i })).toBeDisabled();
  });

  it("resets feedback state when a new analysis arrives", async () => {
    const user = userEvent.setup();
    const nextResult = {
      ...result,
      predicted_shot: "pull_shot",
      api_metadata: {
        ...result.api_metadata,
        analysis_session_id: "22222222-2222-2222-2222-222222222222",
        clip_hash: "b".repeat(64),
      },
    };
    const { rerender } = render(<FeedbackPanel result={result} accessToken="token" />);

    await user.click(screen.getByRole("button", { name: "incorrect" }));
    await user.click(screen.getByRole("button", { name: /save feedback/i }));
    expect(await screen.findByRole("button", { name: /feedback saved/i })).toBeDisabled();

    rerender(<FeedbackPanel result={nextResult} accessToken="token" />);

    expect(screen.getByRole("button", { name: /save feedback/i })).not.toBeDisabled();
    expect(screen.getByRole("button", { name: "unsure" })).toHaveClass("active");
    await user.click(screen.getByRole("button", { name: /save feedback/i }));
    await waitFor(() => expect(mocks.submitAnalysisFeedback).toHaveBeenCalledTimes(2));
    expect(mocks.submitAnalysisFeedback).toHaveBeenLastCalledWith(
      expect.objectContaining({ analysis_session_id: "22222222-2222-2222-2222-222222222222" }),
      "token",
    );
  });
});
