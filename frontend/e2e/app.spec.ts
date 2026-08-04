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
  api_metadata: { clip_hash: "a".repeat(64), pipeline_version: "phase12" },
};

test("demo upload review, mocked analysis, and feedback flow", async ({ page }) => {
  await page.route("**/analyze", async (route) => {
    await route.fulfill({ json: analysisResponse });
  });
  await page.route("**/feedback", async (route) => {
    await route.fulfill({
      json: {
        status: "accepted",
        feedback_id: "feedback-1",
        accepted_for_review: true,
        stored: false,
        duplicate_clip_hash: false,
        request_id: "request-1",
        message: "Feedback queued.",
      },
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: /preview app without login/i }).click();

  await page.getByLabel(/upload clip/i).setInputFiles({
    name: "shot.webm",
    mimeType: "video/webm",
    buffer: Buffer.from("fake-webm-for-ui-test"),
  });
  await expect(page.getByText(/review this take/i)).toBeVisible();

  await page.getByRole("button", { name: /analyze clip/i }).click();
  await expect(page.getByText(/cover drive/i).first()).toBeVisible();
  await expect(page.getByText(/audio unavailable/i)).toBeVisible();

  await page.getByRole("button", { name: "incorrect" }).click();
  await page.getByLabel(/correct shot/i).selectOption("pull_shot");
  await page.getByLabel(/share this clip result/i).check();
  await page.getByRole("button", { name: /send feedback/i }).click();
  await expect(page.getByRole("button", { name: /feedback sent/i })).toBeVisible();
});
