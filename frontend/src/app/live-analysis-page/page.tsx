import React from 'react';
import AppLayout from '@/components/AppLayout';
import LiveAnalysisContent from './components/LiveAnalysisContent';

export default function LiveAnalysisPage() {
  return (
    <AppLayout activePath="/live-analysis-page">
      <LiveAnalysisContent />
    </AppLayout>
  );
}