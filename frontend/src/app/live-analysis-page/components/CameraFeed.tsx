'use client';

import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Camera, CameraOff, Maximize2, Info } from 'lucide-react';
import type { DetectedShot } from './LiveAnalysisContent';
import {
  LivePoseDetector,
  POSE_CONNECTIONS,
  getObjectCoverRenderRect,
  type PoseLandmark,
} from '@/lib/livePose';

interface CameraFeedProps {
  isRecording: boolean;
  currentShot: DetectedShot | null;
  landmarks?: PoseLandmark[];
  onRecordingComplete: (clip: Blob, filename: string) => void;
  onRecordingError: (message: string) => void;
}

const SHOT_LABEL_MAP: Record<string, string> = {
  cover_drive: 'Cover Drive',
  defensive: 'Defensive Shot',
  pull: 'Pull Shot',
  sweep: 'Sweep Shot',
};

const SHOT_COLOR_MAP: Record<string, string> = {
  cover_drive: 'border-violet-400 text-violet-300 bg-violet-400/10',
  defensive: 'border-emerald-400 text-emerald-300 bg-emerald-400/10',
  pull: 'border-yellow-400 text-yellow-300 bg-yellow-400/10',
  sweep: 'border-red-400 text-red-300 bg-red-400/10',
};

const MIRROR_STYLE: React.CSSProperties = { transform: 'scaleX(-1)' };

function drawPoseOverlay(
  context: CanvasRenderingContext2D,
  landmarks: PoseLandmark[],
  video: HTMLVideoElement,
  canvas: HTMLCanvasElement
): void {
  const { width, height } = canvas;
  context.clearRect(0, 0, width, height);
  if (!landmarks.length || !width || !height) return;

  const rect = getObjectCoverRenderRect(video.videoWidth, video.videoHeight, width, height);

  const toCanvas = (point: PoseLandmark) => ({
    x: rect.offsetX + point.x * rect.renderWidth,
    y: rect.offsetY + point.y * rect.renderHeight,
    visibility: point.visibility,
  });

  context.strokeStyle = 'rgba(147, 197, 253, 0.9)';
  context.lineWidth = 4;
  POSE_CONNECTIONS.forEach(([from, to]) => {
    const a = landmarks[from];
    const b = landmarks[to];
    if (!a || !b || a.visibility < 0.3 || b.visibility < 0.3) return;
    const start = toCanvas(a);
    const end = toCanvas(b);
    context.beginPath();
    context.moveTo(start.x, start.y);
    context.lineTo(end.x, end.y);
    context.stroke();
  });

  context.fillStyle = 'rgba(167, 139, 250, 0.95)';
  landmarks.forEach((point) => {
    if (point.visibility < 0.3) return;
    const mapped = toCanvas(point);
    context.beginPath();
      point.x * width,
  point.y * height,
  5,context.arc(mapped.x, mapped.y, 3, 0, Math.PI * 2);
    context.fill();
  });
}

