import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listEvalRuns, listProjects } from "../api";

const GITHUB_URL = "https://github.com/Shri46/repopilot";

const PILLARS = [
  {
    title: "Hybrid retrieval",
    body:
      "pgvector cosine similarity for semantic matches, BM25 for exact identifiers, merged with " +
      "Reciprocal Rank Fusion. Embeddings blur names like getUserById; keyword search nails them. " +
      "Neither alone is enough on code.",
  },
  {
    title: "Agentic tool use",
    body:
      "A five-tool loop — search, read file, grep, run tests, git blame — where the model chooses " +
      "the next call and sees the result before deciding again. Capped at a step budget, with a " +
      "graceful \"here's what I tried\" fallback instead of an error.",
  },
  {
    title: "Evaluation & observability",
    body:
      "The part most projects skip. A golden Q&A set scores retrieval (precision@k, MRR) and answer " +
      "quality (LLM-as-judge), and every run logs its cost, latency, and tool-call trace. So " +
      "\"did retrieval regress?\" has a number, not a vibe.",
  },
];

const STACK = [
  "Python", "FastAPI", "PostgreSQL", "pgvector", "BM25",
  "Gemini API", "React", "Vite", "Tailwind", "Chart.js", "Docker",
];

const FLOW = [
  { label: "Repo", sub: "local or git URL" },
  { label: "AST chunker", sub: "function/class boundaries" },
  { label: "pgvector + BM25", sub: "hybrid index" },
  { label: "Agent loop", sub: "5 tools, streamed" },
  { label: "Answer", sub: "with cost + trace" },
];

function Metric({ label, value, loading }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-700 dark:bg-slate-900">
      <div className="text-xs text-slate-500 dark:text-slate-400">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900 [font-variant-numeric:tabular-nums] dark:text-slate-100">
        {loading ? <span className="text-slate-300 dark:text-slate-700">—</span> : value}
      </div>
    </div>
  );
}

export default function LandingPage() {
  const [run, setRun] = useState(null);
  const [state, setState] = useState("loading"); // loading | ready | unavailable

  useEffect(() => {
    let cancelled = false;

    // Loaded async and allowed to fail: on a free-tier host the backend may be cold, and
    // the page should render instantly either way rather than block on a wake-up.
    (async () => {
      try {
        const projects = await listProjects();
        for (const p of projects) {
          const runs = await listEvalRuns(p.id);
          if (runs.length > 0) {
            if (!cancelled) {
              setRun({ ...runs[0], projectName: p.name });
              setState("ready");
            }
            return;
          }
        }
        if (!cancelled) setState("unavailable");
      } catch {
        if (!cancelled) setState("unavailable");
      }
    })();

    return () => { cancelled = true; };
  }, []);

  const loading = state === "loading";

  return (
    <div className="space-y-16 pb-16">
      {/* Hero */}
      <section className="pt-8 text-center">
        <h1 className="text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl dark:text-slate-100">
          Ask questions about any codebase
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-slate-600 dark:text-slate-400">
          RepoPilot is an agentic RAG assistant that reads a repository, reasons across it with
          real tools, and — unlike most LLM demos — measures whether its own answers are any good.
        </p>
        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/chat"
            className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-medium text-white hover:bg-slate-700 dark:bg-slate-100 dark:text-slate-900 dark:hover:bg-white"
          >
            Try it →
          </Link>
          <Link
            to="/dashboard"
            className="rounded-lg border border-slate-300 px-5 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            See the eval dashboard
          </Link>
          <a
            href={GITHUB_URL}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg px-5 py-2.5 text-sm font-medium text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
          >
            Source on GitHub
          </a>
        </div>
      </section>

      {/* Live eval numbers */}
      <section>
        <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Measured, not claimed
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {state === "ready"
              ? `latest eval run · ${run.num_examples} golden questions · project "${run.projectName}"`
              : state === "unavailable"
              ? "backend asleep — open the dashboard to wake it"
              : "loading latest run…"}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          <Metric label="Precision@k" value={run && run.precision_at_k.toFixed(2)} loading={loading || !run} />
          <Metric label="MRR" value={run && run.mrr.toFixed(2)} loading={loading || !run} />
          <Metric label="Judge score" value={run && `${run.judge_score_avg.toFixed(1)} / 5`} loading={loading || !run} />
          <Metric label="Avg latency" value={run && `${(run.avg_latency_ms / 1000).toFixed(1)} s`} loading={loading || !run} />
          <Metric label="Cost / query" value={run && `$${run.avg_cost_usd.toFixed(4)}`} loading={loading || !run} />
        </div>
        <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
          These are read live from the eval harness, not hardcoded. Re-run it from the dashboard and
          they change.
        </p>
      </section>

      {/* Why */}
      <section className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-700 dark:bg-slate-900">
        <h2 className="text-lg font-medium text-slate-900 dark:text-slate-100">
          Why this exists
        </h2>
        <p className="mt-3 max-w-3xl text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          Most LLM side projects stop at “I called an API and it worked once.” That proves nothing
          about whether the system holds up when you change the chunking strategy, swap the model, or
          point it at a repo it hasn’t seen. RepoPilot is built around the parts that answer that
          question: a retrieval layer you can score, an agent loop you can trace step by step, and a
          cost and latency budget you can actually see.
        </p>
      </section>

      {/* Pillars */}
      <section className="grid gap-4 md:grid-cols-3">
        {PILLARS.map((p) => (
          <div
            key={p.title}
            className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-900"
          >
            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{p.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{p.body}</p>
          </div>
        ))}
      </section>

      {/* Flow */}
      <section>
        <h2 className="mb-4 text-sm font-medium text-slate-700 dark:text-slate-300">
          How a question gets answered
        </h2>
        <div className="flex flex-wrap items-stretch gap-2">
          {FLOW.map((step, i) => (
            <div key={step.label} className="flex items-stretch gap-2">
              <div className="min-w-[9rem] rounded-lg border border-slate-200 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900">
                <div className="text-sm font-medium text-slate-800 dark:text-slate-200">{step.label}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400">{step.sub}</div>
              </div>
              {i < FLOW.length - 1 && (
                <div className="flex items-center text-slate-300 dark:text-slate-600" aria-hidden="true">→</div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Stack */}
      <section>
        <h2 className="mb-3 text-sm font-medium text-slate-700 dark:text-slate-300">Built with</h2>
        <div className="flex flex-wrap gap-2">
          {STACK.map((tech) => (
            <span
              key={tech}
              className="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-400"
            >
              {tech}
            </span>
          ))}
        </div>
      </section>
    </div>
  );
}
