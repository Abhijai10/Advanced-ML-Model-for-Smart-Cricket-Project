import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { Link, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import { Activity, ArrowRight, BarChart3, CheckCircle2, Lock, LogOut } from "lucide-react";
import type { Session } from "@supabase/supabase-js";
import { AuthPanel } from "./components/AuthPanel";
import { CameraAnalysis } from "./components/CameraAnalysis";
import { FeedbackPanel } from "./components/FeedbackPanel";
import { segmentDurationSeconds, fallbackHistory, shotName } from "./lib/history";
import { getCapabilities } from "./lib/api";
import { supabase } from "./lib/supabase";
import type { AnalysisResponse, AnalysisSession, Capabilities } from "./types";
import {
  AnimatedContent,
  AnimatedList,
  BlurText,
  CountUp,
  MagicBento,
  PillNav,
  ShinyText,
  SoftAurora,
  SpotlightCard,
  Stepper,
} from "./components/reactbits/ReactBits";

const ShotCharts = lazy(() => import("./components/ShotCharts").then((module) => ({ default: module.ShotCharts })));

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [demoMode, setDemoMode] = useState(false);
  const [latestResult, setLatestResult] = useState<AnalysisResponse | null>(null);
  const [history, setHistory] = useState<AnalysisSession[]>(fallbackHistory);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState("");
  const [capabilities, setCapabilities] = useState<Capabilities | null>(null);
  const [capabilitiesUnavailable, setCapabilitiesUnavailable] = useState(false);
  const [workflowStep, setWorkflowStep] = useState(0);

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
    if (!supabase || !userId) return;
    void refreshTrustedHistory(userId);
  }, [userId]);

  useEffect(() => {
    void getCapabilities()
      .then((value) => {
        setCapabilities(value);
        setCapabilitiesUnavailable(false);
      })
      .catch(() => {
        setCapabilitiesUnavailable(true);
        setCapabilities({
          auth_required: false,
          feedback_enabled: false,
          model_improvement_enabled: false,
          evidence_retention_enabled: false,
          tts_provider: "unknown",
          audio_storage_backend: "unknown",
          max_upload_bytes: 250 * 1024 * 1024,
          max_recording_duration_seconds: 20,
          accepted_video_extensions: [".mp4", ".mov", ".webm"],
        });
      });
  }, []);

  const canUseApp = Boolean(session) || demoMode;
  const displayName = useMemo(() => {
    if (demoMode) return "Demo workspace";
    return session?.user.user_metadata.display_name ?? session?.user.email ?? "Smart Cricket";
  }, [demoMode, session]);

  async function refreshTrustedHistory(activeUserId: string) {
    if (!supabase) return;
    setIsLoadingHistory(true);
    setHistoryError("");
    const { data, error } = await supabase
      .from("analysis_sessions")
      .select("*")
      .eq("user_id", activeUserId)
      .order("created_at", { ascending: false })
      .limit(20);
    if (!error && data) {
      setHistory((data as AnalysisSession[]).map((row) => ({ ...row, history_status: "server_saved" })));
    } else if (error) {
      setHistoryError("History could not be refreshed. Recent local results remain visible.");
    }
    setIsLoadingHistory(false);
  }

  async function saveResult(result: AnalysisResponse, sourceName: string) {
    setLatestResult(result);
    setWorkflowStep(2);
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

  function enterDemo() {
    setDemoMode(true);
  }

  return (
    <Routes>
      <Route path="/" element={<LandingPage onDemoMode={enterDemo} />} />
      <Route path="/auth" element={<AuthPanel onDemoMode={enterDemo} />} />
      <Route
        path="/app/*"
        element={
          canUseApp ? (
            <AppShell
              capabilities={capabilities}
              capabilitiesUnavailable={capabilitiesUnavailable}
              demoMode={demoMode}
              displayName={displayName}
              history={history}
              historyError={historyError}
              isLoadingHistory={isLoadingHistory}
              latestResult={latestResult}
              onRefreshHistory={userId ? () => refreshTrustedHistory(userId) : undefined}
              onResult={saveResult}
              onSignOut={signOut}
              session={session}
              workflowStep={workflowStep}
              setWorkflowStep={setWorkflowStep}
            />
          ) : (
            <Navigate to="/auth" replace />
          )
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

type ShellProps = {
  capabilities: Capabilities | null;
  capabilitiesUnavailable: boolean;
  demoMode: boolean;
  displayName: string;
  history: AnalysisSession[];
  historyError: string;
  isLoadingHistory: boolean;
  latestResult: AnalysisResponse | null;
  onRefreshHistory?: () => Promise<void>;
  onResult: (result: AnalysisResponse, sourceName: string) => Promise<void>;
  onSignOut: () => Promise<void>;
  session: Session | null;
  workflowStep: number;
  setWorkflowStep: (step: number) => void;
};

function AppShell(props: ShellProps) {
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <header className="app-header">
        <Link to="/app" className="brand-lockup" aria-label="Smart Cricket overview">
          <span className="brand-mark">
            <Activity size={20} aria-hidden="true" />
          </span>
          <span>Smart Cricket</span>
        </Link>
        <PillNav />
        <div className="header-meta">
          <span className="capability-dot">
            <span aria-hidden="true" />
            {props.capabilitiesUnavailable ? "Preview fallback" : "Model ready"}
          </span>
          {props.demoMode ? <span className="demo-badge">Demo</span> : null}
          <span className="user-chip">{props.displayName}</span>
          <button className="ghost-action compact" type="button" onClick={() => void props.onSignOut()}>
            <LogOut size={16} aria-hidden="true" />
            Exit
          </button>
        </div>
      </header>
      <main id="main-content" className="app-main">
        <Routes>
          <Route index element={<OverviewPage {...props} />} />
          <Route path="analyze" element={<AnalyzePage {...props} />} />
          <Route path="history" element={<HistoryPage {...props} />} />
          <Route path="history/:id" element={<AnalysisDetail history={props.history} />} />
          <Route path="settings" element={<SettingsPage {...props} />} />
          <Route path="*" element={<Navigate to="/app" replace />} />
        </Routes>
      </main>
    </div>
  );
}

function LandingPage({ onDemoMode }: { onDemoMode: () => void }) {
  const navigate = useNavigate();
  function demo() {
    onDemoMode();
    navigate("/app");
  }
  function analyze() {
    onDemoMode();
    navigate("/app/analyze");
  }
  return (
    <main className="marketing-shell">
      <SoftAurora />
      <header className="marketing-nav">
        <Link to="/" className="brand-lockup">
          <span className="brand-mark">
            <Activity size={20} aria-hidden="true" />
          </span>
          <span>Smart Cricket</span>
        </Link>
        <nav aria-label="Landing sections">
          <a href="#how-it-works">How it works</a>
          <a href="#analysis">Analysis</a>
          <a href="#technology">Technology</a>
          <a href="#privacy">Privacy</a>
        </nav>
        <div className="marketing-actions">
          <Link className="ghost-action compact" to="/auth">Sign in</Link>
          <button className="primary-action compact" type="button" onClick={demo}>Try demo</button>
        </div>
      </header>

      <section className="hero-section">
        <AnimatedContent className="hero-copy">
          <ShinyText>AI-assisted cricket practice analysis</ShinyText>
          <h1><BlurText>Understand the shot. Improve the next one.</BlurText></h1>
          <p>
            Record or upload one batting motion and review shot prediction, confidence, technique scoring,
            coaching feedback, voice/text output, and practice history.
          </p>
          <div className="hero-actions">
            <button className="primary-action" type="button" onClick={analyze}>
              Analyze a shot
              <ArrowRight size={18} aria-hidden="true" />
            </button>
            <button className="secondary-action" type="button" onClick={demo}>Try demo</button>
          </div>
          <p className="trust-copy">No clip retention unless you explicitly opt in.</p>
        </AnimatedContent>
        <SpotlightCard className="product-preview" aria-label="Demo preview sample analysis">
          <div className="preview-top">
            <span>Demo preview</span>
            <em>Ready</em>
          </div>
          <strong>Cover Drive</strong>
          <div className="preview-metrics">
            <span><b>87%</b>Confidence</span>
            <span><b>79</b>Technique</span>
          </div>
          <div className="preview-insight">
            <span>Practice focus</span>
            <p>Front shoulder opens slightly early.</p>
          </div>
          <div className="preview-quality">
            <span>Quality</span>
            <b>Good</b>
          </div>
        </SpotlightCard>
      </section>

      <section className="capability-strip" aria-label="Smart Cricket capabilities">
        {["Shot classification", "Technique scoring", "Confidence awareness", "Practice history"].map((item) => (
          <span key={item}>{item}</span>
        ))}
      </section>

      <section className="landing-section" id="how-it-works">
        <div className="section-heading">
          <h2>Capture, analyze, review.</h2>
          <p>Smart Cricket keeps the workflow focused on one batting motion at a time.</p>
        </div>
        <div className="step-card-grid">
          {[
            ["Record", "Use camera capture or upload MP4, MOV, or WebM."],
            ["Analyze", "The backend checks motion quality and generates a confidence-aware result."],
            ["Review", "See prediction, technique score, coaching tips, audio state, and history."],
          ].map(([title, copy]) => (
            <SpotlightCard className="landing-card" key={title}>
              <CheckCircle2 size={20} aria-hidden="true" />
              <h3>{title}</h3>
              <p>{copy}</p>
            </SpotlightCard>
          ))}
        </div>
      </section>

      <section className="landing-section" id="analysis">
        <div className="section-heading">
          <h2>Built for responsible practice review.</h2>
          <p>Useful performance signals without pretending the model is a certified coach.</p>
        </div>
        <MagicBento className="feature-bento">
          {[
            ["Shot recognition", "Temporal motion classification from the batting sequence."],
            ["Technique review", "Structured templates produce a practical match score."],
            ["Confidence-aware output", "Uncertain results are shown as uncertain."],
            ["Coaching feedback", "Detected issues become concise practice focus."],
            ["Practice history", "Track saved, unsaved, and demo analyses separately."],
            ["Human-reviewed improvement", "Corrections can contribute only through consent and review."],
          ].map(([title, copy]) => (
            <SpotlightCard className="landing-card" key={title}>
              <h3>{title}</h3>
              <p>{copy}</p>
            </SpotlightCard>
          ))}
        </MagicBento>
      </section>

      <section className="landing-section privacy-band" id="privacy">
        <Lock size={24} aria-hidden="true" />
        <div>
          <h2>Your practice footage stays under your control.</h2>
          <p>
            Analysis does not automatically mean training. Model-improvement retention is opt-in,
            feedback is not ground truth, and human review is required before any candidate export.
          </p>
        </div>
        <button className="secondary-action compact" type="button" onClick={demo}>Learn about data use</button>
      </section>

      <section className="landing-section final-cta" id="technology">
        <h2>Ready to review your next shot?</h2>
        <div className="hero-actions">
          <button className="primary-action" type="button" onClick={analyze}>Analyze a shot</button>
          <button className="secondary-action" type="button" onClick={demo}>Try demo</button>
        </div>
      </section>

      <footer className="site-footer">
        <span>Smart Cricket</span>
        <span>Made by Abhijai Raghuvanshi</span>
        <nav aria-label="Footer">
          <button type="button" onClick={analyze}>Analyze</button>
          <a href="#technology">Technology</a>
          <a href="#privacy">Privacy</a>
          <a href="https://github.com/Abhijai10/Advanced-ML-Model-for-Smart-Cricket-Project">GitHub</a>
        </nav>
      </footer>
    </main>
  );
}

function OverviewPage(props: ShellProps) {
  const latest = props.history[0];
  const averageConfidence = props.history.length
    ? props.history.reduce((sum, row) => sum + (row.shot_confidence ?? 0), 0) / props.history.length
    : 0;
  const latestScore = latest?.technique_match_score ?? 0;
  const mostPracticed = mostPracticedShot(props.history);
  return (
    <div className="page-stack">
      <section className="app-hero-row">
        <div>
          <p className="product-kicker">Made by Abhijai Raghuvanshi</p>
          <h1>Ready for the next session?</h1>
          <p>Review one batting motion, keep the result honest, and build a practice history you can trust.</p>
        </div>
        <Link className="primary-action" to="/app/analyze">
          Analyze a shot
          <ArrowRight size={18} aria-hidden="true" />
        </Link>
      </section>
      <section className="metric-grid" aria-label="Practice summary">
        <MetricCard label="Total analyses" value={props.history.length} />
        <MetricCard label="Latest technique" value={latestScore} />
        <MetricCard label="Average confidence" value={averageConfidence * 100} suffix="%" />
        <MetricCard label="Most practiced shot" text={mostPracticed || "No sessions yet"} />
      </section>
      <section className="content-grid">
        <SpotlightCard className="panel-card">
          <h2>Quick insight</h2>
          <p>{latest ? latest.coaching_tips?.[0] || "Latest result saved, but no coaching tip was available." : "Analyze your first shot to see a practice focus here."}</p>
        </SpotlightCard>
        <SpotlightCard className="panel-card">
          <h2>Recent analyses</h2>
          <RecentList rows={props.history.slice(0, 5)} />
        </SpotlightCard>
      </section>
    </div>
  );
}

function AnalyzePage(props: ShellProps) {
  return (
    <div className="page-stack">
      <section className="page-title-row">
        <div>
          <h1>Analysis workspace</h1>
          <p>Capture one clean batting motion. The workflow shows user-visible state only.</p>
        </div>
      </section>
      <section className="analysis-workspace">
        <div className="analysis-primary">
          <CameraAnalysis
            accessToken={props.session?.access_token}
            capabilities={props.capabilities}
            onResult={props.onResult}
            onWorkflowStep={props.setWorkflowStep}
          />
        </div>
        <aside className="analysis-rail">
          <WorkflowPanel activeStep={props.workflowStep} capabilities={props.capabilities} />
          <FeedbackPanel
            result={props.latestResult}
            accessToken={props.session?.access_token}
            capabilities={props.capabilities}
          />
        </aside>
      </section>
    </div>
  );
}

function HistoryPage(props: ShellProps) {
  return (
    <div className="page-stack">
      <section className="page-title-row">
        <div>
          <h1>History</h1>
          <p>Review saved, unsaved, and demo analyses without mixing trust states.</p>
        </div>
      </section>
      {props.historyError ? <p className="warning-banner" role="status">{props.historyError}</p> : null}
      {props.isLoadingHistory ? (
        <div className="history-empty">Loading history...</div>
      ) : (
        <Suspense fallback={<div className="history-empty">Loading trends...</div>}>
          <ShotCharts rows={props.history} onRefresh={props.onRefreshHistory} />
        </Suspense>
      )}
    </div>
  );
}

function AnalysisDetail({ history }: { history: AnalysisSession[] }) {
  const { id } = useParams();
  const row = history.find((item) => item.id === id);
  if (!row) {
    return (
      <div className="page-stack">
        <div className="history-empty">This analysis is not available in the current session.</div>
      </div>
    );
  }
  return (
    <div className="page-stack">
      <section className="page-title-row">
        <div>
          <h1>{shotName(row.predicted_shot)}</h1>
          <p>{new Date(row.created_at).toLocaleString()} · {row.history_status ?? "unverified"}</p>
        </div>
      </section>
      <div className="metric-grid">
        <MetricCard label="Confidence" value={(row.shot_confidence ?? 0) * 100} suffix="%" />
        <MetricCard label="Technique" value={row.technique_match_score ?? 0} />
        <MetricCard label="Duration" value={row.shot_duration_seconds ?? 0} suffix="s" />
      </div>
      <SpotlightCard className="panel-card">
        <h2>Practice focus</h2>
        <p>{row.coaching_tips?.[0] || "No coaching tip was stored for this analysis."}</p>
      </SpotlightCard>
    </div>
  );
}

function SettingsPage(props: ShellProps) {
  return (
    <div className="page-stack settings-page">
      <section className="page-title-row">
        <div>
          <h1>Settings & privacy</h1>
          <p>Account, data-use, and environment capabilities for this workspace.</p>
        </div>
      </section>
      <div className="settings-grid">
        <SpotlightCard className="panel-card">
          <h2>Account</h2>
          <p>{props.session?.user.email ?? "Demo mode. No account is connected in this preview."}</p>
        </SpotlightCard>
        <SpotlightCard className="panel-card">
          <h2>Privacy & data</h2>
          <p>Clip retention is optional. Retained evidence is only for the human-review workflow and can be withdrawn or deleted where backend storage is configured.</p>
        </SpotlightCard>
        <SpotlightCard className="panel-card">
          <h2>Model improvement</h2>
          <p>{props.capabilities?.model_improvement_enabled ? "Available when evidence retention is enabled and selected before analysis." : "Model-improvement participation is not available in this environment."}</p>
        </SpotlightCard>
        <SpotlightCard className="panel-card">
          <h2>Technical</h2>
          <dl className="settings-list">
            <div><dt>Auth required</dt><dd>{props.capabilities?.auth_required ? "Yes" : "No"}</dd></div>
            <div><dt>Feedback</dt><dd>{props.capabilities?.feedback_enabled ? "Enabled" : "Unavailable"}</dd></div>
            <div><dt>TTS</dt><dd>{props.capabilities?.tts_provider ?? "Unknown"}</dd></div>
            <div><dt>Max recording</dt><dd>{props.capabilities?.max_recording_duration_seconds ?? 20}s</dd></div>
          </dl>
        </SpotlightCard>
      </div>
    </div>
  );
}

function WorkflowPanel({ activeStep, capabilities }: { activeStep: number; capabilities: Capabilities | null }) {
  return (
    <SpotlightCard className="workflow-panel">
      <h2>Workflow</h2>
      <Stepper steps={["Capture", "Analyze", "Review"]} active={activeStep} />
      <div className="guidance-list">
        <span><CheckCircle2 size={16} aria-hidden="true" />Full body visible</span>
        <span><CheckCircle2 size={16} aria-hidden="true" />One shot per clip</span>
        <span><CheckCircle2 size={16} aria-hidden="true" />Side-on angle preferred</span>
        <span><CheckCircle2 size={16} aria-hidden="true" />Under {capabilities?.max_recording_duration_seconds ?? 20}s</span>
      </div>
    </SpotlightCard>
  );
}

function MetricCard({ label, value, suffix = "", text }: { label: string; value?: number; suffix?: string; text?: string }) {
  return (
    <SpotlightCard className="metric-card">
      <span>{label}</span>
      <strong>{text ?? <CountUp value={value ?? 0} suffix={suffix} />}</strong>
    </SpotlightCard>
  );
}

function RecentList({ rows }: { rows: AnalysisSession[] }) {
  if (!rows.length) {
    return <p className="empty-copy">Your analyzed shots will appear here.</p>;
  }
  return (
    <AnimatedList className="recent-list">
      {rows.map((row) => (
        <Link to={`/app/history/${row.id}`} className="recent-row" key={row.id}>
          <BarChart3 size={17} aria-hidden="true" />
          <span>
            <strong>{shotName(row.predicted_shot)}</strong>
            <small>{new Date(row.created_at).toLocaleDateString()} · {row.history_status ?? "unverified"}</small>
          </span>
          <em>{row.technique_match_score ? Math.round(row.technique_match_score) : "—"}</em>
        </Link>
      ))}
    </AnimatedList>
  );
}

function mostPracticedShot(rows: AnalysisSession[]): string {
  const counts = new Map<string, number>();
  for (const row of rows) {
    const label = row.predicted_shot ?? "unknown";
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }
  const best = Array.from(counts).sort((a, b) => b[1] - a[1])[0]?.[0];
  return best ? shotName(best) : "";
}

export default App;
