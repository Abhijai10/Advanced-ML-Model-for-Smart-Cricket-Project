import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { buildChartData, shotName } from "../lib/history";
import type { AnalysisSession } from "../types";

type ShotChartsProps = {
  rows: AnalysisSession[];
};

function historyStatusLabel(row: AnalysisSession): string {
  if (row.history_status === "server_saved") return "Server saved";
  if (row.history_status === "local_demo") return "Local demo";
  if (row.history_status === "unsaved") return "Unsaved";
  return "Unverified";
}

export function ShotCharts({ rows }: ShotChartsProps) {
  const chartData = buildChartData(rows);

  return (
    <section className="history-panel" aria-labelledby="history-title">
      <div className="panel-heading">
        <div>
          <h2 id="history-title">Shot history</h2>
          <p>Track which shots were played and how long the detected segments lasted.</p>
        </div>
      </div>

      {chartData.length === 0 ? (
        <div className="history-empty">No saved analyses yet. Record a shot to start the chart.</div>
      ) : (
        <div className="chart-wrap">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 8 }}>
              <CartesianGrid stroke="oklch(0.88 0.01 110)" vertical={false} />
              <XAxis dataKey="shot" tickLine={false} axisLine={false} />
              <YAxis yAxisId="left" tickLine={false} axisLine={false} allowDecimals={false} />
              <YAxis yAxisId="right" orientation="right" tickLine={false} axisLine={false} />
              <Tooltip formatter={(value, name) => [value, name === "count" ? "Shots" : "Seconds"]} />
              <Bar yAxisId="left" dataKey="count" name="Shots" fill="oklch(0.35 0.075 110)" radius={[6, 6, 0, 0]} />
              <Bar yAxisId="right" dataKey="seconds" name="Seconds" fill="oklch(0.55 0.16 28)" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="history-table" role="table" aria-label="Recent analyses">
        <div className="history-row header" role="row">
          <span role="columnheader">Shot</span>
          <span role="columnheader">Score</span>
          <span role="columnheader">Duration</span>
          <span role="columnheader">Trust</span>
        </div>
        {rows.slice(0, 6).map((row) => (
          <div className="history-row" role="row" key={row.id}>
            <span role="cell">{shotName(row.predicted_shot)}</span>
            <span role="cell">{row.technique_match_score ? Math.round(row.technique_match_score) : "—"}</span>
            <span role="cell">{row.shot_duration_seconds?.toFixed(2) ?? "0.00"}s</span>
            <span role="cell">{historyStatusLabel(row)}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
