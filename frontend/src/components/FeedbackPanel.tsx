import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Send, Volume2 } from "lucide-react";
import { shotName } from "../lib/history";
import { resolveApiUrl, submitAnalysisFeedback } from "../lib/api";
import type { AnalysisResponse, Capabilities, EvidenceRetentionState, FeedbackPayload } from "../types";

type FeedbackPanelProps = {
  result: AnalysisResponse | null;
  accessToken?: string;
  capabilities?: Capabilities | null;
};

const shotOptions = ["cover_drive", "defensive_shot", "pull_shot", "sweep_shot"];
const tipFlags: FeedbackPayload["tip_flags"] = ["useful", "incorrect", "unsafe", "unclear"];

export function FeedbackPanel({ result, accessToken, capabilities }: FeedbackPanelProps) {
  const [correctness, setCorrectness] = useState<FeedbackPayload["prediction_was_correct"]>("unsure");
  const [correctedShot, setCorrectedShot] = useState("cover_drive");
  const [rating, setRating] = useState(3);
  const [flags, setFlags] = useState<FeedbackPayload["tip_flags"]>([]);
  const [consent, setConsent] = useState(false);
  const [notes, setNotes] = useState("");
  const [submitState, setSubmitState] = useState<"idle" | "submitting" | "done">("idle");
  const [storageMessage, setStorageMessage] = useState("");
  const [storageStatus, setStorageStatus] = useState("");
  const [submitError, setSubmitError] = useState("");
  const activeSubmitKeyRef = useRef("");
  const resultKey = result
    ? (typeof result.api_metadata.analysis_session_id === "string" ? result.api_metadata.analysis_session_id : "") ||
      (typeof result.api_metadata.request_id === "string" ? result.api_metadata.request_id : "") ||
      (typeof result.api_metadata.clip_hash === "string" ? result.api_metadata.clip_hash : "")
    : "";

  useEffect(() => {
    setCorrectness("unsure");
    setCorrectedShot("cover_drive");
    setRating(3);
    setFlags([]);
    setConsent(false);
    setNotes("");
    setSubmitState("idle");
    setStorageMessage("");
    setStorageStatus("");
    setSubmitError("");
    activeSubmitKeyRef.current = resultKey;
  }, [resultKey]);

  if (!result) {
    return (
      <aside className="feedback-panel" aria-label="Analysis feedback">
        <h2>Coach panel</h2>
        <p className="empty-copy">
          Your prediction, technique score, shot timing, coaching tips, and spoken feedback will appear here after analysis.
        </p>
      </aside>
    );
  }

  const activeResult = result;
  const probabilityEntries = Object.entries(activeResult.prediction.class_probabilities ?? {});
  const audioUrl = activeResult.voice_output.audio_url ? resolveApiUrl(activeResult.voice_output.audio_url) : "";
  const duration = activeResult.timing?.duration_seconds;
  const qualityStatus = activeResult.analysis_quality?.status ?? "ok";
  const qualityLabel =
    qualityStatus === "insufficient_quality" ? "Needs clearer video" : qualityStatus === "uncertain" ? "Uncertain" : "Ready";
  const analysisSessionId =
    typeof activeResult.api_metadata.analysis_session_id === "string" ? activeResult.api_metadata.analysis_session_id : "";
  const persistence = activeResult.api_metadata.analysis_persistence as
    | { attempted?: boolean; stored?: boolean; storage_status?: string; error_code?: string | null }
    | undefined;
  const evidence = (activeResult.api_metadata.evidence_retention ?? {}) as EvidenceRetentionState;
  const canConsentForModelImprovement = Boolean(accessToken && capabilities?.model_improvement_enabled && evidence.retained);
  const evidenceLabel = evidence.retained
    ? `Evidence retained securely${evidence.retention_expires_at ? ` until ${new Date(evidence.retention_expires_at).toLocaleDateString()}` : ""}.`
    : evidence.requested
      ? "Evidence retention failed or was unavailable; feedback can be saved, but it will not enter model training review."
      : "Clip evidence was not retained. Feedback is product-quality feedback only.";
  const persistenceLabel = persistence?.stored
    ? "Analysis saved to secure history."
    : persistence?.attempted
      ? "Analysis completed, but secure history could not be saved."
      : "Analysis completed in local/demo mode; feedback requires a verified saved analysis.";

  function toggleFlag(flag: FeedbackPayload["tip_flags"][number]) {
    setFlags((current) => (current.includes(flag) ? current.filter((item) => item !== flag) : [...current, flag]));
  }

  async function submitFeedback(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!analysisSessionId) {
      setSubmitError("Sign in and save a verified analysis before sending feedback.");
      return;
    }
    const submitKey = resultKey;
    activeSubmitKeyRef.current = submitKey;
    setSubmitState("submitting");
    setSubmitError("");
    setStorageMessage("");
    try {
      const response = await submitAnalysisFeedback(
        {
          analysis_session_id: analysisSessionId,
          prediction_was_correct: correctness,
          corrected_shot: correctness === "incorrect" ? correctedShot : null,
          technique_feedback_rating: rating,
          tip_flags: flags,
          notes: notes || null,
          consent_to_model_improvement: canConsentForModelImprovement && consent,
        },
        accessToken,
      );
      if (activeSubmitKeyRef.current !== submitKey) return;
      if (!response.stored && response.storage_status !== "duplicate") {
        throw new Error(response.message || "Feedback was not saved.");
      }
      setStorageStatus(response.storage_status);
      setStorageMessage(response.message);
      setSubmitState("done");
    } catch (err) {
      if (activeSubmitKeyRef.current !== submitKey) return;
      setSubmitError(err instanceof Error ? err.message : "Feedback could not be submitted.");
      setSubmitState("idle");
    }
  }

  return (
    <aside className="feedback-panel" aria-label="Analysis feedback">
      <div className="result-topline">
        <span>Prediction</span>
        <strong>{shotName(activeResult.predicted_shot)}</strong>
        <em>{qualityLabel}</em>
      </div>

      <div className="score-grid">
        <div>
          <span>Confidence</span>
          <strong>{Math.round(activeResult.shot_confidence * 100)}%</strong>
        </div>
        <div>
          <span>Technique</span>
          <strong>{Math.round(activeResult.technique_match_score)}</strong>
        </div>
      </div>

      <section className="mini-section">
        <h3>Shot segment</h3>
        <dl className="segment-list">
          <div>
            <dt>Start</dt>
            <dd>{activeResult.segmentation.start_frame ?? "Waiting"}</dd>
          </div>
          <div>
            <dt>End</dt>
            <dd>{activeResult.segmentation.end_frame ?? "Waiting"}</dd>
          </div>
          <div>
            <dt>Duration</dt>
            <dd>{typeof duration === "number" ? `${duration.toFixed(2)}s` : "Unavailable"}</dd>
          </div>
        </dl>
      </section>

      <section className="mini-section">
        <h3>Coaching tips</h3>
        {activeResult.analysis_quality?.reasons?.length ? (
          <p className="quality-note">{activeResult.analysis_quality.reasons[0]}</p>
        ) : null}
        <ul className="tips-list">
          {activeResult.coaching_tips.map((tip) => (
            <li key={tip}>{tip}</li>
          ))}
        </ul>
      </section>

      <section className="spoken-block">
        <div>
          <Volume2 size={18} aria-hidden="true" />
          <h3>{activeResult.voice_output.is_spoken_tts === false ? "Audio cue" : "Spoken feedback"}</h3>
        </div>
        <p>{activeResult.spoken_feedback}</p>
        {audioUrl ? (
          <audio controls src={audioUrl}>
            Your browser does not support audio playback.
          </audio>
        ) : (
          <span className="audio-fallback">Audio unavailable. Text feedback remains available.</span>
        )}
      </section>

      <section className="mini-section" aria-live="polite">
        <h3>Storage state</h3>
        <p className={persistence?.stored ? "quality-note" : "warning-note"}>{persistenceLabel}</p>
        <p className={evidence.retained ? "quality-note" : "warning-note"}>{evidenceLabel}</p>
      </section>

      {probabilityEntries.length > 0 && (
        <section className="mini-section">
          <h3>Class probabilities</h3>
          <div className="probability-list">
            {probabilityEntries.map(([label, value]) => (
              <div key={label}>
                <span>{shotName(label)}</span>
                <meter min={0} max={1} value={value} />
                <strong>{Math.round(value * 100)}%</strong>
              </div>
            ))}
          </div>
        </section>
      )}

      <form className="feedback-form" onSubmit={submitFeedback}>
        <div className="mini-section">
          <h3>Prediction check</h3>
          <fieldset className="radio-card-group">
            <legend>Was the prediction correct?</legend>
            {(["correct", "incorrect", "unsure"] as const).map((value) => (
              <label key={value} className={correctness === value ? "active" : ""}>
                <input
                  type="radio"
                  name="prediction-correctness"
                  value={value}
                  checked={correctness === value}
                  onChange={() => setCorrectness(value)}
                />
                {value}
              </label>
            ))}
          </fieldset>
        </div>

        {correctness === "incorrect" && (
          <label className="compact-field">
            Correct shot
            <select value={correctedShot} onChange={(event) => setCorrectedShot(event.target.value)}>
              {shotOptions.map((shot) => (
                <option key={shot} value={shot}>
                  {shotName(shot)}
                </option>
              ))}
            </select>
          </label>
        )}

        <label className="compact-field">
          Technique feedback rating
          <input
            type="range"
            min="1"
            max="5"
            value={rating}
            onChange={(event) => setRating(Number(event.target.value))}
          />
          <span>{rating}/5</span>
        </label>

        <div className="flag-grid" aria-label="Tip feedback flags">
          {tipFlags.map((flag) => (
            <label key={flag}>
              <input type="checkbox" checked={flags.includes(flag)} onChange={() => toggleFlag(flag)} />
              {flag}
            </label>
          ))}
        </div>

        <label className="compact-field">
          Notes
          <textarea value={notes} onChange={(event) => setNotes(event.target.value)} maxLength={2000} />
        </label>

        <label className="consent-row">
          <span id="feedback-consent-details">
            {capabilities?.model_improvement_enabled === false
              ? "Model-improvement participation is disabled in this environment. Feedback will be saved outside training review."
              : evidence.retained
                ? "This sends judgement and notes for human review only when retained evidence exists. No automatic retraining occurs."
                : "No retained evidence is available for this analysis, so feedback cannot enter model-training review."}
          </span>
          <input
            type="checkbox"
            checked={consent}
            disabled={!canConsentForModelImprovement}
            onChange={(event) => setConsent(event.target.checked)}
          />
          Use this feedback for human-reviewed model improvement if eligible evidence was retained.
        </label>

        <button type="submit" className="primary-action compact" disabled={submitState !== "idle"}>
          {submitState === "done" ? <CheckCircle2 size={17} aria-hidden="true" /> : <Send size={17} aria-hidden="true" />}
          {submitState === "done"
            ? storageStatus === "duplicate"
              ? "Already saved"
              : "Feedback saved"
            : submitState === "submitting"
              ? "Saving"
              : "Save feedback"}
        </button>
        {storageMessage ? <p className="success-banner" role="status" aria-live="polite">{storageMessage}</p> : null}
        {submitError ? <p className="error-banner" role="alert">{submitError}</p> : null}
      </form>
    </aside>
  );
}