export default function CameraFeed({
  isRecording,
  currentShot,
  landmarks = [],
  onRecordingComplete,
  onRecordingError,
}: CameraFeedProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const poseDetectorRef = useRef<LivePoseDetector | null>(null);
  const liveLandmarksRef = useRef<PoseLandmark[]>([]);
  const poseFrameRef = useRef<number | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [shotFlash, setShotFlash] = useState(false);
  const [videoReady, setVideoReady] = useState(false);
  const [canvasSize, setCanvasSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    if (currentShot) {
      setShotFlash(true);
      const t = window.setTimeout(() => setShotFlash(false), 400);
      return () => window.clearTimeout(t);
    }
  }, [currentShot]);

  const syncCanvasSize = useCallback(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;
    const width = Math.round(container.clientWidth);
    const height = Math.round(container.clientHeight);
    if (width <= 0 || height <= 0) return;
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
    }
    setCanvasSize((previous) =>
      previous.width === width && previous.height === height ? previous : { width, height }
    );
  }, []);

  const renderOverlay = useCallback((overlayLandmarks: PoseLandmark[]) => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;
    const context = canvas.getContext('2d');
    if (!context) return;
    drawPoseOverlay(context, overlayLandmarks, video, canvas);
  }, []);

  const stopPoseLoop = useCallback(() => {
    if (poseFrameRef.current !== null) {
      cancelAnimationFrame(poseFrameRef.current);
      poseFrameRef.current = null;
    }
  }, []);

  const startPoseLoop = useCallback(() => {
    stopPoseLoop();
    const video = videoRef.current;
    if (!video || !cameraActive) return;

    const tick = async () => {
      const activeVideo = videoRef.current;
      if (!activeVideo || !cameraActive) return;

      if (!poseDetectorRef.current) {
        poseDetectorRef.current = new LivePoseDetector();
        try {
          await poseDetectorRef.current.init();
        } catch {
          poseDetectorRef.current?.close();
          poseDetectorRef.current = null;
          poseFrameRef.current = requestAnimationFrame(tick);
          return;
        }
      }

      const detector = poseDetectorRef.current;
      if (activeVideo.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
        liveLandmarksRef.current = detector.detect(activeVideo, performance.now());
      }

      const overlayLandmarks =
        landmarks.length > 0 && currentShot ? landmarks : liveLandmarksRef.current;
      renderOverlay(overlayLandmarks);
      poseFrameRef.current = requestAnimationFrame(tick);
    };

    poseFrameRef.current = requestAnimationFrame(tick);
  }, [cameraActive, currentShot, landmarks, renderOverlay, stopPoseLoop]);

  const startCamera = async (): Promise<MediaStream | null> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        streamRef.current = stream;
        setCameraActive(true);
        setCameraError(null);
      }
      return stream;
    } catch {
      setCameraError('Camera access denied. Grant permission to enable live feed.');
      return null;
    }
  };

  const stopCamera = () => {
    stopPoseLoop();
    poseDetectorRef.current?.close();
    poseDetectorRef.current = null;
    liveLandmarksRef.current = [];
    if (videoRef.current?.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach((track) => track.stop());
      videoRef.current.srcObject = null;
    }
    streamRef.current = null;
    setCameraActive(false);
    setVideoReady(false);
    const canvas = canvasRef.current;
    canvas?.getContext('2d')?.clearRect(0, 0, canvas.width, canvas.height);
  };

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const stream = video.srcObject as MediaStream | null;
    if (isRecording && !stream) {
      void startCamera().then((started) => {
        if (!started) onRecordingError('Enable the camera before starting a session.');
      });
      return;
    }
    if (isRecording && stream && !recorderRef.current) {
      const mimeType = MediaRecorder.isTypeSupported('video/webm;codecs=vp8,opus')
        ? 'video/webm;codecs=vp8,opus'
        : 'video/webm';
      const recorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunksRef.current.push(event.data);
      };
      recorder.onstop = () => {
        const clip = new Blob(chunksRef.current, { type: recorder.mimeType || 'video/webm' });
        recorderRef.current = null;
        if (clip.size) onRecordingComplete(clip, `smart-cricket-${Date.now()}.webm`);
      };
      recorder.onerror = () => onRecordingError('Camera recording could not be started.');
      recorderRef.current = recorder;
      recorder.start();
    } else if (!isRecording) {
      const recorder = recorderRef.current;
      if (recorder?.state !== 'inactive') recorder?.stop();
    }
  }, [isRecording, cameraActive, onRecordingComplete, onRecordingError]);

  useEffect(() => {
    const video = videoRef.current;
    const container = containerRef.current;
    if (!video || !container) return;

    const handleReady = () => {
      syncCanvasSize();
      setVideoReady(video.videoWidth > 0 && video.videoHeight > 0);
    };

    video.addEventListener('loadedmetadata', handleReady);
    video.addEventListener('loadeddata', handleReady);
    video.addEventListener('resize', handleReady);

    const resizeObserver = new ResizeObserver(handleReady);
    resizeObserver.observe(container);

    handleReady();
    return () => {
      video.removeEventListener('loadedmetadata', handleReady);
      video.removeEventListener('loadeddata', handleReady);
      video.removeEventListener('resize', handleReady);
      resizeObserver.disconnect();
    };
  }, [cameraActive, syncCanvasSize]);

  useEffect(() => {
    if (cameraActive && videoReady) {
      startPoseLoop();
      return stopPoseLoop;
    }
    stopPoseLoop();
    return undefined;
  }, [cameraActive, videoReady, startPoseLoop, stopPoseLoop]);

  useEffect(() => {
    if (!cameraActive) return;
    const overlayLandmarks =
      landmarks.length > 0 && currentShot ? landmarks : liveLandmarksRef.current;
    renderOverlay(overlayLandmarks);
  }, [cameraActive, canvasSize, currentShot, landmarks, renderOverlay]);

  useEffect(() => {
    return () => {
      stopPoseLoop();
      poseDetectorRef.current?.close();
      poseDetectorRef.current = null;
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    };
  }, [stopPoseLoop]);

  return (
    <div
      ref={containerRef}
      className="relative glass-card-solid rounded-2xl overflow-hidden"
      style={{ minHeight: '420px' }}
    >
      {/* Scanline overlay */}
      <div className="absolute inset-0 camera-scanline pointer-events-none z-10 opacity-60" />

      {/* Recording border glow */}
      {isRecording && (
        <div className="absolute inset-0 rounded-2xl border-2 border-red-500/50 z-20 pointer-events-none" />
      )}

      {/* Video element */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="w-full h-full object-cover"
        style={{ minHeight: '420px', display: cameraActive ? 'block' : 'none', ...MIRROR_STYLE }}
      />
      {cameraActive && (
        <canvas
          ref={canvasRef}
          className="absolute inset-0 z-20 pointer-events-none w-full h-full object-cover"
          style={MIRROR_STYLE}
          aria-hidden="true"
        />
      )}

      {/* Placeholder when camera off */}
      {!cameraActive && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-gradient-to-br from-muted/30 to-background">
          <div className="w-20 h-20 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center mb-5">
            {cameraError ? (
              <CameraOff size={32} className="text-red-400" />
            ) : (
              <Camera size={32} className="text-accent" />
            )}
          </div>
          <p className="text-base font-semibold text-foreground mb-2">
            {cameraError ? 'Camera Unavailable' : 'Camera Not Started'}
          </p>
          <p className="text-sm text-muted-foreground text-center max-w-xs mb-6 leading-relaxed">
            {cameraError ||
              'Enable your camera to see the live feed. The ML model analyses each frame to detect batting shots.'}
          </p>
          {!cameraError && (
            <button
              onClick={startCamera}
              className="btn-primary flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold"
            >
              <Camera size={15} />
              Enable Camera
            </button>
          )}
          {cameraError && (
            <div className="flex items-start gap-2 bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 max-w-xs">
              <Info size={14} className="text-red-400 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-red-300">{cameraError}</p>
            </div>
          )}
        </div>
      )}

      {/* Camera active controls */}
      {cameraActive && (
        <div className="absolute top-4 right-4 z-30 flex items-center gap-2">
          <button
            onClick={stopCamera}
            className="w-8 h-8 rounded-lg bg-background/70 backdrop-blur border border-border flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Stop camera"
          >
            <CameraOff size={14} />
          </button>
          <button
            className="w-8 h-8 rounded-lg bg-background/70 backdrop-blur border border-border flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
            aria-label="Fullscreen"
          >
            <Maximize2 size={14} />
          </button>
        </div>
      )}

      {/* Shot flash overlay */}
      {shotFlash && (
        <div className="absolute inset-0 z-25 rounded-2xl pointer-events-none shot-flash" />
      )}

      {/* Current shot overlay — bottom of feed */}
      {currentShot && (
        <div className="absolute bottom-4 left-4 right-4 z-30">
          <div
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl border backdrop-blur-sm text-sm font-semibold fade-in-up ${
              SHOT_COLOR_MAP[currentShot.shot] ?? ''
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-current recording-dot" />
            {SHOT_LABEL_MAP[currentShot.shot]}
            <span className="font-mono-data text-xs opacity-75 ml-1">
              {Math.round(currentShot.confidence * 100)}% conf.
            </span>
          </div>
        </div>
      )}

      {/* Corner markers — viewfinder aesthetic */}
      {isRecording && (
        <>
          <div className="absolute top-4 left-4 w-6 h-6 border-t-2 border-l-2 border-primary/60 rounded-tl z-20" />
          <div className="absolute top-4 right-4 w-6 h-6 border-t-2 border-r-2 border-primary/60 rounded-tr z-20" />
          <div className="absolute bottom-4 left-4 w-6 h-6 border-b-2 border-l-2 border-primary/60 rounded-bl z-20" />
          <div className="absolute bottom-4 right-4 w-6 h-6 border-b-2 border-r-2 border-primary/60 rounded-br z-20" />
        </>
      )}
    </div>
  );
}
