'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import CameraFeed from './CameraFeed';
import ShotDetectionPanel from './ShotDetectionPanel';
import ShotFrequencyChart from './ShotFrequencyChart';
import ShotAccuracyChart from './ShotAccuracyChart';
import ModelOutputCard from './ModelOutputCard';
import ShotDistributionChart, { ShotDistributionItem } from './ShotDistributionChart';
import ClassAccuracyChart, { ClassAccuracyItem } from './ClassAccuracyChart';
import SessionTimer from './SessionTimer';
import { toast } from 'sonner';
import { Play, Square, RotateCcw, Download } from 'lucide-react';
import { ApiError, createAnalysisJob, getAnalysisJob, getAnalytics } from '@/lib/api';
import { useSmartCricket } from '@/components/SmartCricketProvider';
import { toShotType } from '@/lib/analytics';

export type ShotType = 'cover_drive' | 'defensive' | 'pull' | 'sweep';

export interface DetectedShot {
  id: string;
  shot: ShotType;
  confidence: number;
  timestamp: number;
  feedback: string;
  accurate: boolean | null;
}

export interface ShotFrequencyData {
  shot: string;
  count: number;
  fill: string;
}

export interface ShotAccuracyPoint {
  index: number;
  cover_drive: number;
  defensive: number;
  pull: number;
  sweep: number;
}


function buildFrequencyData(shots: DetectedShot[]): ShotFrequencyData[] {
  const counts: Record<ShotType, number> = {
    cover_drive: 0,
    defensive: 0,
    pull: 0,
    sweep: 0,
  };
  shots.forEach((s) => counts[s.shot]++);
  return [
    { shot: 'Cover Drive', count: counts.cover_drive, fill: 'var(--primary)' },
    { shot: 'Defensive', count: counts.defensive, fill: '#10B981' },
    { shot: 'Pull Shot', count: counts.pull, fill: '#F59E0B' },
    { shot: 'Sweep', count: counts.sweep, fill: '#EF4444' },
  ];
}

function buildAccuracyData(): ShotAccuracyPoint[] { return []; }

function buildDistributionData(shots: DetectedShot[]): ShotDistributionItem[] {
  const counts: Record<ShotType, number> = { cover_drive: 0, defensive: 0, pull: 0, sweep: 0 };
  shots.forEach((s) => counts[s.shot]++);
  return [
    { name: 'Cover drive', value: counts.cover_drive, color: '#93C5FD' },
    { name: 'Defensive shot', value: counts.defensive, color: '#A78BFA' },
    { name: 'Pull shot', value: counts.pull, color: '#6EE7B7' },
    { name: 'Sweep shot', value: counts.sweep, color: '#FCD34D' },
  ];
}

