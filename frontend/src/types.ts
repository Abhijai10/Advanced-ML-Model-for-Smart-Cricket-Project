export type AnalysisResponse = {
  predicted_shot: string;
  shot_confidence: number;
  technique_match_score: number;
  detected_issues: Array<Record<string, unknown>>;
  coaching_tips: string[];
  detailed_feedback: string;
  spoken_feedback: string;
  analysis_quality?: {
    status?: "ok" | "uncertain" | "insufficient_quality";
    reasons?: string[];
  };
  debug_metadata: Record<string, unknown>;
  source_metadata: Record<string, unknown>;
  prediction: {
    class_probabilities?: Record<string, number>;
  };
  segmentation: {
    start_frame: number | null;
    end_frame: number | null;
    peak_frame: number | null;
    prediction_trigger_frame: number | null;
    completed: boolean;
    completion_reason: string | null;
    trigger_count: number;
  };
  timing?: {
    start_seconds?: number | null;
    end_seconds?: number | null;
    duration_seconds?: number | null;
    source?: string;
  };
  voice_output: {
    available: boolean;
    provider: string;
    audio_path: string;
    audio_url?: string | null;
    audio_filename?: string | null;
    audio_format: string;
    audio_bytes: number;
    is_spoken_tts?: boolean;
  };
  api_metadata: Record<string, unknown>;
};

export type FeedbackPayload = {
  analysis_session_id?: string | null;
  client_analysis_id?: string | null;
  clip_hash: string;
  predicted_shot: string;
  prediction_was_correct: "correct" | "incorrect" | "unsure";
  corrected_shot?: string | null;
  technique_feedback_rating?: number | null;
  tip_flags: Array<"useful" | "incorrect" | "unsafe" | "unclear">;
  notes?: string | null;
  consent_to_model_improvement: boolean;
  model_version?: string | null;
  pipeline_version?: string | null;
};

export type FeedbackResponse = {
  status: string;
  feedback_id: string;
  accepted_for_review: boolean;
  stored: boolean;
  duplicate_clip_hash: boolean;
  request_id: string;
  message: string;
};

export type AnalysisSession = {
  id: string;
  user_id: string;
  video_file_name: string;
  predicted_shot: string | null;
  shot_confidence: number | null;
  technique_match_score: number | null;
  shot_start_frame: number | null;
  shot_end_frame: number | null;
  shot_duration_seconds: number | null;
  spoken_feedback: string | null;
  coaching_tips: string[];
  full_result: AnalysisResponse | Record<string, unknown>;
  created_at: string;
};

export type ShotChartDatum = {
  shot: string;
  count: number;
  seconds: number;
};
