'use client';

import { FilesetResolver, PoseLandmarker, type NormalizedLandmark } from '@mediapipe/tasks-vision';

export type PoseLandmark = {
  x: number;
  y: number;
  visibility: number;
};

const WASM_BASE = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21/wasm';
const MODEL_URL =
  'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task';

export function toPoseLandmarks(landmarks: NormalizedLandmark[] | undefined): PoseLandmark[] {
  if (!landmarks?.length) return [];
  return landmarks.map((point) => ({
    x: point.x,
    y: point.y,
    visibility: point.visibility ?? 0,
  }));
}

export class LivePoseDetector {
  private landmarker: PoseLandmarker | null = null;
  private initPromise: Promise<void> | null = null;
  private lastTimestamp = -1;

  async init(): Promise<void> {
    if (this.landmarker) return;
    if (this.initPromise) {
      await this.initPromise;
      return;
    }
    this.initPromise = (async () => {
      const vision = await FilesetResolver.forVisionTasks(WASM_BASE);
      const options = {
        baseOptions: {
          modelAssetPath: MODEL_URL,
        },
        runningMode: 'VIDEO' as const,
        numPoses: 1,
      };
      try {
        this.landmarker = await PoseLandmarker.createFromOptions(vision, {
          ...options,
          baseOptions: { ...options.baseOptions, delegate: 'GPU' },
        });
      } catch {
        this.landmarker = await PoseLandmarker.createFromOptions(vision, {
          ...options,
          baseOptions: { ...options.baseOptions, delegate: 'CPU' },
        });
      }
    })();
    await this.initPromise;
  }

  detect(video: HTMLVideoElement, timestampMs: number): PoseLandmark[] {
    if (!this.landmarker || video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA) {
      return [];
    }
    if (video.videoWidth <= 0 || video.videoHeight <= 0) {
      return [];
    }
    if (timestampMs <= this.lastTimestamp) {
      timestampMs = this.lastTimestamp + 1;
    }
    this.lastTimestamp = timestampMs;
    const result = this.landmarker.detectForVideo(video, timestampMs);
    return toPoseLandmarks(result.landmarks[0]);
  }

  close(): void {
    this.landmarker?.close();
    this.landmarker = null;
    this.initPromise = null;
    this.lastTimestamp = -1;
  }
}

/** Map normalized pose coords to a container using the same object-cover layout as the video. */
export function getObjectCoverRenderRect(
  videoWidth: number,
  videoHeight: number,
  containerWidth: number,
  containerHeight: number
): { offsetX: number; offsetY: number; renderWidth: number; renderHeight: number } {
  if (videoWidth <= 0 || videoHeight <= 0 || containerWidth <= 0 || containerHeight <= 0) {
    return { offsetX: 0, offsetY: 0, renderWidth: containerWidth, renderHeight: containerHeight };
  }
  const videoAspect = videoWidth / videoHeight;
  const containerAspect = containerWidth / containerHeight;
  if (videoAspect > containerAspect) {
    const renderHeight = containerHeight;
    const renderWidth = containerHeight * videoAspect;
    return {
      renderWidth,
      renderHeight,
      offsetX: (containerWidth - renderWidth) / 2,
      offsetY: 0,
    };
  }
  const renderWidth = containerWidth;
  const renderHeight = containerWidth / videoAspect;
  return {
    renderWidth,
    renderHeight,
    offsetX: 0,
    offsetY: (containerHeight - renderHeight) / 2,
  };
}

export const POSE_CONNECTIONS: ReadonlyArray<readonly [number, number]> = [
  [11, 12],
  [11, 13],
  [13, 15],
  [12, 14],
  [14, 16],
  [11, 23],
  [12, 24],
  [23, 24],
  [23, 25],
  [25, 27],
  [24, 26],
  [26, 28],
];
