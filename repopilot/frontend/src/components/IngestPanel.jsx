import { useState } from "react";
import { ingestProject } from "../api";

export default function IngestPanel({ onIngested }) {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [repoPath, setRepoPath] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function submit(e) {
    e.preventDefault();
    if (!name.trim() || !repoPath.trim() || loading) return;
    setLoading(true);
    setError("");
    try {
      const project = await ingestProject(name.trim(), repoPath.trim());
      setName("");
      setRepoPath("");
      setOpen(false);
      onIngested?.(project);
    } catch (err) {
      setError(err.message || "Ingest failed");
    } finally {
      setLoading(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="self-start text-left text-xs text-slate-500 hover:text-slate-800 underline underline-offset-2 mb-3"
      >
        + Ingest a repo
      </button>
    );
  }

  return (
    <form onSubmit={submit} className="bg-white border border-slate-200 rounded-xl p-4 mb-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-700">Ingest a codebase</h3>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="text-xs text-slate-400 hover:text-slate-600"
          disabled={loading}
        >
          Cancel
        </button>
      </div>

      <div className="grid sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs text-slate-500 mb-1">Project name</label>
          <input
            className="w-full border border-slate-300 rounded-md px-2 py-1.5 text-sm"
            placeholder="e.g. my-api"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={loading}
          />
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">Local repo path</label>
          <input
            className="w-full border border-slate-300 rounded-md px-2 py-1.5 text-sm"
            placeholder="C:\path\to\repo"
            value={repoPath}
            onChange={(e) => setRepoPath(e.target.value)}
            disabled={loading}
          />
        </div>
      </div>

      {error && <p className="text-xs text-red-600">{error}</p>}

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={loading || !name.trim() || !repoPath.trim()}
          className="bg-slate-900 text-white px-4 py-1.5 rounded-lg text-sm disabled:opacity-40"
        >
          {loading ? "Ingesting…" : "Ingest"}
        </button>
        {loading && (
          <span className="text-xs text-slate-500">
            Chunking, embedding, and indexing — this can take a minute or more for larger repos.
          </span>
        )}
      </div>
    </form>
  );
}
