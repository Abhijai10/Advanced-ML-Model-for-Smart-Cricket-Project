import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Activity, Lock, Mail, UserRound } from "lucide-react";
import { isSupabaseConfigured, supabase } from "../lib/supabase";

type AuthPanelProps = {
  onDemoMode: () => void;
};

export function AuthPanel({ onDemoMode }: AuthPanelProps) {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!supabase) {
      setStatus("Connect Supabase env values to enable secure login.");
      return;
    }
    setIsSubmitting(true);
    setStatus("");
    try {
      if (mode === "signup") {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: { data: { display_name: name } },
        });
        if (error) throw error;
        if (data.user) {
          await supabase.from("profiles").upsert({
            id: data.user.id,
            display_name: name || email.split("@")[0],
          });
        }
        setStatus("Account created. Check email confirmation settings in Supabase if sign-in is blocked.");
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      }
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Authentication failed.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function enterDemo() {
    onDemoMode();
    navigate("/app");
  }

  return (
    <main className="auth-shell">
      <section className="auth-intro" aria-labelledby="intro-title">
        <Link to="/" className="brand-lockup" aria-label="Smart Cricket home">
          <span className="brand-mark">
            <Activity size={20} aria-hidden="true" />
          </span>
          <span>Smart Cricket</span>
        </Link>
        <h1 id="intro-title">AI cricket shot analysis, built for practice review.</h1>
        <p>
          Record a batting motion, run the Smart Cricket model, and review the predicted shot,
          technique score, coaching feedback, voice output, and shot history in one focused app.
        </p>
        <div className="auth-metric-strip" aria-label="Preview capability summary">
          <span><strong>20s</strong>max clip</span>
          <span><strong>4</strong>shot classes</span>
          <span><strong>Opt-in</strong>data use</span>
        </div>
        <div className="creator-credit">Made by Abhijai Raghuvanshi</div>
      </section>

      <section className="auth-card" aria-label="Login form">
        <div className="auth-tabs" role="tablist" aria-label="Authentication mode">
          <button className={mode === "signin" ? "active" : ""} onClick={() => setMode("signin")} type="button">
            Sign in
          </button>
          <button className={mode === "signup" ? "active" : ""} onClick={() => setMode("signup")} type="button">
            Create account
          </button>
        </div>

        <form onSubmit={submit} className="auth-form">
          {mode === "signup" && (
            <label>
              <span>Name</span>
              <div className="input-wrap">
                <UserRound size={18} aria-hidden="true" />
                <input
                  autoComplete="name"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Abhijai Raghuvanshi"
                />
              </div>
            </label>
          )}
          <label>
            <span>Email</span>
            <div className="input-wrap">
              <Mail size={18} aria-hidden="true" />
              <input
                required
                autoComplete="email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
              />
            </div>
          </label>
          <label>
            <span>Password</span>
            <div className="input-wrap">
              <Lock size={18} aria-hidden="true" />
              <input
                required
                minLength={6}
                autoComplete={mode === "signin" ? "current-password" : "new-password"}
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Minimum 6 characters"
              />
            </div>
          </label>
          <button className="primary-action" type="submit" disabled={isSubmitting || !isSupabaseConfigured}>
            {isSubmitting ? "Working..." : mode === "signin" ? "Enter workspace" : "Create workspace"}
          </button>
          {!isSupabaseConfigured && (
            <p className="form-note">
              Account login is not configured in this preview. Demo mode remains available.
            </p>
          )}
          {status && <p className="form-note">{status}</p>}
        </form>

        <button className="secondary-action" type="button" onClick={enterDemo}>
          Preview app without login
        </button>
      </section>
    </main>
  );
}