export default function LiveAnalysisContent() {
  const { session, refreshSessions } = useSmartCricket();
  const [isRecording, setIsRecording] = useState(false);
  const [shots, setShots] = useState<DetectedShot[]>([]);
  const [currentShot, setCurrentShot] = useState<DetectedShot | null>(null);
  const [sessionSeconds, setSessionSeconds] = useState(0);
  const [analysisState, setAnalysisState] = useState<'idle' | 'shot_detected' | 'processing' | 'result_ready'>('idle');
  const [analysisMessage, setAnalysisMessage] = useState('');
  const [landmarks, setLandmarks] = useState<{ x: number; y: number; visibility: number }[]>([]);
  const [classAccuracyData, setClassAccuracyData] = useState<ClassAccuracyItem[]>([]);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const token = session?.access_token;
    if (!token) { setClassAccuracyData([]); return; }
    void getAnalytics<{ values: Record<string, number> }>('class-accuracy', token)
      .then(({ values }) => setClassAccuracyData(Object.entries(values).map(([shot, accuracy]) => ({ shot: shot.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()), accuracy }))))
      .catch(() => setClassAccuracyData([]));
  }, [session?.access_token, shots.length]);

  const submitRecording = useCallback(async (clip: Blob, filename: string) => {
    if (!session?.access_token) {
      setAnalysisState('idle');
      toast.error('Sign in before analysing a recording.');
      return;
    }
    try {
      setAnalysisState('shot_detected');
      setAnalysisMessage('Shot detected. Preparing analysis…');
      const queued = await createAnalysisJob(clip, filename, session.access_token);
      setAnalysisState('processing');
      setAnalysisMessage('Analysing your shot…');
      const startedAt = Date.now();
      while (true) {
        const job = await getAnalysisJob(queued.job_id, session.access_token);
        if (job.status === 'completed' && job.result) {
          const shot = toShotType(job.result.predicted_shot);
          if (!shot) throw new ApiError('The model returned an unsupported shot label.');
          const detected: DetectedShot = {
            id: job.job_id,
            shot,
            confidence: job.result.shot_confidence,
            timestamp: Date.now(),
            feedback: job.result.detailed_feedback || job.result.spoken_feedback || 'Analysis completed.',
            accurate: null,
          };
          setShots((previous) => [...previous, detected]);
          setCurrentShot(detected);
          setLandmarks(job.result.landmarks || []);
          setAnalysisState('result_ready');
          setAnalysisMessage('Analysis complete.');
          await refreshSessions();
          toast.success('Shot analysis complete');
          return;
        }
        if (job.status === 'failed') throw new ApiError(job.detail || 'Analysis failed.', job.error_code || undefined);
        if (Date.now() - startedAt > 6000) setAnalysisMessage('Still analysing your shot…');
        await new Promise((resolve) => setTimeout(resolve, 800));
      }
    } catch (error) {
      setAnalysisState('idle');
      setAnalysisMessage('');
      toast.error(error instanceof Error ? error.message : 'Analysis could not be completed.');
    }
  }, [refreshSessions, session?.access_token]);

  const stopSession = useCallback(() => {
    setIsRecording(false);
    if (intervalRef.current) clearInterval(intervalRef.current);
    toast.success(`Session ended — ${shots.length} completed analyses`);
  }, [shots.length]);

  const startSession = useCallback(() => {
    setIsRecording(true);
    setShots([]);
    setCurrentShot(null);
    setLandmarks([]);
    setAnalysisState('idle');
    setSessionSeconds(0);

    intervalRef.current = setInterval(() => {
      setSessionSeconds((s) => s + 1);
    }, 1000);

  }, []);

  const resetSession = useCallback(() => {
    stopSession();
    setShots([]);
    setCurrentShot(null);
    setSessionSeconds(0);
    toast.info('Session reset');
  }, [stopSession]);

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const frequencyData = buildFrequencyData(shots);
  const accuracyData = buildAccuracyData();
  const distributionData = buildDistributionData(shots);
  const resolvedClassAccuracyData = classAccuracyData;

  // Build sequence ID from shot count
  const sequenceId = currentShot ? `#${String(shots.length).padStart(4, '0')}` : null;

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-screen-2xl mx-auto px-6 lg:px-8 xl:px-10 2xl:px-16 py-6">

        {/* Page header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Live Analysis</h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Position your camera to capture the full batting stance
            </p>
          </div>
          <div className="flex items-center gap-2">
            {isRecording && (
              <div className="flex items-center gap-2 status-recording px-3 py-1.5 rounded-full text-xs font-semibold">
                <span className="w-2 h-2 rounded-full bg-red-400 recording-dot" />
                Recording
              </div>
            )}
            {!isRecording && shots.length > 0 && (
              <button
                onClick={() => toast.info('Export feature — connect backend to download session CSV')}
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground border border-border rounded-lg px-3 py-2 transition-colors"
              >
                <Download size={15} />
                Export
              </button>
            )}
          </div>
        </div>

        {/* Main analysis area */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 mb-6">

          {/* Camera feed — 2/3 width */}
          <div className="xl:col-span-2 flex flex-col gap-4">
            {/* Session controls */}
            <div className="flex items-center gap-3">
              {!isRecording ? (
                <button
                  onClick={startSession}
                  className="btn-primary flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold"
                >
                  <Play size={15} fill="currentColor" />
                  Start Session
                </button>
              ) : (
                <button
                  onClick={stopSession}
                  className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30 transition-all"
                >
                  <Square size={15} fill="currentColor" />
                  Stop Session
                </button>
              )}
              <button
                onClick={resetSession}
                className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium text-muted-foreground border border-border hover:text-foreground hover:border-primary/30 transition-all"
              >
                <RotateCcw size={15} />
                Reset
              </button>
              <SessionTimer seconds={sessionSeconds} isRunning={isRecording} />
              <div className="ml-auto flex items-center gap-1.5 text-sm text-muted-foreground">
                <span className="font-mono-data font-bold text-foreground">{shots.length}</span>
                shots detected
              </div>
            </div>

            <CameraFeed
              isRecording={isRecording}
              currentShot={currentShot}
              landmarks={landmarks}
              onRecordingComplete={submitRecording}
              onRecordingError={(message) => { setIsRecording(false); setAnalysisState('idle'); toast.error(message); }}
            />
          </div>

          {/* Right panel — shot detection */}
          <div className="xl:col-span-1">
            <ShotDetectionPanel
              currentShot={currentShot}
              shots={shots}
              isRecording={isRecording}
            />
          </div>
        </div>

        {/* Model Output Card — full width */}
        <div className="mb-5">
          <ModelOutputCard
            shotName={currentShot ? currentShot.shot.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase()) : null}
            confidence={currentShot ? currentShot.confidence : null}
            sequenceId={sequenceId}
          />
        </div>

        {/* Charts row — frequency + accuracy (existing) */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-5 mb-5">
          <ShotFrequencyChart data={frequencyData} totalShots={shots.length} />
          <ShotAccuracyChart data={accuracyData} />
        </div>

        {/* New charts row — distribution + class accuracy */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
          <ShotDistributionChart data={distributionData} isLive={isRecording} />
          <ClassAccuracyChart data={resolvedClassAccuracyData} />
        </div>

      </div>
      {(analysisState === 'shot_detected' || analysisState === 'processing') && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/65 backdrop-blur-sm px-6" role="status">
          <div className="glass-card-solid rounded-2xl p-6 border border-border text-center max-w-sm w-full">
            <div className="mx-auto mb-4 h-9 w-9 rounded-full border-2 border-primary/30 border-t-accent animate-spin" />
            <p className="text-base font-semibold text-foreground">{analysisMessage}</p>
            <p className="mt-1 text-sm text-muted-foreground">You can stay on this page while we process the recording.</p>
          </div>
        </div>
      )}
    </div>
  );
}
