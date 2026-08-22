'use client';

import React, { useMemo } from 'react';
import AppLayout from '@/components/AppLayout';
import HomeContent from './components/HomeContent';
import { detectedIssues, practiceStreak, shotLabel } from '@/lib/analytics';
import { useSmartCricket } from '@/components/SmartCricketProvider';

export default function HomeScreenPage() {
  const { displayName, sessions } = useSmartCricket();
  const summary = useMemo(() => {
    const counts = new Map<string, number>();
    sessions.forEach((row) => {
      if (row.predicted_shot) counts.set(row.predicted_shot, (counts.get(row.predicted_shot) || 0) + 1);
    });
    const strongest = [...counts.entries()].sort((a, b) => b[1] - a[1])[0];
    return {
      playerName: displayName,
      overallAccuracy: null,
      practiceStreak: practiceStreak(sessions),
      strongestShot: strongest ? { name: shotLabel(strongest[0]), accuracy: null } : null,
      recentMistakes: detectedIssues(sessions),
      totalSessions: sessions.length,
    };
  }, [displayName, sessions]);
  return (
    <AppLayout activePath="/home-screen">
      <HomeContent summary={summary} />
    </AppLayout>
  );
}
