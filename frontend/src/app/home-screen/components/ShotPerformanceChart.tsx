'use client';

import React from 'react';
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';

export type ShotPerformancePoint = { shot: string; accuracy: number };

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: { shot: string; accuracy: number } }[];
}) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="glass-card rounded-lg px-3 py-2 shadow-card border border-border">
      <p className="text-xs font-semibold text-foreground">{d.shot}</p>
      <p className="font-mono-data text-sm text-accent font-bold">{d.accuracy}%</p>
    </div>
  );
}

export default function ShotPerformanceChart({ data = [] }: { data?: ShotPerformancePoint[] }) {
  if (!data.length)
    return (
      <div className="h-[200px] flex items-center justify-center text-xs text-muted-foreground">
        No rated shot data yet.
      </div>
    );
  return (
    <ResponsiveContainer width="100%" height={200}>
      <RadarChart data={data} outerRadius={72}>
        <PolarGrid stroke="var(--border)" strokeDasharray="3 3" />
        <PolarAngleAxis
          dataKey="shot"
          tick={{ fill: 'var(--muted-foreground)', fontSize: 11, fontFamily: 'var(--font-sans)' }}
        />
        <Radar
          name="Accuracy"
          dataKey="accuracy"
          stroke="var(--primary)"
          fill="var(--primary)"
          fillOpacity={0.25}
          strokeWidth={2}
        />
        <Tooltip content={<CustomTooltip />} />
      </RadarChart>
    </ResponsiveContainer>
  );
}
