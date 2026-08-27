export default function ScoreCard({ label, value, unit, trend, borderColor }) {
  return (
    <div
      className={`bg-surface-container-lowest border border-outline-variant rounded-xl p-4 flex flex-col justify-between hover:shadow-[0_2px_4px_rgba(0,0,0,0.05)] transition-shadow ${borderColor || ''}`}
    >
      <div className="flex justify-between items-center">
        <span className="font-label-md text-label-md text-on-surface-variant uppercase">{label}</span>
        {trend === 'up' && <span className="material-symbols-outlined text-green-600 text-sm">arrow_upward</span>}
      </div>
      <div className="mt-2 flex items-baseline gap-1">
        <span className="font-display-lg text-display-lg text-primary">{value}</span>
        {unit && <span className="font-label-md text-label-md text-on-surface-variant">{unit}</span>}
      </div>
    </div>
  )
}
