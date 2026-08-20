// The Vite dev proxy doesn't reliably forward long-lived SSE streams (observed hangs on
// the query/stream endpoint), so talk to the backend directly instead of going through /api.
const BASE = "http://localhost:8000/api";

export async function listProjects() {
  const res = await fetch(`${BASE}/projects`);
  return res.json();
}

export async function listEvalRuns(projectId) {
  const res = await fetch(`${BASE}/eval/runs?project_id=${projectId}`);
  return res.json();
}

/**
 * Streams an agent run over SSE using the native EventSource API. Calls onStep(stepObj)
 * for each step and onDone(doneObj) when the final answer arrives.
 */
export function streamQuery(projectId, question, { onStep, onDone, onError }) {
  const url = `${BASE}/query/stream?${new URLSearchParams({ project_id: projectId, question })}`;
  const source = new EventSource(url);

  source.addEventListener("step", (e) => onStep?.(JSON.parse(e.data)));
  source.addEventListener("done", (e) => {
    onDone?.(JSON.parse(e.data));
    source.close();
  });
  source.onerror = (err) => {
    source.close();
    console.error("streamQuery failed:", err);
    onError?.(err);
  };

  return () => source.close();
}
