import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageLayout from '../../components/PageLayout'
import RiskGauge from '../../components/RiskGauge'
import ProgressBar from '../../components/ProgressBar'
import { WarningIcon, ErrorIcon, CheckCircleIcon, AnalyticsIcon, GavelIcon, DownloadIcon, VisibilityIcon, VerifiedIcon } from '../../components/Icons'

const signals = [
  { label: 'Document Authenticity', value: '68/100', width: '68%', color: 'bg-secondary', textColor: 'text-primary' },
  { label: 'OCR Confidence', value: '96.8%', width: '96.8%', color: 'bg-primary', textColor: 'text-primary' },
  { label: 'Face Match', value: '92.6%', width: '92.6%', color: 'bg-primary', textColor: 'text-primary' },
  { label: 'Data Consistency', value: '100%', width: '100%', color: 'bg-primary', textColor: 'text-primary' },
  { label: 'Tampering Risk', value: '74/100', width: '74%', color: 'bg-error', textColor: 'text-error', containerColor: 'bg-error-container', isWarning: true },
  { label: 'Liveness Detection', value: 'Passed', width: '100%', color: 'bg-primary', textColor: 'text-primary' },
]

const warningFindings = [
  { text: 'Possible document image manipulation detected', detail: 'Pixel variance anomaly in sector 4B (Portrait border).' },
  { text: 'Unusual visual structure detected', detail: 'Hologram reflection pattern deviates from known template signatures.' },
]

const positiveFindings = [
  'OCR extraction highly confident (Avg 96.8%)',
  'Face match successful against supplied selfie (92.6% similarity)',
  'Identity fields consistent across cross-referenced databases',
]

