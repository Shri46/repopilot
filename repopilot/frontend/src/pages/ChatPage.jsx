import { useEffect, useRef, useState } from "react";
import { deleteProject, listProjects, streamQuery } from "../api";
import IngestPanel from "../components/IngestPanel";
import StepTrace from "../components/StepTrace";

export default function ChatPage() {
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState("");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]); // {role, text, steps, meta}
  const [loading, setLoading] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const cancelRef = useRef(null);

  function refreshProjects(selectId) {
    return listProjects().then((data) => {
      setProjects(data);
      if (selectId) setProjectId(selectId);
      else if (data.length > 0 && !projectId) setProjectId(data[0].id);
      return data;
    });
  }

  useEffect(() => {
    refreshProjects();
  }, []);

  async function handleDelete() {
    const project = projects.find((p) => p.id === projectId);
    if (!project || deleting) return;
    if (!window.confirm(`Delete "${project.name}" and all its ingested data? This can't be undone.`)) return;

    setDeleting(true);
    try {
      await deleteProject(projectId);
      setMessages([]);
      const remaining = await listProjects();
      setProjects(remaining);
      setProjectId(remaining[0]?.id || "");
    } catch (err) {
      alert(err.message || "Delete failed");
    } finally {
      setDeleting(false);
    }
  }

  function ask() {
    if (!question.trim() || !projectId || loading) return;

    const userMsg = { role: "user", text: question };
    const assistantMsg = { role: "assistant", text: "", steps: [], meta: null };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setQuestion("");
    setLoading(true);

    cancelRef.current = streamQuery(projectId, userMsg.text, {
      onStep: (step) => {
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          if (step.step_type === "tool_call") {
            last.steps = [...last.steps, step];
          }
          return next;
        });
      },
      onDone: (done) => {
        setMessages((prev) => {
          const next = [...prev];
          const last = next[next.length - 1];
          last.text = done.final_answer;
          last.meta = { latency_ms: done.total_latency_ms, cost_usd: done.total_cost_usd };
          return next;
        });
        setLoading(false);
      },
      onError: () => setLoading(false),
    });
  }

  return (
    <div className="flex flex-col h-[calc(100vh-140px)]">
      <div className="mb-3 flex items-center gap-2 flex-wrap">
        <label className="text-sm text-slate-600">Project:</label>
        <select
          className="border border-slate-300 rounded-md px-2 py-1 text-sm"
          value={projectId}
          onChange={(e) => setProjectId(e.target.value)}
        >
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              {p.name} ({p.chunk_count} chunks)
            </option>
          ))}
        </select>
        {projectId && (
          <button
            onClick={handleDelete}
            disabled={deleting}
            title="Delete this project"
            className="text-xs text-red-500 hover:text-red-700 disabled:opacity-40"
          >
            {deleting ? "Deleting…" : "Delete"}
          </button>
        )}
        {projects.length === 0 && (
          <span className="text-xs text-slate-400">No projects yet — ingest one below</span>
        )}
      </div>

      <IngestPanel onIngested={(p) => refreshProjects(p.id)} />

      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="flex justify-end">
              <div className="bg-slate-900 text-white rounded-2xl rounded-br-sm px-4 py-2 max-w-lg">
                {m.text}
              </div>
            </div>
          ) : (
            <div key={i} className="flex justify-start">
              <div className="max-w-2xl">
                <StepTrace steps={m.steps} />
                {m.text ? (
                  <div className="bg-white border border-slate-200 rounded-2xl rounded-bl-sm px-4 py-3 whitespace-pre-wrap text-slate-800">
                    {m.text}
                    {m.meta && (
                      <div className="mt-2 text-xs text-slate-400">
                        {m.meta.latency_ms.toFixed(0)} ms · ${m.meta.cost_usd.toFixed(5)}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-sm text-slate-400 px-1">thinking…</div>
                )}
              </div>
            </div>
          )
        )}
      </div>

      <div className="flex gap-2 pt-3 border-t border-slate-200">
        <input
          className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm"
          placeholder="Ask something about the codebase…"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          disabled={loading}
        />
        <button
          onClick={ask}
          disabled={loading || !projectId}
          className="bg-slate-900 text-white px-4 py-2 rounded-lg text-sm disabled:opacity-40"
        >
          Ask
        </button>
      </div>
    </div>
  );
}
