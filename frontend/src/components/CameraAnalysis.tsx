import { useEffect, useMemo, useRef, useState } from "react";
import { Camera, CircleStop, Clock3, Play, RotateCcw, Upload, UserRoundCheck } from "lucide-react";
import { analyzeVideo } from "../lib/api";
import type { AnalysisResponse, Capabilities } from "../types";

type CameraAnalysisProps = {
  onResult: (result: AnalysisResponse, sourceName: string) => Promise<void>;
  accessToken?: string;
  capabilities?: Capabilities | null;
};

type RecordingFormat = {
  mimeType: string;
  extension: "webm" | "mp4";
};

const recordingFormats: RecordingFormat[] = [
  { mimeType: "video/webm;codecs=vp9", extension: "webm" },
  { mimeType: "video/webm;codecs=vp8", extension: "webm" },
  { mimeType: "video/webm", extension: "webm" },
  { mimeType: "video/mp4", extension: "mp4" },
];

function clampRecordingSeconds(raw: unknown): number {
  const parsed = Number(raw ?? 8);
  if (!Number.isFinite(parsed)) return 8;
  return Math.min(20, Math.max(3, Math.round(parsed)));
}

function selectRecordingFormat(): RecordingFormat | null {
  if (typeof MediaRecorder === "undefined") return null;
  return recordingFormats.find((format) => MediaRecorder.isTypeSupported(format.mimeType)) ?? null;
}

