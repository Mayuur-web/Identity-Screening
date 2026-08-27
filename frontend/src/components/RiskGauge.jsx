export default function RiskGauge({ score, size = 128, label = 'Risk Score', color }) {
  const getColor = (s) => {
    if (color) return color
    if (s >= 60) return 'stroke-error'
    if (s >= 31) return 'stroke-amber-500'
    return 'stroke-emerald-500'
  }

  const getTextColor = (s) => {
    if (s >= 60) return 'text-error'
    if (s >= 31) return 'text-amber-600'
    return 'text-emerald-600'
  }

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
        <path
          className="text-surface-container-high"
          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
        />
        <path
          className={getColor(score)}
          d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          fill="none"
          stroke="currentColor"
          strokeDasharray={`${score}, 100`}
          strokeWidth="3"
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className={`text-3xl font-bold ${getTextColor(score)}`}>{score}</span>
        <span className="text-xs text-on-surface-variant font-label-md">/100</span>
      </div>
    </div>
  )
}
