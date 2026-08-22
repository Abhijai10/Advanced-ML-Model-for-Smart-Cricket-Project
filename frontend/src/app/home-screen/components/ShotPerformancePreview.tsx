'use client';

import React from 'react';
import dynamic from 'next/dynamic';

const ShotPerformanceChart = dynamic(
  () => import('./ShotPerformanceChart'),
  { ssr: false, loading: () => <div className="h-[260px] animate-pulse bg-muted/40 rounded-xl" /> }
);

export default function ShotPerformancePreview() {
  return (
    <div className="glass-card-solid rounded-xl p-5 h-full">
      <p className="text-xs text-muted-foreground mb-1">7-day rolling average</p>
      <ShotPerformanceChart />
      <div className="mt-4 grid grid-cols-2 gap-2">
        {[
          { shot: 'Cover Drive', acc: 89, color: 'bg-violet-500' },
          { shot: 'Defensive', acc: 74, color: 'bg-emerald-500' },
          { shot: 'Pull Shot', acc: 82, color: 'bg-yellow-500' },
          { shot: 'Sweep', acc: 61, color: 'bg-red-500' },
        ]?.map((item) => (
          <div key={`perf-${item?.shot?.toLowerCase()?.replace(/\s/g, '-')}`} className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${item?.color} flex-shrink-0`} />
            <div className="min-w-0">
              <p className="text-xs text-muted-foreground truncate">{item?.shot}</p>
              <p className={`font-mono-data text-sm font-bold ${item?.acc >= 75 ? 'text-emerald-400' : item?.acc >= 65 ? 'text-yellow-400' : 'text-red-400'}`}>
                {item?.acc}%
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}