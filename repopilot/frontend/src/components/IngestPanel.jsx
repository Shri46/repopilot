import { useEffect, useState } from "react";
import { cloneProject, fsBrowserEnabled, ingestProject } from "../api";
import FolderBrowser from "./FolderBrowser";

const tabClass = (active) =>
  `px-3 py-1 rounded-md text-xs font-medium ${
    active
      ? "bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900"
      : "text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
  }`;

export default function IngestPanel({ onIngested }) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState("local"); // "local" | "clone"
  const [name, setName] = useState("");
  const [repoPath, setRepoPath] = useState("");
  const [gitUrl, setGitUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [browsing, setBrowsing] = useState(false);
  const [canBrowse, setCanBrowse] = useState(false);

  useEffect(() => {
    fsBrowserEnabled().then(setCanBrowse);
  }, []);

  function reset() {
    setName("");
    setRepoPath("");
    setGitUrl("");
    setOpen(false);
  }

  async function submit(e) {
    e.preventDefault();
    if (loading) return;
    if (mode === "local" && (!name.trim() || !repoPath.trim())) return;
    if (mode === "clone" && (!name.trim() || !gitUrl.trim())) return;

    setLoading(true);
    setError("");
    try {
      const project =
        mode === "local"
          ? await ingestProject(name.trim(), repoPath.trim())
          : await cloneProject(name.trim(), gitUrl.trim());
      reset();
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
        className="self-start text-left text-xs text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 underline underline-offset-2 mb-3"
      >
        + Ingest a repo
      </button>
    );
  }

  return (
    <>
      <form onSubmit={submit} className="bg-white border border-slate-200 dark:bg-slate-900 dark:border-slate-700 rounded-xl p-4 mb-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300 mr-1">Ingest a codebase</h3>
            <button type="button" onClick={() => setMode("local")} className={tabClass(mode === "local")}>
              Local folder
            </button>
            <button type="button" onClick={() => setMode("clone")} className={tabClass(mode === "clone")}>
              Clone from URL
            </button>
          </div>
          <button
            type="button"
            onClick={reset}
            className="text-xs text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300"
            disabled={loading}
          >
            Cancel
          </button>
        </div>

        <div className="grid sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Project name</label>
            <input
              className="w-full border border-slate-300 rounded-md px-2 py-1.5 text-sm bg-white text-slate-900 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-100"
              placeholder="e.g. my-api"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={loading}
            />
          </div>

          {mode === "local" ? (
            <div>
              <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Local repo path</label>
              <div className="flex gap-1">
                <input
                  className="w-full border border-slate-300 rounded-md px-2 py-1.5 text-sm bg-white text-slate-900 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-100"
                  placeholder="C:\path\to\repo"
                  value={repoPath}
                  onChange={(e) => setRepoPath(e.target.value)}
                  disabled={loading}
                />
                {canBrowse && (
                  <button
                    type="button"
                    onClick={() => setBrowsing(true)}
                    disabled={loading}
                    className="shrink-0 border border-slate-300 dark:border-slate-700 rounded-md px-2 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
                  >
                    Browse…
                  </button>
                )}
              </div>
            </div>
          ) : (
            <div>
              <label className="block text-xs text-slate-500 dark:text-slate-400 mb-1">Git URL</label>
              <input
                className="w-full border border-slate-300 rounded-md px-2 py-1.5 text-sm bg-white text-slate-900 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-100"
                placeholder="https://github.com/owner/repo.git"
                value={gitUrl}
                onChange={(e) => setGitUrl(e.target.value)}
                disabled={loading}
              />
            </div>
          )}
        </div>

        {error && <p className="text-xs text-red-600 dark:text-red-400">{error}</p>}

        <div className="flex items-center gap-3">
          <button
            type="submit"
            disabled={
              loading ||
              !name.trim() ||
              (mode === "local" ? !repoPath.trim() : !gitUrl.trim())
            }
            className="bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 px-4 py-1.5 rounded-lg text-sm disabled:opacity-40"
          >
            {loading ? (mode === "clone" ? "Cloning & ingesting…" : "Ingesting…") : mode === "clone" ? "Clone & ingest" : "Ingest"}
          </button>
          {loading && (
            <span className="text-xs text-slate-500 dark:text-slate-400">
              {mode === "clone"
                ? "Cloning, then chunking, embedding, and indexing — this can take a while for larger repos."
                : "Chunking, embedding, and indexing — this can take a minute or more for larger repos."}
            </span>
          )}
        </div>
      </form>

      {browsing && (
        <FolderBrowser
          startPath={repoPath}
          onClose={() => setBrowsing(false)}
          onSelect={(path) => {
            setRepoPath(path);
            setBrowsing(false);
          }}
        />
      )}
    </>
  );
}
