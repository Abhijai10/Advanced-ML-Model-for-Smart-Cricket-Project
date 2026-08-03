import { useEffect, useMemo, useState } from "react";
import { Activity, LogOut, ShieldCheck } from "lucide-react";
import type { Session } from "@supabase/supabase-js";
import { AuthPanel } from "./components/AuthPanel";
import { CameraAnalysis } from "./components/CameraAnalysis";
import { FeedbackPanel } from "./components/FeedbackPanel";
import { ShotCharts } from "./components/ShotCharts";
import { segmentDurationSeconds, fallbackHistory } from "./lib/history";
import { isSupabaseConfigured, supabase } from "./lib/supabase";
import type { AnalysisResponse, AnalysisSession } from "./types";

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [demoMode, setDemoMode] = useState(false);
  const [latestResult, setLatestResult] = useState<AnalysisResponse | null>(null);
  const [history, setHistory] = useState<AnalysisSession[]>(fallbackHistory);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  const userId = session?.user.id;

  useEffect(() => {
    if (!supabase) return;
    void supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setDemoMode(false);
    });
    return () => data.subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!supabase || !userId) {
      return;
    }
    setIsLoadingHistory(true);
    void supabase
      .from("analysis_sessions")
      .select("*")
      .eq("user_id", userId)
      .order("created_at", { ascending: false })
      .limit(20)
      .then(({ data, error }) => {
        if (!error && data) setHistory(data as AnalysisSession[]);
        setIsLoadingHistory(false);
      });
  }, [userId]);

  const canUseApp = Boolean(session) || demoMode;
  const displayName = useMemo(() => {
    if (demoMode) return "Demo workspace";
    return session?.user.user_metadata.display_name ?? session?.user.email ?? "Smart Cricket";
  }, [demoMode, session]);

  async function saveResult(result: AnalysisResponse, sourceName: string) {
    setLatestResult(result);
    const duration = segmentDurationSeconds(result);

    if (!supabase || !userId) {
      const localRow: AnalysisSession = {
        id: crypto.randomUUID(),
        user_id: "demo",
        video_file_name: sourceName,
        predicted_shot: result.predicted_shot,
        shot_confidence: result.shot_confidence,
        technique_match_score: result.technique_match_score,
        shot_start_frame: result.segmentation.start_frame,
        shot_end_frame: result.segmentation.end_frame,
        shot_duration_seconds: duration,
        spoken_feedback: result.spoken_feedback,
        coaching_tips: result.coaching_tips,
        full_result: result,
        created_at: new Date().toISOString(),
      };
      setHistory((rows) => [localRow, ...rows].slice(0, 20));
      return;
    }

    const { data, error } = await supabase
      .from("analysis_sessions")
      .insert({
        user_id: userId,
        video_file_name: sourceName,
        predicted_shot: result.predicted_shot,
        shot_confidence: result.shot_confidence,
        technique_match_score: result.technique_match_score,
        shot_start_frame: result.segmentation.start_frame,
        shot_end_frame: result.segmentation.end_frame,
        shot_duration_seconds: duration,
        spoken_feedback: result.spoken_feedback,
        coaching_tips: result.coaching_tips,
        full_result: result,
      })
      .select()
      .single();

    if (!error && data) {
      await supabase.from("shot_timeline_events").insert({
        user_id: userId,
        analysis_session_id: data.id,
        shot_label: result.predicted_shot,
        duration_seconds: duration,
      });
      setHistory((rows) => [data as AnalysisSession, ...rows].slice(0, 20));
    }
  }

  async function signOut() {
    if (supabase) await supabase.auth.signOut();
    setDemoMode(false);
    setLatestResult(null);
    setHistory([]);
  }

  if (!canUseApp) {
    return <AuthPanel onDemoMode={() => setDemoMode(true)} />;
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="brand-lockup">
          <span className="brand-mark">
            <Activity size={20} aria-hidden="true" />
          </span>
          <span>Smart Cricket</span>
        </div>
        <div className="header-meta">
          <span>{displayName}</span>
          <button className="ghost-action compact" type="button" onClick={signOut}>
            <LogOut size={16} aria-hidden="true" />
            Exit
          </button>
        </div>
      </header>

      <section className="workspace-hero" aria-labelledby="workspace-title">
        <div>
          <p className="product-kicker">Made by Abhijai Raghuvanshi</p>
          <h1 id="workspace-title">Record. Analyze. Improve the next shot.</h1>
          <p>
            A cricket shot analysis workspace with camera capture, model prediction, technique scoring,
            coaching feedback, voice metadata, and saved shot history.
          </p>
        </div>
        <div className="trust-strip">
          <ShieldCheck size={18} aria-hidden="true" />
          <span>{isSupabaseConfigured ? "Secure Supabase workspace" : "Local preview mode"}</span>
        </div>
      </section>

      <main className="analysis-grid">
        <CameraAnalysis onResult={saveResult} accessToken={session?.access_token} />
        <FeedbackPanel result={latestResult} />
      </main>

      {isLoadingHistory ? <div className="history-empty">Loading history...</div> : <ShotCharts rows={history} />}
    </div>
  );
}

export default App;
