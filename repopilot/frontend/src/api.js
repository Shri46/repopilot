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

export async function listDatasets() {
  const res = await fetch(`${BASE}/eval/datasets`);
  return res.json();
}

export async function runEval(projectId, datasetName) {
  const res = await fetch(`${BASE}/eval/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: projectId, dataset_name: datasetName }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Eval run failed (${res.status})`);
  }
  return res.json();
}

export async function ingestProject(name, repoPath) {
  const res = await fetch(`${BASE}/projects/ingest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, repo_path: repoPath }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Ingest failed (${res.status})`);
  }
  return res.json();
}

export async function browseDir(path) {
  const res = await fetch(`${BASE}/fs/browse?${new URLSearchParams({ path: path || "" })}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Browse failed (${res.status})`);
  }
  return res.json();
}

export async function cloneProject(name, gitUrl) {
  const res = await fetch(`${BASE}/projects/clone`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, git_url: gitUrl }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Clone failed (${res.status})`);
  }
  return res.json();
}

export async function deleteProject(projectId) {
  const res = await fetch(`${BASE}/projects/${projectId}`, { method: "DELETE" });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Delete failed (${res.status})`);
  }
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
