const BASE = "/api";

export async function listProjects() {
  const res = await fetch(`${BASE}/projects`);
  return res.json();
}

export async function listEvalRuns(projectId) {
  const res = await fetch(`${BASE}/eval/runs?project_id=${projectId}`);
  return res.json();
}

/**
 * Streams an agent run over SSE. Calls onStep(stepObj) for each step and
 * onDone(doneObj) when the final answer arrives.
 */
export function streamQuery(projectId, question, { onStep, onDone, onError }) {
  const controller = new AbortController();

  fetch(`${BASE}/query/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: projectId, question }),
    signal: controller.signal,
  })
    .then(async (res) => {
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split("\n\n");
        buffer = events.pop() ?? "";

        for (const raw of events) {
          const lines = raw.split("\n");
          let event = "message";
          let data = "";
          for (const line of lines) {
            if (line.startsWith("event:")) event = line.slice(6).trim();
            if (line.startsWith("data:")) data += line.slice(5).trim();
          }
          if (!data) continue;
          const parsed = JSON.parse(data);
          if (event === "step") onStep?.(parsed);
          if (event === "done") onDone?.(parsed);
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") onError?.(err);
    });

  return () => controller.abort();
}
