'use client';

import React, { useRef, useEffect, useState } from 'react';
import { Camera, CameraOff, Maximize2, Info } from 'lucide-react';
import type { DetectedShot } from './LiveAnalysisContent';

interface CameraFeedProps {
  isRecording: boolean;
  currentShot: DetectedShot | null;
  landmarks?: { x: number; y: number; visibility: number }[];
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

export default function CameraFeed({ isRecording, currentShot, landmarks = [], onRecordingComplete, onRecordingError }: CameraFeedProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const [cameraActive, setCameraActive] = useState(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [shotFlash, setShotFlash] = useState(false);

  useEffect(() => {
    if (currentShot) {
      setShotFlash(true);
      const t = setTimeout(() => setShotFlash(false), 400);
      return () => clearTimeout(t);
    }
  }, [currentShot?.id]);

  const startCamera = async (): Promise<MediaStream | null> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
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
    if (videoRef.current?.srcObject) {
      const stream = videoRef.current.srcObject as MediaStream;
      stream.getTracks().forEach((t) => t.stop());
      videoRef.current.srcObject = null;
    }
    setCameraActive(false);
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
      recorder.ondataavailable = (event) => { if (event.data.size) chunksRef.current.push(event.data); };
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
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video || !landmarks.length) return;
    const width = video.clientWidth;
    const height = video.clientHeight;
    if (!width || !height) return;
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext('2d');
    if (!context) return;
    const links = [[11, 12], [11, 13], [13, 15], [12, 14], [14, 16], [11, 23], [12, 24], [23, 24], [23, 25], [25, 27], [24, 26], [26, 28]];
    context.clearRect(0, 0, width, height);
    context.strokeStyle = 'rgba(147, 197, 253, 0.9)';
    context.lineWidth = 2;
    links.forEach(([from, to]) => {
      const a = landmarks[from]; const b = landmarks[to];
      if (!a || !b || a.visibility < 0.3 || b.visibility < 0.3) return;
      context.beginPath(); context.moveTo(a.x * width, a.y * height); context.lineTo(b.x * width, b.y * height); context.stroke();
    });
    context.fillStyle = 'rgba(167, 139, 250, 0.95)';
    landmarks.forEach((point) => {
      if (point.visibility < 0.3) return;
      context.beginPath(); context.arc(point.x * width, point.y * height, 3, 0, Math.PI * 2); context.fill();
    });
  }, [landmarks, cameraActive]);

  return (
    <div className="relative glass-card-solid rounded-2xl overflow-hidden" style={{ minHeight: '420px' }}>
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
        style={{ minHeight: '420px', display: cameraActive ? 'block' : 'none' }}
      />
      {cameraActive && <canvas ref={canvasRef} className="absolute inset-0 z-20 pointer-events-none w-full h-full" aria-hidden="true" />}

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
