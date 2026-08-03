import { useEffect, useRef, useState } from "react";
import { Camera, CircleStop, Play, RotateCcw, Upload } from "lucide-react";
import { analyzeVideo } from "../lib/api";
import type { AnalysisResponse } from "../types";

type CameraAnalysisProps = {
  onResult: (result: AnalysisResponse, sourceName: string) => Promise<void>;
  accessToken?: string;
};

export function CameraAnalysis({ onResult, accessToken }: CameraAnalysisProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<BlobPart[]>([]);
  const [isCameraReady, setIsCameraReady] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [pendingClip, setPendingClip] = useState<{ blob: Blob; filename: string; previewUrl: string } | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((track) => track.stop());
      if (pendingClip) URL.revokeObjectURL(pendingClip.previewUrl);
    };
  }, [pendingClip]);

  async function startCamera() {
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: "environment" },
        audio: false,
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setIsCameraReady(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Camera permission was blocked.");
    }
  }

  function startRecording() {
    if (!streamRef.current) return;
    setError("");
    chunksRef.current = [];
    const mimeType = MediaRecorder.isTypeSupported("video/webm;codecs=vp9")
      ? "video/webm;codecs=vp9"
      : "video/webm";
    const recorder = new MediaRecorder(streamRef.current, { mimeType });
    recorderRef.current = recorder;
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data);
    };
    recorder.onstop = () => {
      const blob = new Blob(chunksRef.current, { type: "video/webm" });
      if (pendingClip) URL.revokeObjectURL(pendingClip.previewUrl);
      setPendingClip({
        blob,
        filename: "smart-cricket-camera-shot.webm",
        previewUrl: URL.createObjectURL(blob),
      });
    };
    recorder.start();
    setIsRecording(true);
  }

  function stopRecording() {
    recorderRef.current?.stop();
    setIsRecording(false);
  }

  async function submitBlob(blob: Blob, filename: string) {
    setIsAnalyzing(true);
    setError("");
    try {
      const result = await analyzeVideo(blob, filename, accessToken);
      await onResult(result, filename);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed.");
    } finally {
      setIsAnalyzing(false);
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
  }

  async function uploadFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    await submitBlob(file, file.name);
    event.target.value = "";
  }

  return (
    <section className="camera-panel" aria-labelledby="camera-title">
      <div className="panel-heading">
        <div>
          <h2 id="camera-title">Live shot analysis</h2>
          <p>Open the camera, record one batting motion, review the clip, and submit only the take you want analyzed.</p>
        </div>
        <span className={isRecording ? "status-pill recording" : "status-pill"}>{isRecording ? "Recording" : "Ready"}</span>
      </div>

      <div className="camera-window">
        <video ref={videoRef} autoPlay muted playsInline aria-label="Camera preview" />
        {!isCameraReady && (
          <div className="camera-empty">
            <Camera size={34} aria-hidden="true" />
            <p>Camera preview appears here.</p>
          </div>
        )}
        {isAnalyzing && <div className="analysis-overlay">Analyzing movement...</div>}
      </div>

      {pendingClip && (
        <div className="review-strip">
          <video src={pendingClip.previewUrl} controls aria-label="Recorded shot preview" />
          <div>
            <strong>Review this take</strong>
            <span>Submit it for model analysis or retake before sending.</span>
          </div>
        </div>
      )}

      <div className="camera-actions">
        <button type="button" className="primary-action compact" onClick={startCamera} disabled={isCameraReady || isAnalyzing}>
          <Play size={17} aria-hidden="true" />
          Start analysis
        </button>
        <button type="button" className="secondary-action compact" onClick={startRecording} disabled={!isCameraReady || isRecording || isAnalyzing || Boolean(pendingClip)}>
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
