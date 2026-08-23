'use client';

import React from 'react';
import dynamic from 'next/dynamic';

const ShotPerformanceChart = dynamic(() => import('./ShotPerformanceChart'), {
  ssr: false,
  loading: () => <div className="h-[260px] animate-pulse bg-muted/40 rounded-xl" />,
});

type PerformancePoint = { shot: string; accuracy: number; color: string };

export default function ShotPerformancePreview({ data = [] }: { data?: PerformancePoint[] }) {
  return (
    <div className="glass-card-solid rounded-xl p-5 h-full">
      <p className="text-xs text-muted-foreground mb-1">7-day rolling average</p>
      <ShotPerformanceChart />
      <div className="mt-4 grid grid-cols-2 gap-2">
        {data.map((item) => (
          <div
            key={`perf-${item?.shot?.toLowerCase()?.replace(/\s/g, '-')}`}
            className="flex items-center gap-2"
          >
            <div className={`w-2 h-2 rounded-full ${item?.color} flex-shrink-0`} />
            <div className="min-w-0">
              <p className="text-xs text-muted-foreground truncate">{item?.shot}</p>
              <p
                className={`font-mono-data text-sm font-bold ${item.accuracy >= 75 ? 'text-emerald-400' : item.accuracy >= 65 ? 'text-yellow-400' : 'text-red-400'}`}
              >
                {item.accuracy}%
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
