# SmartCricket UI Data Mapping

This mapping preserves the approved UI while replacing sample data only with
values that exist in the FastAPI API or user-isolated Supabase tables.

| UI area | Source | Fields | Status |
| --- | --- | --- | --- |
| Player name | `profiles` | `display_name` | Available |
| Total sessions and recent activity | `analysis_sessions` filtered by authenticated `user_id` | `id`, `created_at`, `predicted_shot`, `shot_duration_seconds` | Available |
| Technique score | `analysis_sessions` / `POST /analyze` | `technique_match_score` | Available |
| Detected shot and confidence | `POST /analyze` | `predicted_shot`, `shot_confidence`, `segmentation`, `timing` | Available after a recorded/uploaded clip completes |
| Coaching feedback and audio state | `POST /analyze` | `coaching_tips`, `detailed_feedback`, `spoken_feedback`, `voice_output` | Available |
| Shot distribution | `analysis_sessions` | aggregate `predicted_shot` | Available per completed analysis, not per video frame |
| Confidence trend | `analysis_sessions` | `shot_confidence`, `created_at` | Available per completed analysis |
| True prediction/class accuracy | `analysis_feedback` | `prediction_was_correct`, `corrected_shot` | Not available as an aggregate API contract; no fabricated percentage is shown |
| Practice streak | `analysis_sessions` | distinct `created_at` dates | Available client-side |
| Skeleton overlay | Raw MediaPipe pose results | landmarks are not included in `AnalyzeResponse` | Blocked: backend returns final analysis only |
| Live frame-by-frame inference | FastAPI | only `POST /analyze` accepts completed media | Blocked: no streaming/WebSocket endpoint |

RLS on `profiles` and `analysis_sessions` constrains all direct Supabase reads to
the authenticated user. The browser never receives a service-role credential.
