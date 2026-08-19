const TOOL_LABELS = {
  search_code: "🔍 Searching code",
  read_file: "📄 Reading file",
  grep: "🔎 Grepping",
  run_tests: "🧪 Running tests",
  git_blame: "🕵️ Checking git blame",
};

export default function StepTrace({ steps }) {
  if (steps.length === 0) return null;
  return (
    <div className="space-y-2 mb-3">
      {steps.map((s, i) => (
        <div key={i} className="text-xs bg-slate-100 rounded-lg px-3 py-2 text-slate-600">
          {s.step_type === "tool_call" ? (
            <>
              <span className="font-medium text-slate-800">
                {TOOL_LABELS[s.tool_name] || s.tool_name}
              </span>
              {s.tool_input && (
                <span className="ml-1 text-slate-500">
                  {JSON.stringify(s.tool_input)}
                </span>
              )}
            </>
          ) : (
            <span className="italic">Composing final answer…</span>
          )}
        </div>
      ))}
    </div>
  );
}
