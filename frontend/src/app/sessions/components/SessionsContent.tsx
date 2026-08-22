'use client';

import React, { useState } from 'react';
import ShotBadge, { ShotType } from '@/components/ui/ShotBadge';
import { Clock, BarChart2, ChevronDown, ChevronUp, Filter, Calendar, Target } from 'lucide-react';

export interface Session {
  id: string;
  date: string;
  duration: string;
  totalShots: number;
  accuracy: number | null;
  dominantShot: ShotType;
  shotBreakdown: { shot: ShotType; count: number; accuracy: number | null }[];
  trend: 'up' | 'down' | 'neutral';
  trendValue: string;
  feedback: string;
}

export default function SessionsContent({ sessions = [] }: { sessions?: Session[] }) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | 'good' | 'needs_work'>('all');

  const filtered = sessions.filter((s) => {
    if (filter === 'good') return s.accuracy !== null && s.accuracy >= 75;
    if (filter === 'needs_work') return s.accuracy !== null && s.accuracy < 75;
    return true;
  });

  const avgAccuracy =
    sessions.length > 0
      ? (() => { const known = sessions.filter((s) => s.accuracy !== null); return known.length ? (known.reduce((sum, s) => sum + (s.accuracy || 0), 0) / known.length).toFixed(1) : null; })()
      : null;

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-screen-xl mx-auto px-6 lg:px-8 py-8">

        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-8">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Session History</h1>
            <p className="text-sm text-muted-foreground mt-1">
              {sessions.length} sessions recorded
              {avgAccuracy && (
                <> · avg accuracy <span className="text-foreground font-semibold">{avgAccuracy}%</span></>
              )}
            </p>
          </div>

          {/* Summary stats */}
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Calendar size={14} />
              <span>{sessions.length} total</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Target size={14} />
              <span>{avgAccuracy ? `${avgAccuracy}% avg` : '—'}</span>
            </div>
          </div>
        </div>

        {/* Filter bar */}
        <div className="flex items-center gap-2 mb-6">
          <Filter size={14} className="text-muted-foreground" />
          {(['all', 'good', 'needs_work'] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all duration-150 ${
                filter === f
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted/40 text-muted-foreground hover:text-foreground hover:bg-muted/60'
              }`}
            >
              {f === 'all' ? 'All Sessions' : f === 'good' ? '≥ 75% Accuracy' : '< 75% Accuracy'}
            </button>
          ))}
        </div>

        {/* Sessions list */}
        <div className="flex flex-col gap-3">
          {filtered.length === 0 ? (
            <div className="glass-card-solid rounded-2xl p-12 text-center border border-border">
              <p className="text-muted-foreground text-sm">No sessions match this filter.</p>
            </div>
          ) : (
            filtered.map((session) => (
              <SessionRow
                key={session.id}
                session={session}
                expanded={expandedId === session.id}
                onToggle={() => setExpandedId(expandedId === session.id ? null : session.id)}
              />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function SessionRow({
  session,
  expanded,
  onToggle,
}: {
  session: Session;
  expanded: boolean;
  onToggle: () => void;
}) {
  const trendColor =
    session.trend === 'up' ?'text-emerald-400'
      : session.trend === 'down' ?'text-red-400' :'text-muted-foreground';

  const accuracyColor =
    session.accuracy !== null && session.accuracy >= 75
      ? 'text-emerald-400'
      : session.accuracy !== null && session.accuracy >= 60
      ? 'text-yellow-400' :'text-red-400';

  return (
    <div className="glass-card-solid rounded-2xl border border-border overflow-hidden transition-all duration-200 hover:border-primary/30">
      {/* Row header — always visible */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-4 px-6 py-4 text-left hover:bg-primary/5 transition-colors"
      >
        {/* Session ID + date */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3">
            <span className="text-sm font-bold text-foreground">
              Session #{session.id.split('-')[1]}
            </span>
            <span className="text-xs text-muted-foreground">{session.date}</span>
          </div>
          <div className="flex items-center gap-4 mt-1">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Clock size={11} />
              {session.duration}
            </div>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <BarChart2 size={11} />
              {session.totalShots} shots
            </div>
          </div>
        </div>

        {/* Shot badges */}
        <div className="hidden md:flex items-center gap-1.5 flex-shrink-0">
          <ShotBadge shot={session.dominantShot} size="sm" />
        </div>

        {/* Accuracy */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className={`font-mono-data text-lg font-bold ${accuracyColor}`}>
            {session.accuracy === null ? '—' : `${session.accuracy}%`}
          </span>
          <span className={`text-xs font-semibold ${trendColor}`}>
            {session.trend === 'up' ? '↑' : session.trend === 'down' ? '↓' : '→'} {session.trendValue}
          </span>
        </div>

        {/* Expand toggle */}
        <div className="text-muted-foreground flex-shrink-0">
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="px-6 pb-6 border-t border-border/50 pt-4 fade-in-up">
          {/* Accuracy bar */}
          <div className="mb-5">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs text-muted-foreground uppercase tracking-widest font-semibold">
                Overall Accuracy
              </span>
              <span className={`font-mono-data text-sm font-bold ${accuracyColor}`}>
                {session.accuracy === null ? '—' : `${session.accuracy}%`}
              </span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full accuracy-bar ${
                  session.accuracy !== null && session.accuracy >= 75
                    ? 'bg-emerald-500'
                    : session.accuracy !== null && session.accuracy >= 60
                    ? 'bg-yellow-500' :'bg-red-500'
                }`}
                style={{ width: `${session.accuracy || 0}%` }}
              />
            </div>
          </div>

          {/* Shot breakdown */}
          <div className="mb-5">
            <p className="text-xs text-muted-foreground uppercase tracking-widest font-semibold mb-3">
              Shot Breakdown
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {session.shotBreakdown.map((sb) => (
                <div
                  key={`${session.id}-${sb.shot}`}
                  className="flex items-center justify-between gap-3 bg-muted/20 rounded-xl px-4 py-3"
                >
                  <div className="flex items-center gap-2">
                    <ShotBadge shot={sb.shot} size="sm" />
                    <span className="text-xs text-muted-foreground">×{sb.count}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          sb.accuracy !== null && sb.accuracy >= 75
                            ? 'bg-emerald-500'
                            : sb.accuracy !== null && sb.accuracy >= 60
                            ? 'bg-yellow-500' :'bg-red-500'
                        }`}
                        style={{ width: `${sb.accuracy || 0}%` }}
                      />
                    </div>
                    <span
                      className={`font-mono-data text-xs font-bold ${
                        sb.accuracy !== null && sb.accuracy >= 75
                          ? 'text-emerald-400'
                          : sb.accuracy !== null && sb.accuracy >= 60
                          ? 'text-yellow-400' :'text-red-400'
                      }`}
                    >
                      {sb.accuracy === null ? '—' : `${sb.accuracy}%`}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* ML Feedback */}
          <div className="bg-primary/5 border border-primary/20 rounded-xl px-4 py-3">
            <p className="text-xs text-accent font-semibold uppercase tracking-widest mb-1.5">
              Session Feedback
            </p>
            <p className="text-sm text-foreground leading-relaxed">{session.feedback}</p>
          </div>
        </div>
      )}
    </div>
  );
}
