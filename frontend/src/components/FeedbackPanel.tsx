import { useState } from "react";
import { CheckCircle2, Send, Volume2 } from "lucide-react";
import { shotName } from "../lib/history";
import { resolveApiUrl, submitAnalysisFeedback } from "../lib/api";
import type { AnalysisResponse, FeedbackPayload } from "../types";

type FeedbackPanelProps = {
  result: AnalysisResponse | null;
  accessToken?: string;
};

const shotOptions = ["cover_drive", "defensive_shot", "pull_shot", "sweep_shot"];
const tipFlags: FeedbackPayload["tip_flags"] = ["useful", "incorrect", "unsafe", "unclear"];

export function FeedbackPanel({ result, accessToken }: FeedbackPanelProps) {
  const [correctness, setCorrectness] = useState<FeedbackPayload["prediction_was_correct"]>("unsure");
  const [correctedShot, setCorrectedShot] = useState("cover_drive");
  const [rating, setRating] = useState(3);
  const [flags, setFlags] = useState<FeedbackPayload["tip_flags"]>([]);
  const [consent, setConsent] = useState(false);
  const [notes, setNotes] = useState("");
  const [submitState, setSubmitState] = useState<"idle" | "submitting" | "done">("idle");
  const [submitError, setSubmitError] = useState("");

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
  const clipHash = typeof activeResult.api_metadata.clip_hash === "string" ? activeResult.api_metadata.clip_hash : "";

  function toggleFlag(flag: FeedbackPayload["tip_flags"][number]) {
    setFlags((current) => (current.includes(flag) ? current.filter((item) => item !== flag) : [...current, flag]));
  }

  async function submitFeedback(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!clipHash) {
      setSubmitError("This result is missing a clip hash, so feedback cannot be linked safely.");
      return;
    }
    setSubmitState("submitting");
    setSubmitError("");
    try {
      await submitAnalysisFeedback(
        {
          clip_hash: clipHash,
          predicted_shot: activeResult.predicted_shot,
          prediction_was_correct: correctness,
          corrected_shot: correctness === "incorrect" ? correctedShot : null,
          technique_feedback_rating: rating,
          tip_flags: flags,
          notes: notes || null,
          consent_to_model_improvement: consent,
          model_version:
            typeof activeResult.debug_metadata.model_version === "string" ? activeResult.debug_metadata.model_version : null,
          pipeline_version:
            typeof activeResult.api_metadata.pipeline_version === "string" ? activeResult.api_metadata.pipeline_version : null,
        },
        accessToken,
      );
      setSubmitState("done");
    } catch (err) {
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
          <div className="segmented-control" role="radiogroup" aria-label="Was the prediction correct?">
            {(["correct", "incorrect", "unsure"] as const).map((value) => (
              <button
                key={value}
                type="button"
                className={correctness === value ? "active" : ""}
                onClick={() => setCorrectness(value)}
              >
                {value}
              </button>
            ))}
          </div>
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
          <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} />
          Share this clip result for human-reviewed model improvement.
        </label>

        <button type="submit" className="primary-action compact" disabled={submitState !== "idle"}>
          {submitState === "done" ? <CheckCircle2 size={17} aria-hidden="true" /> : <Send size={17} aria-hidden="true" />}
          {submitState === "done" ? "Feedback sent" : submitState === "submitting" ? "Sending" : "Send feedback"}
        </button>
        {submitError ? <p className="error-banner">{submitError}</p> : null}
      </form>
    </aside>
  );
}
