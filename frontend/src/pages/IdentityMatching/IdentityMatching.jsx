import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import PageLayout from '../../components/PageLayout'
import RiskGauge from '../../components/RiskGauge'

const API_BASE = '/api'

// Field display configuration — maps backend field keys to human-readable labels
const FIELD_CONFIG = [
  { key: 'full_name', label: 'Full Name', icon: 'person' },
  { key: 'date_of_birth', label: 'Date of Birth', icon: 'cake' },
  { key: 'document_number', label: 'Document Number', icon: 'badge' },
  { key: 'gender', label: 'Gender', icon: 'wc' },
  { key: 'address', label: 'Address', icon: 'location_on' },
  { key: 'father_name', label: "Father's Name", icon: 'family_restroom' },
  { key: 'nationality', label: 'Nationality', icon: 'flag' },
  { key: 'place_of_birth', label: 'Place of Birth', icon: 'location_on' },
  { key: 'date_of_issue', label: 'Date of Issue', icon: 'event' },
  { key: 'date_of_expiry', label: 'Date of Expiry', icon: 'event_busy' },
]

// Status display helpers
const statusConfig = {
  VERIFIED: { label: 'VERIFIED', color: 'bg-emerald-50 text-emerald-800 border border-emerald-200', icon: 'check_circle', iconColor: 'text-emerald-500' },
  MANUAL_REVIEW: { label: 'REVIEW', color: 'bg-amber-50 text-amber-800 border border-amber-200', icon: 'warning', iconColor: 'text-amber-500' },
  REJECTED: { label: 'REJECTED', color: 'bg-red-50 text-red-800 border border-red-200', icon: 'cancel', iconColor: 'text-red-500' },
}

const faceStatusConfig = {
  MATCH: { label: 'Face Match', color: 'bg-emerald-50 text-emerald-800 border border-emerald-200', icon: 'check_circle', iconColor: 'text-emerald-500' },
  NO_MATCH: { label: 'Face Mismatch', color: 'bg-red-50 text-red-800 border border-red-200', icon: 'cancel', iconColor: 'text-red-500' },
  NO_FACE: { label: 'No Face Detected', color: 'bg-amber-50 text-amber-800 border border-amber-200', icon: 'face', iconColor: 'text-amber-500' },
  NOT_PROVIDED: { label: 'Not Checked', color: 'bg-surface-container-high text-on-surface-variant border border-outline-variant', icon: 'info', iconColor: 'text-on-surface-variant' },
  ERROR: { label: 'Error', color: 'bg-red-50 text-red-800 border border-red-200', icon: 'error', iconColor: 'text-red-500' },
}

function checkStatusIcon(status) {
  if (status === 'passed') return { icon: 'check_circle', color: 'text-emerald-500' }
  if (status === 'failed') return { icon: 'cancel', color: 'text-red-500' }
  return { icon: 'remove_circle', color: 'text-on-surface-variant' }
}

