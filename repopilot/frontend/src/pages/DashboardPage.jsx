import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from "chart.js";
import { useEffect, useState } from "react";
import { Bar, Line } from "react-chartjs-2";
import { listEvalRuns, listProjects } from "../api";
import StatTile from "../components/StatTile";

ChartJS.register(CategoryScale, LinearScale, BarElement, LineElement, PointElement, Legend, Tooltip);

// Validated categorical slots (see dataviz skill palette): blue, orange, aqua.
const COLOR_BLUE = "#2a78d6";
const COLOR_ORANGE = "#eb6834";
const COLOR_AQUA = "#1baf7a";
const GRIDLINE = "#e1e0d9";
const MUTED = "#898781";

const baseGrid = { color: GRIDLINE, drawTicks: false };
const baseTicks = { color: MUTED, font: { size: 11 } };

export default function DashboardPage() {
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState("");
  const [runs, setRuns] = useState([]);

  useEffect(() => {
    listProjects().then((data) => {
      setProjects(data);
      if (data.length > 0) setProjectId(data[0].id);
    });
  }, []);

  useEffect(() => {
    if (!projectId) return;
    listEvalRuns(projectId).then((data) => setRuns([...data].reverse())); // chronological
  }, [projectId]);

  const latest = runs[runs.length - 1];
  const prev = runs[runs.length - 2];
  const delta = (key) => (latest && prev ? (latest[key] - prev[key]).toFixed(2) : null);

  const labels = runs.map((r) => new Date(r.created_at).toLocaleDateString());

  const qualityData = {
    labels,
    datasets: [
      { label: "precision@k", data: runs.map((r) => r.precision_at_k), backgroundColor: COLOR_BLUE },
      { label: "MRR", data: runs.map((r) => r.mrr), backgroundColor: COLOR_ORANGE },
      { label: "judge score (÷5)", data: runs.map((r) => r.judge_score_avg / 5), backgroundColor: COLOR_AQUA },
    ],
  };

  const latencyData = {
    labels,
    datasets: [
      {
        label: "avg latency (ms)",
        data: runs.map((r) => r.avg_latency_ms),
        borderColor: COLOR_BLUE,
        backgroundColor: COLOR_BLUE,
        tension: 0.25,
        pointRadius: 4,
      },
    ],
  };

  const costData = {
    labels,
    datasets: [
      {
        label: "avg cost per query (USD)",
        data: runs.map((r) => r.avg_cost_usd),
        borderColor: COLOR_ORANGE,
        backgroundColor: COLOR_ORANGE,
        tension: 0.25,
        pointRadius: 4,
      },
    ],
  };

  const chartOpts = (yLabel) => ({
    responsive: true,
    plugins: { legend: { labels: { color: "#52514e", font: { size: 11 } } } },
    scales: {
      x: { grid: { display: false }, ticks: baseTicks },
      y: {
        grid: baseGrid,
        ticks: baseTicks,
        title: { display: true, text: yLabel, color: MUTED, font: { size: 11 } },
        beginAtZero: true,
      },
    },
  });

  return (
    <div>
      <div className="mb-4 flex items-center gap-2">
        <label className="text-sm text-slate-600">Project:</label>
        <select
          className="border border-slate-300 rounded-md px-2 py-1 text-sm"
          value={projectId}
          onChange={(e) => setProjectId(e.target.value)}
        >
          {projects.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {runs.length === 0 ? (
        <p className="text-sm text-slate-500">
          No eval runs yet. Run <code className="bg-slate-100 px-1 rounded">scripts/run_eval.py</code> to populate this dashboard.
        </p>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
            <StatTile label="Precision@k" value={latest.precision_at_k.toFixed(2)} sub={delta("precision_at_k") && `${delta("precision_at_k")} vs prior run`} />
            <StatTile label="MRR" value={latest.mrr.toFixed(2)} sub={delta("mrr") && `${delta("mrr")} vs prior run`} />
            <StatTile label="Judge score" value={`${latest.judge_score_avg.toFixed(1)} / 5`} sub={delta("judge_score_avg") && `${delta("judge_score_avg")} vs prior run`} />
            <StatTile label="Avg latency" value={`${latest.avg_latency_ms.toFixed(0)} ms`} />
            <StatTile label="Avg cost / query" value={`$${latest.avg_cost_usd.toFixed(5)}`} />
          </div>

          <div className="bg-white border border-slate-200 rounded-xl p-4 mb-6">
            <h3 className="text-sm font-medium text-slate-700 mb-3">Retrieval & answer quality across eval runs</h3>
            <Bar data={qualityData} options={chartOpts("score (0-1)")} />
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <h3 className="text-sm font-medium text-slate-700 mb-3">Latency trend</h3>
              <Line data={latencyData} options={chartOpts("ms")} />
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <h3 className="text-sm font-medium text-slate-700 mb-3">Cost trend</h3>
              <Line data={costData} options={chartOpts("USD")} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
