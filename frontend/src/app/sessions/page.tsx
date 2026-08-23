'use client';

import { useEffect, useState } from 'react';
import AppLayout from '@/components/AppLayout';
import SessionsContent from './components/SessionsContent';
import { durationLabel, formatDate, toShotType } from '@/lib/analytics';
import { useSmartCricket } from '@/components/SmartCricketProvider';
import { getAnalytics } from '@/lib/api';

export default function SessionsPage() {
  const { sessions: rows, session } = useSmartCricket();
  const [accuracyBySession, setAccuracyBySession] = useState<Record<string, number>>({});
  useEffect(() => {
    if (!session?.access_token) return;
    void getAnalytics<{ sessions: { id: string; accuracy: boolean | null }[] }>(
      'session-history',
      session.access_token
    )
      .then(({ sessions }) =>
        setAccuracyBySession(
          Object.fromEntries(
            sessions
              .filter((item) => item.accuracy !== null)
              .map((item) => [item.id, item.accuracy ? 100 : 0])
          )
        )
      )
      .catch(() => setAccuracyBySession({}));
  }, [rows.length, session?.access_token]);
  const sessions = rows.flatMap((row) => {
    const shot = toShotType(row.predicted_shot);
    if (!shot) return [];
    const accuracy = accuracyBySession[row.id] ?? null;
    return [
      {
        id: row.id,
        date: formatDate(row.created_at),
        duration: durationLabel(row.shot_duration_seconds),
        totalShots: 1,
        accuracy,
        dominantShot: shot,
        shotBreakdown: [{ shot, count: 1, accuracy }],
        trend: 'neutral' as const,
        trendValue: '—',
        feedback:
          row.coaching_tips?.join(' ') ||
          row.full_result?.detailed_feedback ||
          'No feedback was generated.',
      },
    ];
  });
  return (
    <AppLayout activePath="/sessions">
      <SessionsContent sessions={sessions} />
    </AppLayout>
  );
}
