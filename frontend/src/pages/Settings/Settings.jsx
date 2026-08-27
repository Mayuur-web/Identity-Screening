import { useState } from 'react'
import PageLayout from '../../components/PageLayout'
import Toggle from '../../components/Toggle'
import { TuneIcon, FactCheckIcon } from '../../components/Icons'

const settingsTabs = [
  { label: 'Profile', active: false },
  { label: 'Security', active: false },
  { label: 'Verification Rules', active: false },
  { label: 'Risk Thresholds', active: true },
  { label: 'API Configuration', active: false },
  { label: 'Audit Logs', active: false },
]

const riskRanges = [
  { label: 'Low Risk Range', color: 'bg-green-500', range: '0 - 30', left: '0%', width: '30%' },
  { label: 'Medium Risk Range', color: 'bg-yellow-500', range: '31 - 60', left: '30%', width: '30%' },
  { label: 'High Risk Range', color: 'bg-red-500', range: '61 - 100', left: '60%', width: '40%' },
]

const features = [
  { label: 'Face Verification', description: 'Biometric facial match.', defaultOn: true },
  { label: 'OCR Validation', description: 'Text extraction analysis.', defaultOn: true },
  { label: 'Tamper Detection', description: 'Image manipulation check.', defaultOn: true },
  { label: 'Metadata Analysis', description: 'EXIF data scrutiny.', defaultOn: true },
  { label: 'Cross-field Consistency', description: 'Logical data matching.', defaultOn: true },
]

export default function Settings() {
  const [activeTab, setActiveTab] = useState('Risk Thresholds')

  return (
    <PageLayout>
      <div className="flex flex-col lg:flex-row gap-8">
        {/* Settings Sidebar Menu */}
        <aside className="w-full lg:w-56 shrink-0">
          <nav className="flex lg:flex-col gap-2 overflow-x-auto pb-4 lg:pb-0">
            {settingsTabs.map((tab) => (
              <button
                key={tab.label}
                onClick={() => setActiveTab(tab.label)}
                className={`whitespace-nowrap px-4 py-2 rounded-lg font-label-md text-label-md transition-colors ${
                  activeTab === tab.label
                    ? 'bg-surface-container-high text-primary font-bold border-l-4 border-secondary'
                    : 'text-on-surface-variant hover:bg-surface-container-high'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </aside>

        {/* Settings Detail Pane */}
        <section className="flex-1 flex flex-col gap-stack-gap-lg">
          <div className="flex justify-between items-end mb-2 border-b border-outline-variant pb-4">
            <div>
              <h3 className="font-headline-md text-headline-md text-primary">Risk Thresholds</h3>
              <p className="text-on-surface-variant mt-1 max-w-2xl">
                Configure the score ranges for risk categorization and toggle active verification features.
              </p>
            </div>
            <button className="bg-primary text-on-primary font-label-md text-label-md px-4 py-2 rounded-lg hover:bg-primary-container transition-colors shadow-sm whitespace-nowrap">
              Save Changes
            </button>
          </div>

          {/* Bento Grid Layout */}
          <div className="grid grid-cols-1 md:grid-cols-12 gap-stack-gap-md">
            {/* Score Ranges Card */}
            <div className="md:col-span-12 lg:col-span-7 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm">
              <div className="flex items-center gap-2 mb-6">
                <TuneIcon className="text-on-surface-variant" />
                <h4 className="font-headline-sm text-headline-sm text-primary">Score Calibration</h4>
              </div>
              <div className="space-y-8">
                {riskRanges.map((range, i) => (
                  <div key={i}>
                    <div className="flex justify-between items-center mb-2">
                      <label className="font-label-md text-label-md text-on-surface flex items-center gap-2">
                        <div className={`w-3 h-3 rounded-full ${range.color}`}></div>
                        {range.label}
                      </label>
                      <span className="font-data-mono text-data-mono bg-surface-container px-2 py-1 rounded text-primary">{range.range}</span>
                    </div>
                    <div className="relative w-full h-2 bg-surface-variant rounded-full mt-2">
                      <div className={`absolute top-0 h-full ${range.color} rounded-full`} style={{ left: range.left, width: range.width }}></div>
                    </div>
                    {i === 0 && (
                      <div className="flex justify-between text-[10px] text-outline mt-1">
                        <span>0</span>
                        <span>100</span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Feature Toggles Card */}
            <div className="md:col-span-12 lg:col-span-5 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm flex flex-col">
              <div className="flex items-center gap-2 mb-6">
                <FactCheckIcon className="text-on-surface-variant" />
                <h4 className="font-headline-sm text-headline-sm text-primary">Active Features</h4>
              </div>
              <div className="flex-1 space-y-4">
                {features.map((feature, i) => (
                  <Toggle
                    key={i}
                    label={feature.label}
                    description={feature.description}
                    defaultOn={feature.defaultOn}
                  />
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </PageLayout>
  )
}
