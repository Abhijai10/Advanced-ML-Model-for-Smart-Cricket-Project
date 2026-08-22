'use client';

import React from 'react';
import Link from 'next/link';
import ShotBadge, { ShotType } from '@/components/ui/ShotBadge';
import { Clock, BarChart2, ArrowUpRight } from 'lucide-react';

interface Session {
  id: string;
  date: string;
  duration: string;
  totalShots: number;
  accuracy: number;
  dominantShot: ShotType;
  shotBreakdown: { shot: ShotType; count: number }[];
  trend: 'up' | 'down' | 'neutral';
  trendValue: string;
}

export default function RecentSessionsGrid({ sessions = [] }: { sessions?: Session[] }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {sessions.map((session) => (
        <SessionCard key={session.id} session={session} />
      ))}
    </div>
  );
}

function SessionCard({ session }: { session: Session }) {
  const trendColor =
    session.trend === 'up' ?'text-emerald-400'
      : session.trend === 'down' ?'text-red-400' :'text-muted-foreground';

  const accuracyColor =
    session.accuracy >= 75
      ? 'text-emerald-400'
      : session.accuracy >= 60
      ? 'text-yellow-400' :'text-red-400';

  return (
    <div className="glass-card-solid rounded-xl p-4 card-hover group relative overflow-hidden">
      {/* Subtle hover glow */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary/0 to-primary/0 group-hover:from-primary/5 group-hover:to-transparent transition-all duration-300 rounded-xl pointer-events-none" />

      <div className="relative z-10">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div>
            <p className="text-xs text-muted-foreground font-medium">{session.date}</p>
            <p className="text-sm font-semibold text-foreground mt-0.5">
              Session #{session.id.split('-')[1]}
            </p>
          </div>
          <div className="flex items-center gap-1.5">
            <span className={`font-mono-data text-lg font-bold ${accuracyColor}`}>
              {session.accuracy}%
            </span>
            <span className={`text-xs font-semibold ${trendColor}`}>
              {session.trend === 'up' ? '↑' : session.trend === 'down' ? '↓' : '→'}{' '}
              {session.trendValue}
            </span>
          </div>
        </div>

        {/* Meta row */}
        <div className="flex items-center gap-4 mb-3">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock size={12} />
            {session.duration}
          </div>
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <BarChart2 size={12} />
            {session.totalShots} shots
          </div>
        </div>

        {/* Shot breakdown */}
        <div className="flex flex-wrap gap-1.5 mb-3">
          {session.shotBreakdown.map((sb) => (
            <div
              key={`${session.id}-${sb.shot}`}
              className="flex items-center gap-1"
            >
              <ShotBadge shot={sb.shot} size="sm" />
              <span className="text-xs text-muted-foreground font-mono-data">
                ×{sb.count}
              </span>
            </div>
          ))}
        </div>

        {/* Accuracy bar */}
        <div className="mt-2">
          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full accuracy-bar ${
                session.accuracy >= 75
                  ? 'bg-emerald-500'
                  : session.accuracy >= 60
                  ? 'bg-yellow-500' :'bg-red-500'
              }`}
              style={{ width: `${session.accuracy}%` }}
            />
          </div>
        </div>

        {/* View link */}
        <Link
          href="/live-analysis-page"
          className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity duration-150 text-accent"
          aria-label="View session details"
        >
          <ArrowUpRight size={16} />
        </Link>
      </div>
    </div>
  );
}
