import { useEffect, useState } from "react";
import { browseDir } from "../api";

export default function FolderBrowser({ startPath, onSelect, onClose }) {
  const [current, setCurrent] = useState(null); // {path, parent, entries}
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  function go(path) {
    setLoading(true);
    setError("");
    browseDir(path)
      .then(setCurrent)
      .catch((err) => setError(err.message || "Failed to browse"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    go(startPath || "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl w-full max-w-lg max-h-[80vh] flex flex-col">
        <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 dark:border-slate-700">
          <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300">Choose a folder</h3>
          <button onClick={onClose} className="text-xs text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300">
            Close
          </button>
        </div>

        <div className="px-4 py-2 text-xs text-slate-500 dark:text-slate-400 border-b border-slate-100 dark:border-slate-800 truncate">
          {current?.path || "Drives"}
        </div>

        <div className="flex-1 overflow-y-auto px-2 py-2">
          {loading && <p className="text-sm text-slate-400 px-2 py-4">Loading…</p>}
          {error && <p className="text-sm text-red-600 dark:text-red-400 px-2 py-4">{error}</p>}
          {!loading && !error && (
            <>
              {current?.parent !== null && current?.parent !== undefined && (
                <button
                  onClick={() => go(current.parent)}
                  className="w-full text-left px-3 py-1.5 rounded-md text-sm text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  .. (up)
                </button>
              )}
              {current?.entries.map((entry) => (
                <button
                  key={entry.path}
                  onClick={() => go(entry.path)}
                  className="w-full text-left px-3 py-1.5 rounded-md text-sm text-slate-800 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  📁 {entry.name}
                </button>
              ))}
              {current?.entries.length === 0 && (
                <p className="text-sm text-slate-400 px-3 py-2">No subfolders here.</p>
              )}
            </>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 px-4 py-3 border-t border-slate-200 dark:border-slate-700">
          <button
            onClick={onClose}
            className="text-sm px-3 py-1.5 rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            Cancel
          </button>
          <button
            onClick={() => current?.path && onSelect(current.path)}
            disabled={!current?.path}
            className="bg-slate-900 text-white dark:bg-slate-100 dark:text-slate-900 px-3 py-1.5 rounded-lg text-sm disabled:opacity-40"
          >
            Select this folder
          </button>
        </div>
      </div>
    </div>
  );
}