export default function RiskReport() {
  const navigate = useNavigate()
  const [isReviewed, setIsReviewed] = useState(false)

  const handleMarkReviewed = () => {
    setIsReviewed(true)
  }

  return (
    <PageLayout>
      <div className="flex flex-col gap-stack-gap-lg">
        {/* Header Section */}
        <div className="flex justify-between items-end border-b border-outline-variant pb-4">
          <div>
            <p className="font-data-mono text-data-mono text-on-surface-variant mb-1">VERIFICATION ID: #VS-8924-X</p>
            <h1 className="font-display-lg text-display-lg text-primary">AI Verification Report</h1>
          </div>
          <div className="font-label-md text-label-md bg-surface-container text-on-surface px-3 py-1 rounded-full border border-outline-variant">
            Generated: Just now
          </div>
        </div>

        {/* Bento Grid Layout */}
        <div className="grid grid-cols-12 gap-stack-gap-lg">
          {/* Overall Result Card */}
          <div className="col-span-12 lg:col-span-4 bg-surface-container-lowest border border-error rounded-xl p-stack-gap-lg shadow-sm flex flex-col relative overflow-hidden">
            <div className="absolute inset-0 bg-error opacity-[0.03] pointer-events-none" />
            <div className="flex justify-between items-center mb-6 relative z-10">
              <h2 className="font-headline-sm text-headline-sm text-primary">Overall Assessment</h2>
              <span className="font-label-md text-label-md bg-error-container text-on-error-container px-3 py-1 rounded uppercase tracking-wider font-bold">High Risk</span>
            </div>
            <div className="flex-grow flex flex-col items-center justify-center relative z-10">
              <RiskGauge score={78} size={192} />
            </div>
            <div className="mt-6 space-y-3 relative z-10 border-t border-error-container pt-4">
              <div className="flex justify-between items-center">
                <span className="font-body-md text-body-md text-on-surface-variant">AI Confidence:</span>
                <span className="font-data-mono text-data-mono text-primary font-bold">94.2%</span>
              </div>
              <div className="bg-error-container text-on-error-container font-label-md text-label-md p-3 rounded-lg flex items-center gap-2 font-bold uppercase">
                <WarningIcon className="text-lg" filled />
                Manual Review Recommended
              </div>
            </div>
          </div>

          {/* AI Signal Breakdown */}
          <div className="col-span-12 lg:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-gap-lg shadow-sm flex flex-col">
            <h2 className="font-headline-sm text-headline-sm text-primary mb-6">AI Signal Breakdown</h2>
            <div className="space-y-5 flex-grow">
              {signals.map((signal, i) => (
                <ProgressBar
                  key={i}
                  label={signal.label}
                  value={signal.value}
                  color={signal.color}
                  textColor={signal.textColor}
                />
              ))}
            </div>
          </div>

          {/* Explainable Findings */}
          <div className="col-span-12 lg:col-span-6 bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-gap-lg shadow-sm">
            <h2 className="font-headline-sm text-headline-sm text-primary mb-4 flex items-center gap-2">
              <AnalyticsIcon />
              Why was this flagged?
            </h2>
            <div className="space-y-4">
              {warningFindings.map((finding, i) => (
                <div key={i} className="flex gap-3 items-start bg-error-container/30 p-3 rounded-lg border border-error-container">
                  <WarningIcon className="text-error mt-0.5" filled />
                  <div>
                    <p className="font-body-md text-body-md text-error font-semibold">{finding.text}</p>
                    <p className="font-data-mono text-data-mono text-on-surface-variant mt-1">{finding.detail}</p>
                  </div>
                </div>
              ))}
              <hr className="border-outline-variant my-4" />
              {positiveFindings.map((finding, i) => (
                <div key={i} className="flex gap-3 items-start">
                  <CheckCircleIcon className="text-primary mt-0.5" filled />
                  <p className="font-data-mono text-data-mono text-on-surface">{finding}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Decision Summary */}
          <div className="col-span-12 lg:col-span-6 bg-surface-container-lowest border border-outline-variant rounded-xl p-stack-gap-lg shadow-sm flex flex-col">
            <h2 className="font-headline-sm text-headline-sm text-primary mb-4 flex items-center gap-2">
              <GavelIcon />
              Decision Summary
            </h2>
            <div className="bg-surface p-4 rounded-lg border border-outline-variant flex-grow">
              <p className="font-body-lg text-body-lg text-on-surface leading-relaxed">
                The verification attempt is classified as <strong className="text-error font-semibold">HIGH RISK</strong>. While the identity data (OCR extraction) is consistent and the facial biometric match is highly successful, our computer vision models have detected significant anomalies in the physical document's imagery.
                <br /><br />
                Specifically, there are indications of digital tampering around the portrait border and irregular holographic reflections that do not align with standard issuer parameters. Due to these structural inconsistencies, automated approval is blocked. <strong className="text-primary font-semibold">Manual review by a Tier 2 analyst is strongly recommended</strong> before proceeding.
              </p>
            </div>
          </div>
        </div>

        {/* Action Buttons Footer */}
        <div className="flex justify-end items-center gap-4 border-t border-outline-variant pt-6 mt-4 pb-12">
          <button
            onClick={() => navigate('/new-verification')}
            className="font-label-md text-label-md text-secondary hover:bg-surface-variant px-4 py-2 rounded-lg transition-colors bg-transparent"
          >
            Start New Verification
          </button>
          <button className="font-label-md text-label-md text-primary bg-surface-container-lowest border border-outline-variant hover:bg-surface-container-high px-4 py-2 rounded-lg transition-colors flex items-center gap-2">
            <DownloadIcon className="text-sm" />
            Download Report
          </button>
          <button
            onClick={() => navigate('/document-analysis')}
            className="font-label-md text-label-md text-primary bg-surface-container-lowest border border-outline-variant hover:bg-surface-container-high px-4 py-2 rounded-lg transition-colors flex items-center gap-2"
          >
            <VisibilityIcon className="text-sm" />
            View Document
          </button>
          <button
            onClick={handleMarkReviewed}
            className={`font-label-md text-label-md px-6 py-2 rounded-lg transition-colors shadow-sm font-bold flex items-center gap-2 ${
              isReviewed
                ? 'bg-surface-container-high text-on-surface-variant'
                : 'bg-primary text-on-primary hover:bg-primary-container'
            }`}
          >
            <span className="material-symbols-outlined text-sm">{isReviewed ? 'check_circle' : 'verified'}</span>
            {isReviewed ? 'Reviewed' : 'Mark as Reviewed'}
          </button>
        </div>
      </div>
    </PageLayout>
  )
}
