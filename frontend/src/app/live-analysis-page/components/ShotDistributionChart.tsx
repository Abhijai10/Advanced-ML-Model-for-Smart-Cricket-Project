'use client';

import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';

// BACKEND INTEGRATION POINT: Receive from WebSocket/API
// { class: string, confidence: number, timestamp: number } → aggregate into shotDistribution
export interface ShotDistributionItem {
  name: string;
  value: number; // count or percentage
  color: string;
}

export interface ShotDistributionChartProps {
  data: ShotDistributionItem[];
  isLive?: boolean;
}

const DEFAULT_COLORS = ['#93C5FD', '#A78BFA', '#6EE7B7', '#FCD34D'];


export default function ShotDistributionChart({
  data,
  isLive = false,
}: ShotDistributionChartProps) {
  const total = data.reduce((sum, d) => sum + d.value, 0);

  return (
    <div className="glass-card-solid rounded-2xl p-5 border border-border">
      {/* Header */}
      <div className="flex items-center justify-between mb-1">
        <div>
          <p className="text-xs font-semibold tracking-widest uppercase text-muted-foreground">
            Model Response / Shot Classes
          </p>
          <h3 className="text-lg font-bold text-foreground mt-0.5">Shot distribution</h3>
        </div>
        <div className={`flex items-center gap-1.5 border border-border rounded-full px-3 py-1 text-xs font-semibold ${isLive ? 'text-emerald-400 border-emerald-500/30' : 'text-muted-foreground'}`}>
          {isLive && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 recording-dot" />}
          {isLive ? 'Live' : 'Live schema'}
        </div>
      </div>

      <div className="flex items-center gap-6 mt-4">
        {/* Donut chart */}
        <div className="flex-shrink-0" style={{ width: 140, height: 140 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                innerRadius={42}
                outerRadius={65}
                paddingAngle={3}
                dataKey="value"
                strokeWidth={0}
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  background: 'var(--card)',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  fontSize: '12px',
                  color: 'var(--foreground)',
                }}
                formatter={(value: number) => [`${total > 0 ? Math.round((value / total) * 100) : 0}%`, '']}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Legend */}
        <div className="flex-1 flex flex-col gap-3">
          {data.map((item) => {
            const pct = total > 0 ? Math.round((item.value / total) * 100) : 0;
            return (
              <div key={item.name} className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <span
                    className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                    style={{ backgroundColor: item.color }}
                  />
                  <span className="text-sm text-foreground">{item.name}</span>
                </div>
                <span className="font-mono-data text-sm font-semibold text-muted-foreground">
                  {pct}%
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer */}
      <div className="mt-4 pt-3 border-t border-border/50">
        <p className="text-xs text-muted-foreground tracking-widest uppercase font-semibold">
          Expected Payload: Class · Confidence · Timestamp
        </p>
      </div>
    </div>
  );
}
