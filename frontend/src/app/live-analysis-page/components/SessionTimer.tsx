'use client';

import React from 'react';
import { Timer } from 'lucide-react';

interface SessionTimerProps {
  seconds: number;
  isRunning: boolean;
}

function formatTime(s: number): string {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
}

export default function SessionTimer({ seconds, isRunning }: SessionTimerProps) {
  return (
    <div
      className={`flex items-center gap-2 px-3 py-2 rounded-xl border text-sm font-semibold font-mono-data ${
        isRunning ? 'status-recording' : 'border-border text-muted-foreground bg-muted/30'
      }`}
    >
      <Timer size={14} />
      {formatTime(seconds)}
    </div>
  );
}