export function CameraAnalysis({ onResult, accessToken, capabilities }: CameraAnalysisProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const countdownTimerRef = useRef<number | null>(null);
  const analysisTimersRef = useRef<number[]>([]);
  const [isCameraReady, setIsCameraReady] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [recordingSeconds, setRecordingSeconds] = useState(0);
  const [analysisStage, setAnalysisStage] = useState<"idle" | "uploading" | "analyzing" | "result">("idle");
  const [pendingClip, setPendingClip] = useState<{ blob: Blob; filename: string; previewUrl: string; mediaType: string } | null>(null);
  const [retainEvidence, setRetainEvidence] = useState(false);
  const [error, setError] = useState("");
  const maxRecordingSeconds = clampRecordingSeconds(import.meta.env.VITE_MAX_RECORDING_SECONDS);
  const canRetainEvidence = Boolean(accessToken && capabilities?.evidence_retention_enabled);

  const stageLabel = useMemo(() => {
    if (analysisStage === "uploading") return "Uploading clip";
    if (analysisStage === "analyzing") return "Analysis in progress";
    if (analysisStage === "result") return "Preparing result";
    return "";
  }, [analysisStage]);

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      if (countdownTimerRef.current) window.clearInterval(countdownTimerRef.current);
      analysisTimersRef.current.forEach((timer) => window.clearTimeout(timer));
    };
  }, []);

  useEffect(() => {
    return () => {
      if (pendingClip) URL.revokeObjectURL(pendingClip.previewUrl);
    };
  }, [pendingClip]);

  useEffect(() => {
    if (!isRecording) return;
    const interval = window.setInterval(() => {
      setRecordingSeconds((seconds) => {
        const next = seconds + 1;
        if (next >= maxRecordingSeconds) {
          window.setTimeout(stopRecording, 0);
        }
        return next;
      });
    }, 1000);
    return () => window.clearInterval(interval);
  }, [isRecording, maxRecordingSeconds]);

  async function startCamera() {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "environment" },
        audio: false,
      });
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setIsCameraReady(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Camera permission was blocked.");
    }
  }

  function beginCountdown() {
    if (!streamRef.current) return;
    setError("");
    setCountdown(3);
    if (countdownTimerRef.current) window.clearInterval(countdownTimerRef.current);
    countdownTimerRef.current = window.setInterval(() => {
      setCountdown((current) => {
        if (current <= 1) {
          if (countdownTimerRef.current) window.clearInterval(countdownTimerRef.current);
          countdownTimerRef.current = null;
          startRecording();
          return 0;
        }
        return current - 1;
      });
    }, 1000);
  }

  function startRecording() {
    if (!streamRef.current) return;
    if (typeof MediaRecorder === "undefined") {
      setError("This browser cannot record from the camera. Upload a saved clip instead.");
      return;
    }
    chunksRef.current = [];
    const selectedFormat = selectRecordingFormat();
    if (!selectedFormat) {
      setError("Camera recording is not supported in this browser format. Upload an MP4, MOV, or WebM clip instead.");
      return;
    }
    const recorder = new MediaRecorder(streamRef.current, { mimeType: selectedFormat.mimeType });
    recorderRef.current = recorder;
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data);
    };
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: selectedFormat.mimeType });
      setPendingClip({
        blob,
        filename: `smart-cricket-camera-shot-${Date.now()}.${selectedFormat.extension}`,
        previewUrl: URL.createObjectURL(blob),
        mediaType: selectedFormat.mimeType,
      });
    };
    recorder.start();
    setRecordingSeconds(0);
    setIsRecording(true);
  }

  function stopRecording() {
    if (recorderRef.current?.state === "recording") {
      recorderRef.current.stop();
    }
    setIsRecording(false);
  }

  async function submitBlob(blob: Blob, filename: string) {
    setIsAnalyzing(true);
    setError("");
    setAnalysisStage("uploading");
    analysisTimersRef.current.forEach((timer) => window.clearTimeout(timer));
    analysisTimersRef.current = [
      window.setTimeout(() => setAnalysisStage("analyzing"), 350),
    ];
    try {
      const result = await analyzeVideo(blob, filename, accessToken, canRetainEvidence && retainEvidence);
      setAnalysisStage("result");
      await onResult(result, filename);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed.");
    } finally {
      analysisTimersRef.current.forEach((timer) => window.clearTimeout(timer));
      analysisTimersRef.current = [];
      setIsAnalyzing(false);
      setAnalysisStage("idle");
    }
  }

  async function submitPendingClip() {
    if (!pendingClip) return;
    await submitBlob(pendingClip.blob, pendingClip.filename);
    URL.revokeObjectURL(pendingClip.previewUrl);
    setPendingClip(null);
  }

  function retakeClip() {
    if (pendingClip) URL.revokeObjectURL(pendingClip.previewUrl);
    setPendingClip(null);
    setError("");
    setRetainEvidence(false);
  }

  useEffect(() => {
    if (!canRetainEvidence && retainEvidence) {
      setRetainEvidence(false);
    }
  }, [canRetainEvidence, retainEvidence]);

  async function uploadFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (pendingClip) URL.revokeObjectURL(pendingClip.previewUrl);
    setPendingClip({
      blob: file,
      filename: file.name,
      previewUrl: URL.createObjectURL(file),
      mediaType: file.type || "application/octet-stream",
    });
    event.target.value = "";
  }

  return (
    <section className="camera-panel" aria-labelledby="camera-title">
      <div className="panel-heading">
        <div>
          <h2 id="camera-title">Live shot analysis</h2>
          <p>Record one short batting motion in landscape if possible, or upload MP4, MOV, or WebM. Keep clips under 20 seconds and 250 MB.</p>
        </div>
        <span className={isRecording ? "status-pill recording" : "status-pill"}>{isRecording ? "Recording" : "Ready"}</span>
      </div>

      <div className="camera-window">
        <video ref={videoRef} autoPlay muted playsInline aria-label="Camera preview" />
        <div className="framing-guide" aria-hidden="true">
          <span />
          <span />
        </div>
        {!isCameraReady && (
          <div className="camera-empty">
            <UserRoundCheck size={34} aria-hidden="true" />
            <p>Fit the full body, bat path, and front foot inside the guide.</p>
          </div>
        )}
        {countdown > 0 && <div className="countdown-overlay" aria-live="assertive">{countdown}</div>}
        {isRecording && (
          <div className="recording-clock" aria-live="polite">
            <Clock3 size={16} aria-hidden="true" />
            {recordingSeconds}s / {maxRecordingSeconds}s
          </div>
        )}
        {isAnalyzing && (
          <div className="analysis-overlay" aria-live="polite">
            <strong>{stageLabel}</strong>
            <span>Keep this tab open while the server checks pose quality and model confidence.</span>
          </div>
        )}
      </div>

      <div className="quality-guidance" aria-label="Recording guidance">
        <span>Full body visible</span>
        <span>Side-on batting angle</span>
        <span>One shot per clip</span>
        <span>Bright, steady camera</span>
      </div>

      {pendingClip && (
        <div className="review-strip">
          <video src={pendingClip.previewUrl} controls aria-label="Recorded shot preview" />
          <div>
            <strong>Review this take</strong>
            <span>{pendingClip.filename} ({pendingClip.mediaType || "video"}) is ready. Submit it for model analysis or retake before sending.</span>
          </div>
        </div>
      )}

      <label className="consent-card" id="retention-consent">
        <input
          type="checkbox"
          checked={retainEvidence}
          disabled={isAnalyzing || !canRetainEvidence}
          onChange={(event) => setRetainEvidence(event.target.checked)}
        />
        <span>
          {capabilities?.model_improvement_enabled === false
            ? "Model-improvement participation is disabled in this environment, so clips are not retained."
            : accessToken
              ? "Keep this clip securely for human-reviewed model improvement. This must be selected before analysis; no automatic retraining occurs."
              : "Sign in to retain clip evidence for human-reviewed model improvement."}
        </span>
      </label>

      <div className="camera-actions">
        <button type="button" className="primary-action compact" onClick={startCamera} disabled={isCameraReady || isAnalyzing}>
          <Play size={17} aria-hidden="true" />
          Start analysis
        </button>
        <button type="button" className="secondary-action compact" onClick={beginCountdown} disabled={!isCameraReady || isRecording || isAnalyzing || Boolean(pendingClip) || countdown > 0}>
          <Camera size={17} aria-hidden="true" />
          Record shot
        </button>
        <button type="button" className="danger-action compact" onClick={stopRecording} disabled={!isRecording}>
          <CircleStop size={17} aria-hidden="true" />
          Stop
        </button>
        <button type="button" className="primary-action compact" onClick={submitPendingClip} disabled={!pendingClip || isAnalyzing}>
          <Upload size={17} aria-hidden="true" />
          Analyze clip
        </button>
        <button type="button" className="secondary-action compact" onClick={retakeClip} disabled={!pendingClip || isAnalyzing}>
          <RotateCcw size={17} aria-hidden="true" />
          Retake
        </button>
        <label className="file-action">
          <Upload size={17} aria-hidden="true" />
          Upload clip
          <input type="file" accept="video/mp4,video/quicktime,video/webm,video/x-matroska" onChange={uploadFile} />
        </label>
        <button type="button" className="ghost-action compact" onClick={() => setError("")} disabled={!error}>
          <RotateCcw size={17} aria-hidden="true" />
          Clear
        </button>
      </div>

      {error && <p className="error-banner">{error}</p>}
    </section>
  );
}
