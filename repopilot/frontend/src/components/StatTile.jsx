export default function StatTile({ label, value, sub }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl px-4 py-3">
      <div className="text-xs text-[#898781] mb-1">{label}</div>
      <div className="text-2xl font-semibold text-[#0b0b0b] [font-variant-numeric:tabular-nums]">
        {value}
      </div>
      {sub && <div className="text-xs text-[#52514e] mt-1">{sub}</div>}
    </div>
  );
}
