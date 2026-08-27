export default function ProgressBar({ label, value, color = 'bg-secondary', textColor = 'text-primary' }) {
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className={`font-body-md text-body-md ${textColor} font-medium`}>{label}</span>
        <span className="font-data-mono text-data-mono text-on-surface-variant">{value}</span>
      </div>
      <div className="w-full bg-surface-variant rounded-full h-2">
        <div className={`${color} h-2 rounded-full`} style={{ width: `${parseFloat(value)}%` }}></div>
      </div>
    </div>
  )
}
