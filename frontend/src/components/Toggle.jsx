import { useState } from 'react'

export default function Toggle({ defaultOn = true, label, description, onChange }) {
  const [on, setOn] = useState(defaultOn)

  const handleToggle = () => {
    const newState = !on
    setOn(newState)
    if (onChange) onChange(newState)
  }

  return (
    <div className="flex items-center justify-between p-3 border border-outline-variant rounded-lg bg-surface-container-low">
      <div>
        <p className="font-label-md text-label-md text-primary">{label}</p>
        <p className="text-[11px] text-on-surface-variant mt-0.5">{description}</p>
      </div>
      <button
        onClick={handleToggle}
        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-secondary focus:ring-offset-2 ${
          on ? 'bg-secondary-container' : 'bg-outline-variant'
        }`}
      >
        <span
          className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
            on ? 'translate-x-4' : 'translate-x-1'
          }`}
        />
      </button>
    </div>
  )
}
