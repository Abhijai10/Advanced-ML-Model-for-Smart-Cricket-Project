import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
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
  let stopTrack: ReturnType<typeof vi.fn>;
  let lastRecorder: { state: string; ondataavailable?: (event: { data: Blob }) => void; onstop?: () => void; stop: ReturnType<typeof vi.fn>; start: ReturnType<typeof vi.fn> } | null;

  beforeEach(() => {
    stopTrack = vi.fn();
    lastRecorder = null;
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi.fn(async () => ({
          getTracks: () => [{ stop: stopTrack }],
        })),
      },
    });
    class MockMediaRecorder {
      static isTypeSupported = vi.fn((type: string) => type === "video/webm");
      state = "inactive";
      ondataavailable?: (event: { data: Blob }) => void;
      onstop?: () => void;
      start = vi.fn(() => {
        this.state = "recording";
      });
      stop = vi.fn(() => {
        if (this.state !== "recording") return;
        this.state = "inactive";
        this.ondataavailable?.({ data: new Blob(["recorded"], { type: "video/webm" }) });
        this.onstop?.();
      });
      constructor() {
        // eslint-disable-next-line @typescript-eslint/no-this-alias
        lastRecorder = this;
      }
    }
    Object.defineProperty(globalThis, "MediaRecorder", {
      configurable: true,
      value: MockMediaRecorder,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("previews uploaded clips before submitting them", async () => {
    const user = userEvent.setup();
    const onResult = vi.fn();
    render(<CameraAnalysis onResult={onResult} />);

    const input = screen.getByLabelText(/upload clip/i) as HTMLInputElement;
    await user.upload(input, new File(["video"], "shot.webm", { type: "video/webm" }));

    expect(await screen.findByText(/review this take/i)).toBeInTheDocument();
    expect(onResult).not.toHaveBeenCalled();
  });

  it("keeps the live stream through retake and stops tracks on unmount", async () => {
    vi.useFakeTimers();
    const onResult = vi.fn();
    const { unmount } = render(<CameraAnalysis onResult={onResult} />);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /start analysis/i }));
      await Promise.resolve();
    });
    expect(screen.getByText(/ready/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /record shot/i }));
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(lastRecorder?.state).toBe("recording");
    fireEvent.click(screen.getByRole("button", { name: /^stop$/i }));
    expect(screen.getByText(/review this take/i)).toBeInTheDocument();
    expect(stopTrack).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("button", { name: /retake/i }));
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:smart-cricket-preview");
    expect(stopTrack).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /record shot/i }));
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    expect(lastRecorder?.state).toBe("recording");
    fireEvent.click(screen.getByRole("button", { name: /^stop$/i }));
    fireEvent.click(screen.getByRole("button", { name: /^stop$/i }));

    unmount();
    expect(stopTrack).toHaveBeenCalledTimes(1);
  });

  it("auto-stops at the configured duration", async () => {
    vi.useFakeTimers();
    render(<CameraAnalysis onResult={vi.fn()} />);

    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /start analysis/i }));
      await Promise.resolve();
    });
    expect(screen.getByText(/ready/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /record shot/i }));
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    await act(async () => {
      await Promise.resolve();
    });
    act(() => {
      vi.advanceTimersByTime(8000);
    });
    await act(async () => {
      await Promise.resolve();
    });
    act(() => {
      vi.runOnlyPendingTimers();
    });

    expect(screen.getByText(/review this take/i)).toBeInTheDocument();
    expect(lastRecorder?.stop).toHaveBeenCalledTimes(1);
  });

  it("shows an accessible fallback when camera permission is rejected", async () => {
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi.fn(async () => {
          throw new Error("permission denied");
        }),
      },
    });
    render(<CameraAnalysis onResult={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /start analysis/i }));

    expect(await screen.findByText(/permission denied/i)).toBeInTheDocument();
  });
});
