'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { Session, User } from '@supabase/supabase-js';
import { supabase } from '@/lib/supabase';
import type { StoredAnalysisSession } from '@/lib/analytics';

type SmartCricketContextValue = {
  session: Session | null;
  user: User | null;
  displayName: string;
  sessions: StoredAnalysisSession[];
  loading: boolean;
  configurationError: string | null;
  refreshSessions: () => Promise<void>;
  signOut: () => Promise<void>;
};

const SmartCricketContext = createContext<SmartCricketContextValue | null>(null);

export function SmartCricketProvider({ children }: { children: React.ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [sessions, setSessions] = useState<StoredAnalysisSession[]>([]);
  const [loading, setLoading] = useState(Boolean(supabase));
  const configurationError = supabase ? null : 'Supabase is not configured for this environment.';

  const refreshSessions = useCallback(async () => {
    if (!supabase || !session?.user) {
      setSessions([]);
      return;
    }
    const { data, error } = await supabase
      .from('analysis_sessions')
      .select(
        'id,user_id,video_file_name,predicted_shot,shot_confidence,technique_match_score,shot_duration_seconds,coaching_tips,full_result,created_at'
      )
      .order('created_at', { ascending: false })
      .limit(100);
    if (!error && data) setSessions(data as StoredAnalysisSession[]);
  }, [session?.user]);

  useEffect(() => {
    if (!supabase) {
      setLoading(false);
      return;
    }
    void supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });
    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) =>
      setSession(nextSession)
    );
    return () => data.subscription.unsubscribe();
  }, []);

  useEffect(() => {
    void refreshSessions();
  }, [refreshSessions]);

  const value = useMemo<SmartCricketContextValue>(
    () => ({
      session,
      user: session?.user || null,
      displayName: String(
        session?.user.user_metadata.full_name ||
          session?.user.user_metadata.display_name ||
          session?.user.email ||
          'Player'
      ),
      sessions,
      loading,
      configurationError,
      refreshSessions,
      signOut: async () => {
        if (supabase) await supabase.auth.signOut();
      },
    }),
    [configurationError, loading, refreshSessions, session, sessions]
  );

  return <SmartCricketContext.Provider value={value}>{children}</SmartCricketContext.Provider>;
}

export function useSmartCricket() {
  const value = useContext(SmartCricketContext);
  if (!value) throw new Error('useSmartCricket must be used within SmartCricketProvider.');
  return value;
}
