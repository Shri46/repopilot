export default function StatTile({ label, value, sub }) {
  return (
    <div className="bg-white border border-slate-200 dark:bg-slate-900 dark:border-slate-700 rounded-xl px-4 py-3">
      <div className="text-xs text-[#898781] dark:text-slate-500 mb-1">{label}</div>
      <div className="text-2xl font-semibold text-[#0b0b0b] dark:text-slate-100 [font-variant-numeric:tabular-nums]">
        {value}
      </div>
      {sub && <div className="text-xs text-[#52514e] dark:text-slate-400 mt-1">{sub}</div>}
    </div>
  );
}
