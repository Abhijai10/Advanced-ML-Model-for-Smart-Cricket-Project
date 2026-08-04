import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { CameraAnalysis } from "./CameraAnalysis";

vi.mock("../lib/api", () => ({
  analyzeVideo: vi.fn(async () => ({
    predicted_shot: "cover_drive",
    shot_confidence: 0.8,
    technique_match_score: 75,
    detected_issues: [],
    coaching_tips: ["Keep the head still."],
    detailed_feedback: "Good shape.",
    spoken_feedback: "Keep the head still.",
    analysis_quality: { status: "ok", reasons: [] },
    debug_metadata: {},
    source_metadata: {},
    prediction: { class_probabilities: { cover_drive: 0.8 } },
    segmentation: {
      start_frame: 1,
      end_frame: 30,
      peak_frame: 20,
      prediction_trigger_frame: 30,
      completed: true,
      completion_reason: "test",
      trigger_count: 1,
    },
    timing: { duration_seconds: 1.2 },
    voice_output: {
      available: false,
      provider: "unavailable",
      audio_path: "",
      audio_url: null,
      audio_format: "none",
      audio_bytes: 0,
      is_spoken_tts: false,
    },
    api_metadata: { clip_hash: "a".repeat(64) },
  })),
}));

describe("CameraAnalysis", () => {
  it("previews uploaded clips before submitting them", async () => {
    const user = userEvent.setup();
    const onResult = vi.fn();
    render(<CameraAnalysis onResult={onResult} />);

    const input = screen.getByLabelText(/upload clip/i) as HTMLInputElement;
    await user.upload(input, new File(["video"], "shot.webm", { type: "video/webm" }));

    expect(await screen.findByText(/review this take/i)).toBeInTheDocument();
    expect(onResult).not.toHaveBeenCalled();
  });
});