// ─── Empty State ──────────────────────────────────────────────────────────────
function EmptyState({ onNavigate }) {
  return (
    <PageLayout>
      <div className="mb-stack-gap-lg">
        <h1 className="font-display-lg text-display-lg text-on-surface">Identity Matching</h1>
        <p className="text-on-surface-variant mt-2">Biometric cross-reference and identity consistency analysis.</p>
      </div>
      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-12 text-center">
        <div className="inline-flex flex-col items-center gap-4">
          <span className="material-symbols-outlined text-[64px] text-outline">how_to_reg</span>
          <h3 className="font-headline-sm text-headline-sm text-on-surface">No verification data available</h3>
          <p className="font-body-md text-body-md text-on-surface-variant max-w-md">
            Run a document verification first to see identity matching analysis here.
          </p>
          <button
            onClick={() => onNavigate('/new-verification')}
            className="mt-2 px-6 py-2.5 bg-primary text-on-primary rounded-lg font-label-md text-label-md hover:bg-primary-container transition-colors shadow-sm flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-[18px]">add</span>
            Start New Verification
          </button>
        </div>
      </div>
    </PageLayout>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function IdentityMatching() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [dataSource, setDataSource] = useState('')

  useEffect(() => {
    let cancelled = false

    async function loadData() {
      setLoading(true)
      setError(null)

      // 1. Try sessionStorage first (from NewVerification → DocumentAnalysis flow)
      const stored = sessionStorage.getItem('ocrResults')
      if (stored) {
        try {
          const parsed = JSON.parse(stored)
          if (!cancelled) {
            setData(parsed)
            setDataSource('session')
            setLoading(false)
          }
          return
        } catch { /* fall through to history API */ }
      }

      // 2. Fallback: fetch most recent record from history API
      try {
        const res = await fetch(`${API_BASE}/history?limit=1`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json = await res.json()
        if (!cancelled) {
          if (json.records && json.records.length > 0) {
            // History records have a slightly different shape — normalize
            const record = json.records[0]
            const normalized = {
              success: true,
              document_id: record.document_id,
              document_type: record.document_type,
              status: record.status,
              score: record.score,
              checks: record.verification_checks || record.checks || [],
              reasons: record.reasons || [],
              fields: record.extracted_fields || record.fields || {},
              mrz: record.mrz || null,
              face_verification: record.face_verification || { status: 'NOT_PROVIDED', similarity_score: null, face_detected_in_document: false, face_detected_in_selfie: false, message: 'Not available from history' },
              ocr: record.ocr || null,
            }
            setData(normalized)
            setDataSource('history')
          }
          setLoading(false)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Failed to load verification data')
          setLoading(false)
        }
      }
    }

    loadData()
    return () => { cancelled = true }
  }, [])

  // Loading
  if (loading) {
    return (
      <PageLayout>
        <div className="mb-stack-gap-lg">
          <h1 className="font-display-lg text-display-lg text-on-surface">Identity Matching</h1>
          <p className="text-on-surface-variant mt-2">Biometric cross-reference and identity consistency analysis.</p>
        </div>
        <div className="flex items-center justify-center py-12">
          <span className="material-symbols-outlined text-4xl text-secondary animate-spin mr-3">progress_activity</span>
          <span className="font-body-lg text-body-lg text-on-surface-variant">Loading verification data...</span>
        </div>
      </PageLayout>
    )
  }

  // Error
  if (error) {
    return (
      <PageLayout>
        <div className="mb-stack-gap-lg">
          <h1 className="font-display-lg text-display-lg text-on-surface">Identity Matching</h1>
          <p className="text-on-surface-variant mt-2">Biometric cross-reference and identity consistency analysis.</p>
        </div>
        <div className="p-6 bg-error-container border border-error/30 rounded-xl mb-6">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-error">error</span>
            <span className="font-body-md text-body-md text-on-surface">{error}</span>
          </div>
          <button onClick={() => navigate('/new-verification')} className="mt-4 px-4 py-2 bg-primary text-on-primary rounded-lg font-label-md text-label-md hover:bg-primary/90 transition-colors">
            Start New Verification
          </button>
        </div>
      </PageLayout>
    )
  }

  // Empty state
  if (!data) {
    return <EmptyState onNavigate={navigate} />
  }

  // ── Extract real data from response ──
  const fields = data.fields || {}
  const checks = data.checks || []
  const faceVerification = data.face_verification || { status: 'NOT_PROVIDED' }
  const reasons = data.reasons || []
  const score = data.score
  const status = data.status
  const docId = data.document_id
  const docType = data.document_type

  const statusInfo = statusConfig[status] || statusConfig.MANUAL_REVIEW
  const faceInfo = faceStatusConfig[faceVerification.status] || faceStatusConfig.NOT_PROVIDED

  // Build field consistency rows from extracted fields
  const fieldRows = FIELD_CONFIG
    .filter(({ key }) => fields[key] != null && fields[key] !== '')
    .map(({ key, label, icon }) => {
      const value = fields[key]
      const confidence = fields.field_confidence?.[key]
      const fieldStatus = fields.field_status?.[key]
      const confPct = confidence != null ? Math.round(confidence * 100) : null

      // Determine status display
      let statusLabel = 'Extracted'
      let statusClass = 'text-emerald-600'
      let statusIcon = 'check_circle'

      if (fieldStatus === 'conflict') {
        statusLabel = 'Conflict'
        statusClass = 'text-red-600'
        statusIcon = 'warning'
      } else if (fieldStatus === 'consistent') {
        statusLabel = 'Consistent (OCR + MRZ)'
        statusClass = 'text-emerald-600'
        statusIcon = 'check_circle'
      } else if (fieldStatus === 'not_detected') {
        statusLabel = 'Not Detected'
        statusClass = 'text-on-surface-variant'
        statusIcon = 'remove_circle'
      }

      return { key, label, icon, value, confPct, statusLabel, statusClass, statusIcon }
    })

  // Build matching breakdown signals
  const signals = []
  if (fields && Object.keys(fields).some(k => !k.startsWith('field_') && fields[k])) {
    signals.push({ label: 'OCR / Field Extraction', status: 'active', detail: `${fieldRows.length} fields extracted` })
  }
  if (docType) {
    signals.push({ label: 'Document Validation', status: 'active', detail: `${docType.toUpperCase()} verification` })
  }
  if (faceVerification.status !== 'NOT_PROVIDED') {
    signals.push({ label: 'Face Verification', status: faceVerification.status === 'MATCH' ? 'passed' : 'failed', detail: faceVerification.message })
  } else {
    signals.push({ label: 'Face Verification', status: 'not_checked', detail: 'Selfie not provided' })
  }
  if (checks.length > 0) {
    const passed = checks.filter(c => c.status === 'passed').length
    signals.push({ label: 'Cross-field Consistency', status: passed > 0 ? 'passed' : 'active', detail: `${passed}/${checks.length} checks passed` })
  }
  if (data.mrz?.detected) {
    signals.push({ label: 'MRZ Validation', status: 'passed', detail: 'Machine-readable zone detected' })
  }

  return (
    <PageLayout>
      {/* Header */}
      <div className="mb-stack-gap-lg flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="font-display-lg text-display-lg text-on-surface mb-2">Identity Matching</h1>
          <p className="text-on-surface-variant">Biometric cross-reference and identity consistency analysis.</p>
        </div>
        <div className="flex items-center gap-3">
          {dataSource === 'history' && (
            <span className="text-xs text-on-surface-variant bg-surface-container-high px-2 py-1 rounded border border-outline-variant">
              Loaded from history
            </span>
          )}
          <button
            onClick={() => navigate('/new-verification')}
            className="px-4 py-2 bg-primary text-on-primary rounded-lg font-label-md text-label-md hover:bg-primary-container transition-colors shadow-sm flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-[16px]">add</span>
            New Verification
          </button>
        </div>
      </div>

      {/* Overall Result Banner */}
      <section className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 mb-stack-gap-lg">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-surface-container-high flex items-center justify-center">
              <span className={`material-symbols-outlined text-[32px] ${statusInfo.iconColor}`}>{statusInfo.icon}</span>
            </div>
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h2 className="font-headline-md text-headline-md text-primary">Overall Result</h2>
                <span className={`px-3 py-1 rounded-lg font-label-md text-label-md font-semibold ${statusInfo.color}`}>
                  {statusInfo.label}
                </span>
              </div>
              <p className="text-on-surface-variant text-sm">
                {docId && <span className="font-data-mono text-data-mono">ID: {docId}</span>}
                {docId && docType && <span className="mx-2">·</span>}
                {docType && <span className="uppercase">{docType}</span>}
              </p>
            </div>
          </div>
          {score != null && (
            <div className="flex items-center gap-4">
              <RiskGauge score={score} size={100} />
              <div className="text-right">
                <div className="font-data-mono text-data-mono text-3xl font-bold text-primary">{score}</div>
                <div className="text-on-surface-variant text-[10px] uppercase tracking-wider">Verification Score</div>
              </div>
            </div>
          )}
        </div>

        {/* Reasons */}
        {reasons.length > 0 && (
          <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <div className="flex items-center gap-2 mb-1">
              <span className="material-symbols-outlined text-[16px] text-amber-600">info</span>
              <span className="font-label-md text-label-md text-amber-800 font-semibold">Reasons</span>
            </div>
            <ul className="list-disc list-inside text-sm text-amber-700">
              {reasons.map((r, i) => <li key={i}>{r}</li>)}
            </ul>
          </div>
        )}
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-stack-gap-lg mb-stack-gap-lg">
        {/* Left Column: Document Identity + Field Consistency */}
        <div className="lg:col-span-7 flex flex-col gap-stack-gap-lg">
          {/* Document Identity */}
          <section className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
            <h3 className="font-headline-sm text-headline-sm text-primary mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-secondary">badge</span>
              Document Identity
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {fieldRows.map(({ key, label, icon, value, confPct }) => (
                <div key={key} className="flex items-start gap-3 p-3 rounded-lg border border-outline-variant/50 bg-surface">
                  <span className="material-symbols-outlined text-[20px] text-secondary mt-0.5">{icon}</span>
                  <div className="flex-1 min-w-0">
                    <span className="font-label-md text-[11px] text-on-surface-variant uppercase tracking-wider">{label}</span>
                    <p className="font-data-mono text-data-mono text-primary font-bold mt-0.5 truncate">{value}</p>
                    {confPct != null && (
                      <span className={`text-[11px] font-data-mono ${confPct >= 90 ? 'text-emerald-600' : confPct >= 70 ? 'text-amber-600' : 'text-red-600'}`}>
                        {confPct}% confidence
                      </span>
                    )}
                  </div>
                </div>
              ))}
              {fieldRows.length === 0 && (
                <div className="col-span-2 text-center py-6 text-on-surface-variant">
                  <span className="material-symbols-outlined text-[32px] text-outline">search_off</span>
                  <p className="mt-2 text-sm">No identity fields were extracted from this document.</p>
                </div>
              )}
            </div>
          </section>

          {/* Field Consistency Table */}
          {fieldRows.length > 0 && (
            <section className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden">
              <div className="px-6 py-4 border-b border-outline-variant bg-surface-container-low">
                <h3 className="font-headline-sm text-headline-sm text-primary">Field Consistency</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead className="bg-surface-container-low text-on-surface-variant font-label-md text-label-md">
                    <tr>
                      <th className="px-6 py-3 font-semibold border-b border-outline-variant">Field</th>
                      <th className="px-6 py-3 font-semibold border-b border-outline-variant">Document Value</th>
                      <th className="px-6 py-3 font-semibold border-b border-outline-variant text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="font-body-md text-body-md text-on-surface divide-y divide-outline-variant">
                    {fieldRows.map(({ key, label, value, confPct, statusLabel, statusClass, statusIcon }) => (
                      <tr key={key} className="hover:bg-surface-bright transition-colors">
                        <td className="px-6 py-3 font-medium">{label}</td>
                        <td className="px-6 py-3 font-data-mono text-data-mono text-on-surface-variant text-sm max-w-[250px] truncate">{value}</td>
                        <td className="px-6 py-3 text-right">
                          <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border border-outline-variant/50 ${statusClass === 'text-emerald-600' ? 'bg-emerald-50' : statusClass === 'text-red-600' ? 'bg-red-50' : 'bg-surface-container-high'}`}>
                            <span className={`material-symbols-outlined text-[14px] ${statusClass}`}>{statusIcon}</span>
                            <span className={`font-label-md text-[11px] ${statusClass}`}>{statusLabel}</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>

        {/* Right Column: Face Match + Checks + Breakdown */}
        <div className="lg:col-span-5 flex flex-col gap-stack-gap-lg">
          {/* Face Match */}
          <section className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
            <h3 className="font-headline-sm text-headline-sm text-primary mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-secondary">face</span>
              Face Match
            </h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-surface border border-outline-variant/50">
                <span className="font-label-md text-label-md text-on-surface-variant">Status</span>
                <span className={`px-2 py-0.5 rounded font-label-md text-[11px] uppercase tracking-wide ${faceInfo.color}`}>
                  {faceInfo.label}
                </span>
              </div>
              {faceVerification.similarity_score != null && (
                <div className="flex items-center justify-between p-3 rounded-lg bg-surface border border-outline-variant/50">
                  <span className="font-label-md text-label-md text-on-surface-variant">Similarity</span>
                  <span className="font-data-mono text-data-mono text-primary font-bold">{faceVerification.similarity_score}%</span>
                </div>
              )}
              <div className="flex items-center justify-between p-3 rounded-lg bg-surface border border-outline-variant/50">
                <span className="font-label-md text-label-md text-on-surface-variant">Face in Document</span>
                <span className={`font-label-md text-label-md ${faceVerification.face_detected_in_document ? 'text-emerald-600' : 'text-on-surface-variant'}`}>
                  {faceVerification.face_detected_in_document ? 'Detected' : 'Not Detected'}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-surface border border-outline-variant/50">
                <span className="font-label-md text-label-md text-on-surface-variant">Face in Selfie</span>
                <span className={`font-label-md text-label-md ${faceVerification.face_detected_in_selfie ? 'text-emerald-600' : 'text-on-surface-variant'}`}>
                  {faceVerification.face_detected_in_selfie ? 'Detected' : 'Not Detected'}
                </span>
              </div>
              {faceVerification.message && (
                <div className="p-3 rounded-lg bg-surface-container-low border border-outline-variant/30">
                  <p className="text-on-surface-variant text-xs">{faceVerification.message}</p>
                </div>
              )}
            </div>
          </section>

          {/* Verification Checks */}
          {checks.length > 0 && (
            <section className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
              <h3 className="font-headline-sm text-headline-sm text-primary mb-4 flex items-center gap-2">
                <span className="material-symbols-outlined text-secondary">fact_check</span>
                Verification Checks
              </h3>
              <div className="space-y-2">
                {checks.map((check, i) => {
                  const { icon, color } = checkStatusIcon(check.status)
                  return (
                    <div key={i} className="flex items-start gap-2 p-2 rounded-lg bg-surface">
                      <span className={`material-symbols-outlined text-[18px] mt-0.5 ${color}`}>{icon}</span>
                      <div className="flex-1 min-w-0">
                        <div className="font-label-md text-label-md text-on-surface font-medium">{check.name}</div>
                        <div className="text-on-surface-variant text-xs truncate">{check.message}</div>
                      </div>
                      <span className={`font-label-md text-[10px] uppercase tracking-wide shrink-0 ${
                        check.status === 'passed' ? 'text-emerald-600' :
                        check.status === 'failed' ? 'text-red-600' : 'text-on-surface-variant'
                      }`}>
                        {check.status}
                      </span>
                    </div>
                  )
                })}
              </div>
            </section>
          )}

          {/* Matching Breakdown */}
          {signals.length > 0 && (
            <section className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6">
              <h3 className="font-headline-sm text-headline-sm text-primary mb-4 flex items-center gap-2">
                <span className="material-symbols-outlined text-secondary">analytics</span>
                Matching Breakdown
              </h3>
              <div className="space-y-3">
                {signals.map((signal, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 rounded-lg bg-surface border border-outline-variant/50">
                    <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${
                      signal.status === 'passed' ? 'bg-emerald-500' :
                      signal.status === 'failed' ? 'bg-red-500' :
                      signal.status === 'not_checked' ? 'bg-on-surface-variant/30' :
                      'bg-secondary'
                    }`}></span>
                    <div className="flex-1 min-w-0">
                      <span className="font-label-md text-label-md text-on-surface">{signal.label}</span>
                      <p className="text-on-surface-variant text-[11px] truncate">{signal.detail}</p>
                    </div>
                    <span className={`font-label-md text-[10px] uppercase tracking-wide shrink-0 ${
                      signal.status === 'passed' ? 'text-emerald-600' :
                      signal.status === 'failed' ? 'text-red-600' :
                      'text-on-surface-variant'
                    }`}>
                      {signal.status === 'passed' ? 'PASS' :
                       signal.status === 'failed' ? 'FAIL' :
                       signal.status === 'not_checked' ? 'N/A' : 'ACTIVE'}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </PageLayout>
  )
}
