import { Volume2 } from "lucide-react";
import { shotName } from "../lib/history";
import { resolveApiUrl } from "../lib/api";
import type { AnalysisResponse } from "../types";

type FeedbackPanelProps = {
  result: AnalysisResponse | null;
};

export function FeedbackPanel({ result }: FeedbackPanelProps) {
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

  const probabilityEntries = Object.entries(result.prediction.class_probabilities ?? {});
  const audioUrl = result.voice_output.audio_url ? resolveApiUrl(result.voice_output.audio_url) : "";
  const duration = result.timing?.duration_seconds;

  return (
    <aside className="feedback-panel" aria-label="Analysis feedback">
      <div className="result-topline">
        <span>Prediction</span>
        <strong>{shotName(result.predicted_shot)}</strong>
      </div>

      <div className="score-grid">
        <div>
          <span>Confidence</span>
          <strong>{Math.round(result.shot_confidence * 100)}%</strong>
        </div>
        <div>
          <span>Technique</span>
          <strong>{Math.round(result.technique_match_score)}</strong>
        </div>
      </div>

      <section className="mini-section">
        <h3>Shot segment</h3>
        <dl className="segment-list">
          <div>
            <dt>Start</dt>
            <dd>{result.segmentation.start_frame ?? "Waiting"}</dd>
          </div>
          <div>
            <dt>End</dt>
            <dd>{result.segmentation.end_frame ?? "Waiting"}</dd>
          </div>
          <div>
            <dt>Duration</dt>
            <dd>{typeof duration === "number" ? `${duration.toFixed(2)}s` : "Unavailable"}</dd>
          </div>
        </dl>
      </section>

      <section className="mini-section">
        <h3>Coaching tips</h3>
        <ul className="tips-list">
          {result.coaching_tips.map((tip) => (
            <li key={tip}>{tip}</li>
          ))}
        </ul>
      </section>

      <section className="spoken-block">
        <div>
          <Volume2 size={18} aria-hidden="true" />
          <h3>{result.voice_output.is_spoken_tts === false ? "Audio cue" : "Spoken feedback"}</h3>
        </div>
        <p>{result.spoken_feedback}</p>
        {audioUrl ? (
          <audio controls src={audioUrl}>
            Your browser does not support audio playback.
          </audio>
        ) : null}
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
    </aside>
  );
}
