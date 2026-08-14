import { expect, test } from "@playwright/test";

const analysisResponse = {
  predicted_shot: "cover_drive",
  shot_confidence: 0.82,
  technique_match_score: 74,
  detected_issues: [],
  coaching_tips: ["Keep the head still."],
  detailed_feedback: "Good shape.",
  spoken_feedback: "Keep the head still.",
  analysis_quality: { status: "ok", reasons: ["Input quality and model confidence meet thresholds."] },
  debug_metadata: { model_version: "phase8-best" },
  source_metadata: {},
  prediction: { class_probabilities: { cover_drive: 0.82, pull_shot: 0.18 } },
  segmentation: {
    start_frame: 6,
    end_frame: 30,
    peak_frame: 18,
    prediction_trigger_frame: 30,
    completed: true,
    completion_reason: "test",
    trigger_count: 1,
  },
  timing: { duration_seconds: 1.25 },
  voice_output: {
    available: false,
    provider: "unavailable",
    audio_path: "",
    audio_url: null,
    audio_format: "none",
    audio_bytes: 0,
    is_spoken_tts: false,
  },
  api_metadata: {
    analysis_session_id: "11111111-1111-1111-1111-111111111111",
    clip_hash: "a".repeat(64),
    pipeline_version: "phase12",
    analysis_persistence: { attempted: true, stored: true, storage_status: "stored" },
    evidence_retention: { requested: false, retained: false, status: "not_requested" },
  },
};

test("demo upload review, mocked analysis, and feedback flow", async ({ page }) => {
  await page.route("**/capabilities", async (route) => {
    await route.fulfill({
      json: {
        auth_required: false,
        feedback_enabled: true,
        model_improvement_enabled: false,
        evidence_retention_enabled: false,
        tts_provider: "signed_audio",
        audio_storage_backend: "local",
        max_upload_bytes: 262144000,
        max_recording_duration_seconds: 20,
        accepted_video_extensions: [".mp4", ".mov", ".webm"],
      },
    });
  });
  await page.route("**/analyze", async (route) => {
    await route.fulfill({ json: analysisResponse });
  });
  await page.route("**/feedback", async (route) => {
    await route.fulfill({
      json: {
        status: "stored",
        storage_status: "stored",
        feedback_id: "feedback-1",
        accepted_for_review: false,
        stored: true,
        duplicate_clip_hash: false,
        request_id: "request-1",
        message: "Feedback was saved as metadata only because model-improvement consent was not granted.",
      },
    });
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: /understand the shot/i })).toBeVisible();
  await page.getByRole("button", { name: /analyze a shot/i }).first().click();
  await expect(page).toHaveURL(/\/app\/analyze$/);
  await expect(page.getByRole("heading", { name: /analysis workspace/i })).toBeVisible();

  await page.getByLabel(/upload clip/i).setInputFiles({
    name: "shot.webm",
    mimeType: "video/webm",
    buffer: Buffer.from("fake-webm-for-ui-test"),
  });
  await expect(page.getByText(/review this take/i)).toBeVisible();

  await page.getByRole("button", { name: /analyze clip/i }).click();
  await expect(page.getByText(/cover drive/i).first()).toBeVisible();
  await expect(page.getByText(/audio feedback isn't available/i)).toBeVisible();

  await page.getByRole("radio", { name: "incorrect" }).check();
  await page.getByLabel(/correct shot/i).selectOption("pull_shot");
  await expect(page.getByText(/Feedback will be saved outside training review/i)).toBeVisible();
  await expect(page.getByLabel(/human-reviewed model improvement/i)).toBeDisabled();
  await page.getByRole("button", { name: /save feedback/i }).click();
  await expect(page.getByRole("button", { name: /feedback saved/i })).toBeVisible();
});
