'use client';

import React, { useRef, useEffect } from 'react';
import ShotBadge, { ShotType } from '@/components/ui/ShotBadge';
import { MessageSquare, Zap, BarChart2, AlertTriangle } from 'lucide-react';
import type { DetectedShot } from './LiveAnalysisContent';

interface ShotDetectionPanelProps {
  currentShot: DetectedShot | null;
  shots: DetectedShot[];
  isRecording: boolean;
}

const SHOT_DISPLAY: Record<ShotType, { label: string; icon: string; colorClass: string }> = {
  cover_drive: { label: 'Cover Drive', icon: '🏏', colorClass: 'text-violet-300 bg-violet-400/10 border-violet-400/30' },
  defensive: { label: 'Defensive Shot', icon: '🛡️', colorClass: 'text-emerald-300 bg-emerald-400/10 border-emerald-400/30' },
  pull: { label: 'Pull Shot', icon: '💥', colorClass: 'text-yellow-300 bg-yellow-400/10 border-yellow-400/30' },
  sweep: { label: 'Sweep Shot', icon: '🌀', colorClass: 'text-red-300 bg-red-400/10 border-red-400/30' },
};

export default function ShotDetectionPanel({
  currentShot,
  shots,
  isRecording,
}: ShotDetectionPanelProps) {
  const feedRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [shots.length]);

  const recentShots = shots.slice(-12).reverse();

  return (
    <div className="flex flex-col gap-4 h-full">
      {/* Current detection card */}
      <div className="glass-card-solid rounded-xl p-5">
        <div className="flex items-center gap-2 mb-3">
          <Zap size={15} className="text-accent" />
          <span className="text-xs font-semibold tracking-widest uppercase text-muted-foreground">
            Current Detection
          </span>
        </div>

        {currentShot && isRecording ? (
          <div className="fade-in-up">
            <div
              className={`flex items-center gap-3 rounded-xl px-4 py-3 border mb-3 ${
                SHOT_DISPLAY[currentShot.shot].colorClass
              }`}
            >
              <span className="text-2xl">{SHOT_DISPLAY[currentShot.shot].icon}</span>
              <div>
                <p className="text-base font-bold text-foreground">
                  {SHOT_DISPLAY[currentShot.shot].label}
                </p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xs text-muted-foreground">Confidence</span>
                  <span className="font-mono-data text-xs font-bold text-accent">
                    {Math.round(currentShot.confidence * 100)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Confidence bar */}
            <div className="mb-3">
              <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full accuracy-bar"
                  style={{ width: `${Math.round(currentShot.confidence * 100)}%` }}
                />
              </div>
            </div>

            {/* Accuracy badge */}
            <div className={`inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full ${
              currentShot.accurate
                ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/25' :'bg-red-500/15 text-red-400 border border-red-500/25'
            }`}>
              {currentShot.accurate ? '✓ Accurate' : '✗ Needs work'}
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center py-6 text-center">
            <div className="w-12 h-12 rounded-xl bg-muted/40 flex items-center justify-center mb-3">
              {isRecording ? (
                <div className="w-4 h-4 rounded-full bg-primary/40 pulse-ring" />
              ) : (
                <BarChart2 size={20} className="text-muted-foreground" />
              )}
            </div>
            <p className="text-sm text-muted-foreground">
              {isRecording ? 'Waiting for shot…' : 'Start session to begin detection'}
            </p>
          </div>
        )}
      </div>

      {/* Feedback */}
      {currentShot && isRecording && (
        <div className="glass-card-solid rounded-xl p-4 fade-in-up">
          <div className="flex items-center gap-2 mb-2">
            <MessageSquare size={14} className="text-accent" />
            <span className="text-xs font-semibold tracking-widest uppercase text-muted-foreground">
              ML Feedback
            </span>
          </div>
          <p className="text-sm text-foreground leading-relaxed">
            {currentShot.feedback}
          </p>
        </div>
      )}

      {/* Shot feed */}
      <div className="glass-card-solid rounded-xl p-4 flex-1 flex flex-col">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <BarChart2 size={14} className="text-accent" />
            <span className="text-xs font-semibold tracking-widest uppercase text-muted-foreground">
              Shot Log
            </span>
          </div>
          <span className="font-mono-data text-xs text-muted-foreground">
            {shots.length} total
          </span>
        </div>

        {shots.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <AlertTriangle size={20} className="text-muted-foreground mb-2" />
            <p className="text-xs text-muted-foreground">
              No shots logged yet. Start a session.
            </p>
          </div>
        ) : (
          <div
            ref={feedRef}
            className="flex-1 overflow-y-auto scrollbar-thin space-y-2"
            style={{ maxHeight: '220px' }}
          >
            {recentShots.map((shot, idx) => (
              <div
                key={shot.id}
                className="flex items-center justify-between gap-2 py-1.5 border-b border-border/50 last:border-0"
                style={{ opacity: 1 - idx * 0.06 }}
              >
                <ShotBadge shot={shot.shot as ShotType} size="sm" />
                <span className="font-mono-data text-xs text-muted-foreground">
                  {Math.round(shot.confidence * 100)}%
                </span>
                <span
                  className={`text-xs font-semibold ${
                    shot.accurate ? 'text-emerald-400' : 'text-red-400'
                  }`}
                >
                  {shot.accurate ? '✓' : '✗'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}