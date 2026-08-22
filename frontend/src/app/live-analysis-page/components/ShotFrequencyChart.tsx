'use client';

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { BarChart2 } from 'lucide-react';
import type { ShotFrequencyData } from './LiveAnalysisContent';

interface ShotFrequencyChartProps {
  // BACKEND INTEGRATION POINT: Pass real-time shot count data from ML inference stream
  data: ShotFrequencyData[];
  totalShots: number;
}

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: { value: number; payload: ShotFrequencyData }[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass-card rounded-xl px-3 py-2.5 shadow-card border border-border">
      <p className="text-xs font-semibold text-foreground mb-0.5">{label}</p>
      <p className="font-mono-data text-sm text-accent font-bold">
        {payload[0].value} shots
      </p>
    </div>
  );
}

export default function ShotFrequencyChart({ data, totalShots }: ShotFrequencyChartProps) {
  return (
    <div className="glass-card-solid rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BarChart2 size={16} className="text-accent" />
          <h3 className="text-sm font-semibold text-foreground">Shot Frequency</h3>
        </div>
        <span className="font-mono-data text-xs text-muted-foreground">
          {totalShots} total
        </span>
      </div>

      {totalShots === 0 ? (
        <div className="flex flex-col items-center justify-center h-44 text-center">
          <p className="text-xs text-muted-foreground">
            Shot frequency will appear as the session progresses
          </p>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={data} barSize={36} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
            <XAxis
              dataKey="shot"
              tick={{ fill: 'var(--muted-foreground)', fontSize: 12, fontFamily: 'var(--font-sans)' }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fill: 'var(--muted-foreground)', fontSize: 11, fontFamily: 'var(--font-sans)' }}
              axisLine={false}
              tickLine={false}
              allowDecimals={false}
            />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(124,58,237,0.06)' }} />
            <Bar dataKey="count" radius={[6, 6, 0, 0]}>
              {data.map((entry) => (
                <Cell key={`cell-freq-${entry.shot.toLowerCase().replace(/\s/g, '-')}`} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}