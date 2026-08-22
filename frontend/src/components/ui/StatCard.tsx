import React from 'react';

interface StatCardProps {
  label: string;
  value: string;
  subtext?: string;
  icon?: React.ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  alert?: boolean;
  className?: string;
}

export default function StatCard({
  label,
  value,
  subtext,
  icon,
  trend,
  trendValue,
  alert,
  className = '',
}: StatCardProps) {
  const trendColor =
    trend === 'up' ?'text-emerald-400'
      : trend === 'down' ?'text-red-400' :'text-muted-foreground';

  return (
    <div
      className={`glass-card-solid rounded-xl p-5 card-hover ${
        alert ? 'border-red-500/30 bg-red-950/10' : ''
      } ${className}`}
    >
      <div className="flex items-start justify-between mb-3">
        <span className="text-xs font-semibold tracking-widest uppercase text-muted-foreground">
          {label}
        </span>
        {icon && (
          <span className={`${alert ? 'text-red-400' : 'text-accent'}`}>
            {icon}
          </span>
        )}
      </div>
      <div className="flex items-end gap-2">
        <span className="font-mono-data text-3xl font-bold text-foreground">
          {value}
        </span>
        {trendValue && (
          <span className={`text-xs font-semibold mb-1 ${trendColor}`}>
            {trend === 'up' ? '↑' : trend === 'down' ? '↓' : ''} {trendValue}
          </span>
        )}
      </div>
      {subtext && (
        <p className="text-xs text-muted-foreground mt-1">{subtext}</p>
      )}
    </div>
  );
}