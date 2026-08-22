'use client';

import AppLayout from '@/components/AppLayout';
import SessionsContent from './components/SessionsContent';
import { durationLabel, formatDate, toShotType } from '@/lib/analytics';
import { useSmartCricket } from '@/components/SmartCricketProvider';

export default function SessionsPage() {
  const { sessions: rows } = useSmartCricket();
  const sessions = rows.flatMap((row) => {
    const shot = toShotType(row.predicted_shot);
    if (!shot) return [];
    return [{ id: row.id, date: formatDate(row.created_at), duration: durationLabel(row.shot_duration_seconds), totalShots: 1, accuracy: null, dominantShot: shot, shotBreakdown: [{ shot, count: 1, accuracy: null }], trend: 'neutral' as const, trendValue: '—', feedback: row.coaching_tips?.join(' ') || row.full_result?.detailed_feedback || 'No feedback was generated.' }];
  });
  return (
    <AppLayout activePath="/sessions">
      <SessionsContent sessions={sessions} />
    </AppLayout>
  );
}
