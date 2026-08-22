'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Play, ChevronRight, Target, Zap, AlertTriangle, TrendingUp } from 'lucide-react';

function getGreeting(hour: number): string {
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

// BACKEND INTEGRATION POINT: Replace with API call to fetch player summary stats
// GET /api/player/summary → { playerName, overallAccuracy, practiceStreak, strongestShot, recentMistakes, totalSessions }
interface PlayerSummary {
  playerName: string;
  overallAccuracy: number | null;
  practiceStreak: number | null;
  strongestShot: { name: string; accuracy: number | null } | null;
  recentMistakes: { shot: string; note: string }[];
  totalSessions: number | null;
}

const EMPTY_SUMMARY: PlayerSummary = {
  playerName: 'Player',
  overallAccuracy: null,
  practiceStreak: null,
  strongestShot: null,
  recentMistakes: [],
  totalSessions: null,
};

export default function HomeContent({ summary = EMPTY_SUMMARY }: { summary?: PlayerSummary }) {
  const [greeting, setGreeting] = useState('Good morning');
  const [timeStr, setTimeStr] = useState('');

  useEffect(() => {
    const now = new Date();
    setGreeting(getGreeting(now.getHours()));
    setTimeStr(
      now.toLocaleDateString('en-AU', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric',
      })
    );
  }, []);

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <div className="max-w-3xl mx-auto w-full px-6 py-16 flex flex-col gap-12">

        {/* Hero greeting */}
        <div className="flex flex-col gap-3">
          {timeStr && (
            <p className="text-xs font-semibold tracking-widest uppercase text-muted-foreground">
              {timeStr}
            </p>
          )}
          <h1 className="text-4xl xl:text-5xl font-bold text-foreground leading-tight">
            {greeting},{' '}
            <span className="text-gradient-primary">{summary.playerName}</span>
          </h1>
          {summary.practiceStreak !== null ? (
            <p className="text-base text-muted-foreground">
              You&apos;re on a{' '}
              <span className="text-foreground font-semibold">{summary.practiceStreak}-day</span>{' '}
              practice streak. Keep it going.
            </p>
          ) : (
            <p className="text-base text-muted-foreground">
              Ready to analyse your game today?
            </p>
          )}
        </div>

        {/* Primary CTA */}
        <Link
          href="/live-analysis-page"
          className="btn-primary flex items-center gap-3 px-8 py-4 rounded-2xl text-base font-semibold w-fit primary-glow"
        >
          <Play size={18} fill="currentColor" />
          Start Analysing
          <ChevronRight size={18} />
        </Link>

        {/* Key stats — 3 minimal cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <MinimalStatCard
            label="Overall Accuracy"
            value={summary.overallAccuracy !== null ? `${summary.overallAccuracy}%` : '—'}
            icon={<Target size={16} />}
            highlight={summary.overallAccuracy !== null && summary.overallAccuracy >= 75}
          />
          <MinimalStatCard
            label="Sessions Completed"
            value={summary.totalSessions !== null ? `${summary.totalSessions}` : '—'}
            icon={<TrendingUp size={16} />}
          />
          <MinimalStatCard
            label="Practice Streak"
            value={summary.practiceStreak !== null ? `${summary.practiceStreak} days` : '—'}
            icon={<Zap size={16} />}
            highlight={summary.practiceStreak !== null && summary.practiceStreak >= 5}
          />
        </div>

        {/* Strongest shot */}
        <div className="glass-card-solid rounded-2xl p-6 border border-border">
          <div className="flex items-center gap-2 mb-4">
            <Zap size={15} className="text-accent" />
            <span className="text-xs font-semibold tracking-widest uppercase text-muted-foreground">
              Strongest Shot
            </span>
          </div>
          {summary.strongestShot ? (
            <div className="flex items-end justify-between">
              <div>
                <p className="text-2xl font-bold text-foreground">{summary.strongestShot.name}</p>
                <p className="text-sm text-muted-foreground mt-1">Your most consistent shot</p>
              </div>
              <div className="text-right">
                <p className="font-mono-data text-3xl font-bold text-accent">
                  {summary.strongestShot.accuracy === null ? '—' : `${summary.strongestShot.accuracy}%`}
                </p>
                <p className="text-xs text-muted-foreground">accuracy</p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Complete a session to see your strongest shot.
            </p>
          )}
        </div>

        {/* Recent mistakes */}
        <div className="glass-card-solid rounded-2xl p-6 border border-border">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle size={15} className="text-yellow-400" />
            <span className="text-xs font-semibold tracking-widest uppercase text-muted-foreground">
              Areas to Improve
            </span>
          </div>
          {summary.recentMistakes.length > 0 ? (
            <div className="flex flex-col gap-3">
              {summary.recentMistakes.map((m, i) => (
                <div
                  key={`mistake-${i}`}
                  className="flex items-start gap-3 py-3 border-b border-border/50 last:border-0"
                >
                  <div className="w-1.5 h-1.5 rounded-full bg-yellow-400 mt-1.5 flex-shrink-0" />
                  <div>
                    <p className="text-sm font-semibold text-foreground">{m.shot}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{m.note}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              No recent mistakes logged. Complete a session to get feedback.
            </p>
          )}
        </div>

        {/* Sessions shortcut */}
        <Link
          href="/sessions"
          className="flex items-center justify-between px-6 py-4 rounded-2xl border border-border hover:border-primary/40 hover:bg-primary/5 transition-all duration-200 group"
        >
          <span className="text-sm font-medium text-muted-foreground group-hover:text-foreground transition-colors">
            View full session history
          </span>
          <ChevronRight size={16} className="text-muted-foreground group-hover:text-accent transition-colors" />
        </Link>

      </div>
    </div>
  );
}

function MinimalStatCard({
  label,
  value,
  icon,
  highlight = false,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  highlight?: boolean;
}) {
  return (
    <div className={`glass-card-solid rounded-2xl p-5 border transition-all duration-200 ${highlight ? 'border-primary/40' : 'border-border'}`}>
      <div className={`flex items-center gap-2 mb-3 ${highlight ? 'text-accent' : 'text-muted-foreground'}`}>
        {icon}
        <span className="text-xs font-semibold tracking-widest uppercase">{label}</span>
      </div>
      <p className={`font-mono-data text-2xl font-bold ${highlight ? 'text-accent' : 'text-foreground'}`}>
        {value}
      </p>
    </div>
  );
}
