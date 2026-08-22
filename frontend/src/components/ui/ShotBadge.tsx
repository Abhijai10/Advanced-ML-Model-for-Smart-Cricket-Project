import React from 'react';

export type ShotType = 'cover_drive' | 'defensive' | 'pull' | 'sweep';

interface ShotBadgeProps {
  shot: ShotType;
  size?: 'sm' | 'md';
}

const SHOT_CONFIG: Record<ShotType, { label: string; className: string }> = {
  cover_drive: { label: 'Cover Drive', className: 'shot-badge-cover' },
  defensive: { label: 'Defensive', className: 'shot-badge-defensive' },
  pull: { label: 'Pull Shot', className: 'shot-badge-pull' },
  sweep: { label: 'Sweep', className: 'shot-badge-sweep' },
};

export default function ShotBadge({ shot, size = 'md' }: ShotBadgeProps) {
  const config = SHOT_CONFIG[shot];
  return (
    <span
      className={`inline-flex items-center font-semibold rounded-full ${config.className} ${
        size === 'sm' ? 'text-xs px-2 py-0.5' : 'text-xs px-2.5 py-1'
      }`}
    >
      {config.label}
    </span>
  );
}