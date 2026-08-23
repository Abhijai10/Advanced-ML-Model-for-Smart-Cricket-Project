'use client';

import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Cell,
  LabelList,
} from 'recharts';

// BACKEND INTEGRATION POINT: Receive from API
// GET /api/sessions/class-accuracy → { shot: string, accuracy: number }[]
export interface ClassAccuracyItem {
  shot: string;
  accuracy: number; // 0–100
}

export interface ClassAccuracyChartProps {
  data: ClassAccuracyItem[];
}

const BAR_COLOR = '#93C5FD';

export default function ClassAccuracyChart({ data }: ClassAccuracyChartProps) {
  return (
    <div className="glass-card-solid rounded-2xl p-5 border border-border">
      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <div>
          <p className="text-xs font-semibold tracking-widest uppercase text-muted-foreground">
            Model Response / Precision
          </p>
          <h3 className="text-lg font-bold text-foreground mt-0.5">Class accuracy</h3>
        </div>
        <div className="w-8 h-8 rounded-full border-2 border-accent/40 flex items-center justify-center">
          <div className="w-4 h-4 rounded-full border-2 border-accent/60 flex items-center justify-center">
            <div className="w-1.5 h-1.5 rounded-full bg-accent" />
          </div>
        </div>
      </div>

      <div className="mt-4" style={{ height: 200 }}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 0, right: 48, left: 0, bottom: 0 }}
            barSize={16}
          >
            <CartesianGrid
              horizontal={false}
              strokeDasharray="4 4"
              stroke="rgba(255,255,255,0.06)"
            />
            <XAxis type="number" domain={[0, 100]} tick={false} axisLine={false} tickLine={false} />
            <YAxis
              type="category"
              dataKey="shot"
              width={110}
              tick={{ fill: 'var(--foreground)', fontSize: 13 }}
              axisLine={false}
              tickLine={false}
            />
            <Bar dataKey="accuracy" radius={[0, 4, 4, 0]} background={{ fill: 'transparent' }}>
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={BAR_COLOR}
                  fillOpacity={0.85}
                  style={{ filter: 'drop-shadow(0 0 4px rgba(147, 197, 253, 0.3))' }}
                />
              ))}
              <LabelList
                dataKey="accuracy"
                position="right"
                formatter={(v: number) => `${v}%`}
                style={{
                  fill: 'var(--foreground)',
                  fontSize: 13,
                  fontWeight: 600,
                  fontFamily: 'var(--font-mono)',
                }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
