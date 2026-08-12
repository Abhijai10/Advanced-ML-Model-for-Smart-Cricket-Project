import { act, fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CameraAnalysis } from "./CameraAnalysis";
import { analyzeVideo } from "../lib/api";
import type { Capabilities } from "../types";

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

const capabilities: Capabilities = {
  auth_required: false,
  feedback_enabled: true,
  model_improvement_enabled: true,
  evidence_retention_enabled: true,
  tts_provider: "signed_audio",
  max_upload_bytes: 250 * 1024 * 1024,
  max_recording_duration_seconds: 20,
  accepted_video_extensions: [".mp4", ".mov", ".webm"],
};

describe("CameraAnalysis", () => {
  let stopTrack: ReturnType<typeof vi.fn>;
  let supportedTypes: string[];
  let lastRecorder: { state: string; mimeType?: string; ondataavailable?: (event: { data: Blob }) => void; onstop?: () => void; stop: ReturnType<typeof vi.fn>; start: ReturnType<typeof vi.fn> } | null;

  beforeEach(() => {
    stopTrack = vi.fn();
    supportedTypes = ["video/webm"];
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
      static isTypeSupported = vi.fn((type: string) => supportedTypes.includes(type));
      state = "inactive";
      mimeType: string;
      ondataavailable?: (event: { data: Blob }) => void;
      onstop?: () => void;
      start = vi.fn(() => {
        this.state = "recording";
      });
      stop = vi.fn(() => {
        if (this.state !== "recording") return;
        this.state = "inactive";
        this.ondataavailable?.({ data: new Blob(["recorded"], { type: this.mimeType }) });
        this.onstop?.();
      });
      constructor(_stream: MediaStream, options?: MediaRecorderOptions) {
        this.mimeType = options?.mimeType ?? "";
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
    vi.mocked(analyzeVideo).mockClear();
  });

  async function recordAndAnalyze() {
    vi.useFakeTimers();
    render(<CameraAnalysis onResult={vi.fn()} accessToken="token" />);
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /start analysis/i }));
      await Promise.resolve();
    });
    fireEvent.click(screen.getByRole("button", { name: /record shot/i }));
    act(() => {
      vi.advanceTimersByTime(3000);
    });
    fireEvent.click(screen.getByRole("button", { name: /^stop$/i }));
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /analyze clip/i }));
      await Promise.resolve();
    });
  }

  it("previews uploaded clips before submitting them", async () => {
    const user = userEvent.setup();
    const onResult = vi.fn();
    render(<CameraAnalysis onResult={onResult} />);

    const input = screen.getByLabelText(/upload clip/i) as HTMLInputElement;
    await user.upload(input, new File(["video"], "shot.webm", { type: "video/webm" }));

    expect(await screen.findByText(/review this take/i)).toBeInTheDocument();
    expect(onResult).not.toHaveBeenCalled();
  });

  it("disables clip retention when model improvement is unavailable", async () => {
    render(
      <CameraAnalysis
        onResult={vi.fn()}
        accessToken="token"
        capabilities={{ ...capabilities, model_improvement_enabled: false, evidence_retention_enabled: false }}
      />,
    );

    expect(screen.getByText(/participation is disabled/i)).toBeInTheDocument();
    expect(screen.getByRole("checkbox")).toBeDisabled();
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

  it.each([
    ["video/webm;codecs=vp9", "webm"],
    ["video/webm;codecs=vp8", "webm"],
    ["video/webm", "webm"],
    ["video/mp4", "mp4"],
  ])("uses the selected recorder MIME type and %s extension", async (mimeType, extension) => {
    supportedTypes = [mimeType];
    await recordAndAnalyze();

    expect(lastRecorder?.mimeType).toBe(mimeType);
    expect(vi.mocked(analyzeVideo)).toHaveBeenCalledWith(
      expect.objectContaining({ type: mimeType }),
      expect.stringMatching(new RegExp(`\\.${extension}$`)),
      "token",
      false,
    );
  });

  it("shows upload fallback when no MediaRecorder MIME type is supported", async () => {
    vi.useFakeTimers();
    supportedTypes = [];
    render(<CameraAnalysis onResult={vi.fn()} />);
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: /start analysis/i }));
      await Promise.resolve();
    });
    fireEvent.click(screen.getByRole("button", { name: /record shot/i }));
    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(screen.getByText(/upload an mp4, mov, or webm/i)).toBeInTheDocument();
  });
});
