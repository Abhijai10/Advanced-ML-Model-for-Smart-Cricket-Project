import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ShotCharts } from "./ShotCharts";
import type { AnalysisSession } from "../types";

function row(id: string, history_status: AnalysisSession["history_status"]): AnalysisSession {
  return {
    id,
    user_id: "user-1",
    video_file_name: `${id}.webm`,
    predicted_shot: id === "server" ? "cover_drive" : "pull_shot",
    shot_confidence: 0.8,
    technique_match_score: 72,
    shot_start_frame: 1,
    shot_end_frame: 30,
    shot_duration_seconds: 1.2,
    spoken_feedback: "Keep the head still.",
    coaching_tips: ["Keep the head still."],
    full_result: {},
    created_at: "2026-08-12T00:00:00Z",
    history_status,
  };
}

describe("ShotCharts", () => {
  it("filters by history trust state and exposes refresh", async () => {
    const user = userEvent.setup();
    const onRefresh = vi.fn();
    render(<ShotCharts rows={[row("server", "server_saved"), row("local", "unsaved")]} onRefresh={onRefresh} />);

    expect(screen.getByText(/some rows are local unsaved/i)).toBeInTheDocument();
    expect(screen.getByText("Cover Drive")).toBeInTheDocument();
    expect(screen.getByText("Pull Shot")).toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/trust filter/i), "server_saved");

    expect(screen.getByText("Cover Drive")).toBeInTheDocument();
    expect(screen.queryByText("Pull Shot")).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /refresh/i }));
    expect(onRefresh).toHaveBeenCalledOnce();
  });

  it("shows a filtered empty state", async () => {
    const user = userEvent.setup();
    render(<ShotCharts rows={[row("local", "unsaved")]} />);

    await user.selectOptions(screen.getByLabelText(/trust filter/i), "server_saved");

    expect(screen.getByText(/no analyses match this trust filter/i)).toBeInTheDocument();
  });
});
