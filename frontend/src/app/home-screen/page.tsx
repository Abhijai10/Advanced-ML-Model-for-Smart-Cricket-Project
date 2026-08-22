'use client';

import React, { useEffect, useMemo, useState } from 'react';
import AppLayout from '@/components/AppLayout';
import HomeContent from './components/HomeContent';
import { detectedIssues, practiceStreak, shotLabel } from '@/lib/analytics';
import { useSmartCricket } from '@/components/SmartCricketProvider';
import { getAnalytics } from '@/lib/api';

export default function HomeScreenPage() {
  const { displayName, sessions } = useSmartCricket();
  const { session } = useSmartCricket();
  const [summaryMetrics, setSummaryMetrics] = useState<{ overall_accuracy: number | null; technique_quality: Record<string, number> }>({ overall_accuracy: null, technique_quality: {} });
  useEffect(() => {
    if (!session?.access_token) return;
    void getAnalytics<typeof summaryMetrics>('summary', session.access_token).then(setSummaryMetrics).catch(() => setSummaryMetrics({ overall_accuracy: null, technique_quality: {} }));
  }, [session?.access_token, sessions.length]);
  const summary = useMemo(() => {
    const strongest = Object.entries(summaryMetrics.technique_quality).sort((a, b) => b[1] - a[1])[0];
    return {
      playerName: displayName,
      overallAccuracy: summaryMetrics.overall_accuracy,
      practiceStreak: practiceStreak(sessions),
      strongestShot: strongest ? { name: shotLabel(strongest[0]), accuracy: strongest[1] } : null,
      recentMistakes: detectedIssues(sessions),
      totalSessions: sessions.length,
    };
  }, [displayName, sessions, summaryMetrics]);
  return (
    <AppLayout activePath="/home-screen">
      <HomeContent summary={summary} />
    </AppLayout>
  );
}
