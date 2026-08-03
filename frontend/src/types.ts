export type AnalysisResponse = {
  predicted_shot: string;
  shot_confidence: number;
  technique_match_score: number;
  detected_issues: Array<Record<string, unknown>>;
  coaching_tips: string[];
  detailed_feedback: string;
  spoken_feedback: string;
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
  voice_output: {
    available: boolean;
    provider: string;
    audio_path: string;
    audio_format: string;
    audio_bytes: number;
  };
  api_metadata: Record<string, unknown>;
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
