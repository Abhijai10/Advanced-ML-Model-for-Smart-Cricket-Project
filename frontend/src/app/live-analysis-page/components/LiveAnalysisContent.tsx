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

function buildClassAccuracyData(): ClassAccuracyItem[] { return []; }

export default function LiveAnalysisContent() {
  const [isRecording, setIsRecording] = useState(false);
  const [shots, setShots] = useState<DetectedShot[]>([]);
  const [currentShot, setCurrentShot] = useState<DetectedShot | null>(null);
  const [sessionSeconds, setSessionSeconds] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopSession = useCallback(() => {
    setIsRecording(false);
    if (intervalRef.current) clearInterval(intervalRef.current);
    toast.success(`Session ended — ${shots.length} completed analyses`);
  }, [shots.length]);

  const startSession = useCallback(() => {
    setIsRecording(true);
    setShots([]);
    setCurrentShot(null);
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
  const classAccuracyData = buildClassAccuracyData();

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

            <CameraFeed isRecording={isRecording} currentShot={currentShot} />
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
          <ClassAccuracyChart data={classAccuracyData} />
        </div>

      </div>
    </div>
  );
}
