'use client';

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { TrendingUp } from 'lucide-react';
import type { ShotAccuracyPoint } from './LiveAnalysisContent';

interface ShotAccuracyChartProps {
  // BACKEND INTEGRATION POINT: Pass rolling per-shot accuracy data from ML inference stream
  data: ShotAccuracyPoint[];
}

const LINES: { key: keyof ShotAccuracyPoint; color: string; label: string }[] = [
  { key: 'cover_drive', color: 'var(--primary)', label: 'Cover Drive' },
  { key: 'defensive', color: '#10B981', label: 'Defensive' },
  { key: 'pull', color: '#F59E0B', label: 'Pull Shot' },
  { key: 'sweep', color: '#EF4444', label: 'Sweep' },
];

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { color: string; name: string; value: number }[];
  label?: string | number;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass-card rounded-xl px-3 py-2.5 shadow-card border border-border min-w-[140px]">
      <p className="text-xs text-muted-foreground mb-2">After {label} shots</p>
      {payload.map((p) => (
        <div key={`tip-${p.name.toLowerCase().replace(/\s/g, '-')}`} className="flex items-center justify-between gap-3 mb-0.5">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: p.color }} />
            <span className="text-xs text-muted-foreground">{p.name}</span>
          </div>
          <span className="font-mono-data text-xs font-bold text-foreground">{p.value}%</span>
        </div>
      ))}
    </div>
  );
}

export default function ShotAccuracyChart({ data }: ShotAccuracyChartProps) {
  return (
    <div className="glass-card-solid rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <TrendingUp size={16} className="text-accent" />
          <h3 className="text-sm font-semibold text-foreground">Per-Shot Accuracy</h3>
        </div>
        <span className="text-xs text-muted-foreground">Rolling window · 5 shots</span>
      </div>

      {data.length < 2 ? (
        <div className="flex flex-col items-center justify-center h-44 text-center">
          <p className="text-xs text-muted-foreground">
            Accuracy trends appear after 10+ shots are detected
          </p>
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis
              dataKey="index"
              tick={{ fill: 'var(--muted-foreground)', fontSize: 11, fontFamily: 'var(--font-sans)' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${v}`}
            />
            <YAxis
              domain={[0, 100]}
              tick={{ fill: 'var(--muted-foreground)', fontSize: 11, fontFamily: 'var(--font-sans)' }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: '11px', color: 'var(--muted-foreground)' }}
              formatter={(value) => (
                <span style={{ color: 'var(--muted-foreground)', fontFamily: 'var(--font-sans)' }}>
                  {value}
                </span>
              )}
            />
            {LINES.map((line) => (
              <Line
                key={`line-${String(line.key)}`}
                type="monotone"
                dataKey={line.key}
                name={line.label}
                stroke={line.color}
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4, strokeWidth: 0 }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}