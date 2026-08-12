import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { Activity, LogOut, ShieldCheck } from "lucide-react";
import type { Session } from "@supabase/supabase-js";
import { AuthPanel } from "./components/AuthPanel";
import { CameraAnalysis } from "./components/CameraAnalysis";
import { FeedbackPanel } from "./components/FeedbackPanel";
import { segmentDurationSeconds, fallbackHistory } from "./lib/history";
import { getCapabilities } from "./lib/api";
import { isSupabaseConfigured, supabase } from "./lib/supabase";
import type { AnalysisResponse, AnalysisSession, Capabilities } from "./types";

const ShotCharts = lazy(() => import("./components/ShotCharts").then((module) => ({ default: module.ShotCharts })));

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [demoMode, setDemoMode] = useState(false);
  const [latestResult, setLatestResult] = useState<AnalysisResponse | null>(null);
  const [history, setHistory] = useState<AnalysisSession[]>(fallbackHistory);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);

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
    void refreshTrustedHistory(userId);
  }, [userId]);

  useEffect(() => {
    void getCapabilities()
      .then(setCapabilities)
      .catch(() =>
        setCapabilities({
          auth_required: false,
          feedback_enabled: false,
          model_improvement_enabled: false,
          evidence_retention_enabled: false,
          tts_provider: "unknown",
          max_upload_bytes: 250 * 1024 * 1024,
          max_recording_duration_seconds: 20,
          accepted_video_extensions: [".mp4", ".mov", ".webm"],
        }),
      );
  }, []);

  const canUseApp = Boolean(session) || demoMode;
  const displayName = useMemo(() => {
    if (demoMode) return "Demo workspace";
    return session?.user.user_metadata.display_name ?? session?.user.email ?? "Smart Cricket";
  }, [demoMode, session]);

  async function refreshTrustedHistory(activeUserId: string) {
    if (!supabase) return;
    setIsLoadingHistory(true);
    const { data, error } = await supabase
      .from("analysis_sessions")
      .select("*")
      .eq("user_id", activeUserId)
      .order("created_at", { ascending: false })
      .limit(20);
    if (!error && data) {
      setHistory((data as AnalysisSession[]).map((row) => ({ ...row, history_status: "server_saved" })));
    }
    setIsLoadingHistory(false);
  }

  async function saveResult(result: AnalysisResponse, sourceName: string) {
    setLatestResult(result);
    const duration = segmentDurationSeconds(result);
    const serverAnalysisId =
      typeof result.api_metadata.analysis_session_id === "string" ? result.api_metadata.analysis_session_id : "";
    const persistence = result.api_metadata.analysis_persistence as
      | { attempted?: boolean; stored?: boolean; storage_status?: string; error_code?: string | null }
      | undefined;
    const historyStatus: AnalysisSession["history_status"] =
      serverAnalysisId && persistence?.stored ? "server_saved" : userId ? "unsaved" : "local_demo";
    const localRow: AnalysisSession = {
      id: serverAnalysisId || crypto.randomUUID(),
      user_id: userId ?? "demo",
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
      history_status: historyStatus,
    };

    if (!supabase || !userId) {
      setHistory((rows) => [localRow, ...rows].slice(0, 20));
      return;
    }

    setHistory((rows) => [localRow, ...rows.filter((row) => row.id !== localRow.id)].slice(0, 20));
    if (serverAnalysisId && persistence?.stored) {
      await refreshTrustedHistory(userId);
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
        <CameraAnalysis onResult={saveResult} accessToken={session?.access_token} capabilities={capabilities} />
        <FeedbackPanel result={latestResult} accessToken={session?.access_token} capabilities={capabilities} />
      </main>

      {isLoadingHistory ? (
        <div className="history-empty">Loading history...</div>
      ) : (
        <Suspense fallback={<div className="history-empty">Loading trends...</div>}>
          <ShotCharts rows={history} />
        </Suspense>
      )}
    </div>
  );
}

export default App;
