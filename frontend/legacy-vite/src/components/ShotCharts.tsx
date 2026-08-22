import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { buildChartData, shotName } from "../lib/history";
import type { AnalysisSession } from "../types";

type ShotChartsProps = {
  rows: AnalysisSession[];
  onRefresh?: () => Promise<void> | void;
};

function historyStatusLabel(row: AnalysisSession): string {
  if (row.history_status === "server_saved") return "Server saved";
  if (row.history_status === "local_demo") return "Local demo";
  if (row.history_status === "unsaved") return "Unsaved";
  return "Unverified";
}

const filters = [
  { value: "all", label: "All" },
  { value: "server_saved", label: "Server saved" },
  { value: "unsaved", label: "Unsaved" },
  { value: "local_demo", label: "Local demo" },
] as const;

type HistoryFilter = (typeof filters)[number]["value"];

function historyTrustNote(rows: AnalysisSession[]): string {
  if (rows.length === 0) {
    return "No analyses yet. Record or upload a clip to create the first result.";
  }
  const hasServer = rows.some((row) => row.history_status === "server_saved");
  const hasUnsaved = rows.some((row) => row.history_status === "unsaved");
  const hasDemo = rows.some((row) => row.history_status === "local_demo");
  if (hasServer && !hasUnsaved && !hasDemo) {
    return "These rows were loaded from trusted server history.";
  }
  if (hasUnsaved) {
    return "Some rows are local unsaved results because secure persistence was unavailable.";
  }
  if (hasDemo) {
    return "Demo rows are local-only and are not secure history.";
  }
  return "Rows without a trust label should be treated as unverified.";
}

export function ShotCharts({ rows, onRefresh }: ShotChartsProps) {
  const [filter, setFilter] = useState<HistoryFilter>("all");
  const filteredRows = useMemo(
    () => (filter === "all" ? rows : rows.filter((row) => row.history_status === filter)),
    [filter, rows],
  );
  const chartData = buildChartData(filteredRows);

  return (
    <section className="history-panel" aria-labelledby="history-title">
      <div className="panel-heading">
        <div>
          <h2 id="history-title">Shot history</h2>
          <p>{historyTrustNote(rows)}</p>
        </div>
        <div className="history-tools" aria-label="History controls">
          <label>
            Trust filter
            <select value={filter} onChange={(event) => setFilter(event.target.value as HistoryFilter)}>
              {filters.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
          {onRefresh ? (
            <button type="button" className="secondary-action compact" onClick={() => void onRefresh()}>
              <RefreshCw size={16} aria-hidden="true" />
              Refresh
            </button>
          ) : null}
        </div>
      </div>

      {chartData.length === 0 ? (
        <div className="history-empty">
          {rows.length === 0
            ? "No analyses yet. Record a shot or upload a clip to start the chart."
            : "No analyses match this trust filter."}
        </div>
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
        {filteredRows.slice(0, 8).map((row) => (
          <Link className="history-row" role="row" key={row.id} to={`/app/history/${row.id}`}>
            <span role="cell">{shotName(row.predicted_shot)}</span>
            <span role="cell">{row.technique_match_score ? Math.round(row.technique_match_score) : "—"}</span>
            <span role="cell">{row.shot_duration_seconds?.toFixed(2) ?? "0.00"}s</span>
            <span role="cell">{historyStatusLabel(row)}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}
