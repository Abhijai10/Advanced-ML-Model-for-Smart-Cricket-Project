'use client';

import React from 'react';

// BACKEND INTEGRATION POINT: Receive from WebSocket/API
// { shotName, confidence, sequenceId } → update this component's props
export interface ModelOutputCardProps {
  shotName: string | null;
  confidence: number | null; // 0–1
  sequenceId: string | null;
}

export default function ModelOutputCard({
  shotName,
  confidence,
  sequenceId,
}: ModelOutputCardProps) {
  const pct = confidence !== null ? Math.round(confidence * 100) : 0;

  return (
    <div className="glass-card-solid rounded-2xl p-5 border border-border">
      {/* Header row */}
      <div className="flex items-center justify-between mb-5">
        <span className="text-xs font-semibold tracking-widest uppercase text-muted-foreground">
          Current Model Output
        </span>
        {confidence !== null && (
          <div className="flex items-center gap-2 bg-muted/40 border border-border rounded-full px-3 py-1">
            <span
              className="w-2 h-2 rounded-full bg-emerald-400"
              style={{ boxShadow: '0 0 6px #34d399' }}
            />
            <span className="text-xs font-semibold text-foreground font-mono-data">
              {pct}% confident
            </span>
          </div>
        )}
      </div>

      {/* Shot name */}
      <div className="mb-4">
        {shotName ? (
          <>
            <h2 className="text-4xl font-bold text-foreground mb-2">{shotName}</h2>
            {sequenceId && (
              <p className="text-sm text-muted-foreground">
                Detected from motion sequence{' '}
                <span className="text-accent font-mono-data font-semibold">{sequenceId}</span>
              </p>
            )}
          </>
        ) : (
          <p className="text-sm text-muted-foreground py-4">Waiting for detection…</p>
        )}
      </div>

      {/* Confidence gradient bar */}
      <div className="mt-4">
        <div className="h-2 bg-muted/50 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700 ease-out"
            style={{
              width: `${pct}%`,
              background:
                'linear-gradient(90deg, #818CF8 0%, #A78BFA 40%, #C084FC 70%, #E879F9 100%)',
              boxShadow: pct > 50 ? '0 0 12px rgba(167, 139, 250, 0.4)' : 'none',
            }}
          />
        </div>
        <div className="flex items-center justify-between mt-1.5">
          <span className="text-xs font-semibold tracking-widest uppercase text-muted-foreground">
            Confidence
          </span>
          <span className="font-mono-data text-xs font-bold text-foreground">
            {pct > 0 ? pct : '—'}
          </span>
        </div>
      </div>
    </div>
  );
}
