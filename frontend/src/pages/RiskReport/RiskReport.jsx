import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import PageLayout from '../../components/PageLayout'
import RiskGauge from '../../components/RiskGauge'
import { WarningIcon, CheckCircleIcon, AnalyticsIcon, GavelIcon, DownloadIcon, VisibilityIcon } from '../../components/Icons'

const API_BASE = '/api'

const defaultThresholds = { lowMax: 30, mediumMax: 60, highMax: 100 }

function loadThresholds() {
  try {
    const stored = localStorage.getItem('parakhseva-risk-thresholds')
    if (stored) return JSON.parse(stored)
  } catch { /* ignore */ }
  return defaultThresholds
}

function getRiskLevel(score, thresholds) {
  if (score == null) return { level: 'UNKNOWN', color: 'text-on-surface-variant', bg: 'bg-surface-container-high', border: 'border-outline-variant' }
  if (score <= thresholds.lowMax) return { level: 'LOW', color: 'text-emerald-600', bg: 'bg-emerald-50', border: 'border-emerald-200' }
  if (score <= thresholds.mediumMax) return { level: 'MEDIUM', color: 'text-amber-600', bg: 'bg-amber-50', border: 'border-amber-200' }
  return { level: 'HIGH', color: 'text-red-600', bg: 'bg-red-50', border: 'border-red-200' }
}

function getStatusConfig(status) {
  const map = {
    VERIFIED: { label: 'VERIFIED', color: 'bg-emerald-50 text-emerald-800 border border-emerald-200', icon: 'check_circle', iconColor: 'text-emerald-500' },
    MANUAL_REVIEW: { label: 'REVIEW', color: 'bg-amber-50 text-amber-800 border border-amber-200', icon: 'warning', iconColor: 'text-amber-500' },
    REJECTED: { label: 'REJECTED', color: 'bg-red-50 text-red-800 border border-red-200', icon: 'cancel', iconColor: 'text-red-500' },
  }
  return map[status] || map.MANUAL_REVIEW
}

function formatDate(iso) {
  if (!iso) return '—'
  try { return new Date(iso).toLocaleString() } catch { return iso }
}

// ─── Empty State ──────────────────────────────────────────────────────────────
function EmptyState({ onNavigate }) {
  return (
    <PageLayout>
      <div className="mb-stack-gap-lg">
        <h1 className="font-display-lg text-display-lg text-on-surface">Risk Reports</h1>
        <p className="text-on-surface-variant mt-2">AI-powered risk analysis and verification intelligence.</p>
      </div>
      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-12 text-center">
        <div className="inline-flex flex-col items-center gap-4">
          <span className="material-symbols-outlined text-[64px] text-outline">assessment</span>
          <h3 className="font-headline-sm text-headline-sm text-on-surface">No Risk Reports Available</h3>
          <p className="font-body-md text-body-md text-on-surface-variant max-w-md">
            Complete a verification to generate a risk report.
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

// ─── Report Detail Modal ──────────────────────────────────────────────────────
function ReportDetail({ record, onClose, thresholds }) {
  if (!record) return null
  const risk = getRiskLevel(record.score, thresholds)
  const statusCfg = getStatusConfig(record.status)
  const checks = record.verification_checks || record.checks || []
  const faceV = record.face_verification || {}
  const fields = record.extracted_fields || record.fields || {}
  const reasons = record.reasons || []

  const identityFields = [
    { key: 'full_name', label: 'Full Name', icon: 'person' },
    { key: 'date_of_birth', label: 'Date of Birth', icon: 'cake' },
    { key: 'document_number', label: 'Document Number', icon: 'badge' },
    { key: 'gender', label: 'Gender', icon: 'wc' },
    { key: 'address', label: 'Address', icon: 'location_on' },
    { key: 'father_name', label: "Father's Name", icon: 'family_restroom' },
    { key: 'nationality', label: 'Nationality', icon: 'flag' },
  ].filter(({ key }) => fields[key] != null && fields[key] !== '')

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl max-w-3xl w-full max-h-[85vh] overflow-y-auto shadow-2xl" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="sticky top-0 bg-surface-container-lowest border-b border-outline-variant px-6 py-4 flex items-center justify-between z-10">
          <div>
            <h2 className="font-headline-sm text-headline-sm text-primary">Risk Report Detail</h2>
            <p className="font-data-mono text-data-mono text-on-surface-variant text-xs mt-1">{record.document_id || '—'}</p>
          </div>
          <button onClick={onClose} className="p-2 rounded-full hover:bg-surface-container-high transition-colors">
            <span className="material-symbols-outlined text-on-surface-variant">close</span>
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Overview */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="p-3 rounded-lg bg-surface border border-outline-variant/50">
              <span className="font-label-md text-[11px] text-on-surface-variant uppercase tracking-wider">Status</span>
              <div className={`mt-1 px-2 py-0.5 rounded inline-block font-label-md text-[11px] uppercase ${statusCfg.color}`}>{statusCfg.label}</div>
            </div>
            <div className="p-3 rounded-lg bg-surface border border-outline-variant/50">
              <span className="font-label-md text-[11px] text-on-surface-variant uppercase tracking-wider">Score</span>
              <p className={`font-data-mono text-data-mono text-xl font-bold mt-1 ${risk.color}`}>{record.score ?? '—'}</p>
            </div>
            <div className="p-3 rounded-lg bg-surface border border-outline-variant/50">
              <span className="font-label-md text-[11px] text-on-surface-variant uppercase tracking-wider">Risk Level</span>
              <p className={`font-label-md text-label-md font-bold mt-1 ${risk.color}`}>{risk.level}</p>
            </div>
            <div className="p-3 rounded-lg bg-surface border border-outline-variant/50">
              <span className="font-label-md text-[11px] text-on-surface-variant uppercase tracking-wider">Document Type</span>
              <p className="font-body-md text-body-md text-primary font-medium mt-1 uppercase">{record.document_type || '—'}</p>
            </div>
          </div>

          {/* Reasons */}
          {reasons.length > 0 && (
            <div className="p-4 rounded-lg bg-amber-50 border border-amber-200">
              <div className="flex items-center gap-2 mb-2">
                <WarningIcon className="text-amber-600" filled />
                <span className="font-label-md text-label-md text-amber-800 font-semibold">Reasons</span>
              </div>
              <ul className="list-disc list-inside text-sm text-amber-700 space-y-1">
                {reasons.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </div>
          )}

          {/* Verification Checks */}
          {checks.length > 0 && (
            <div>
              <h3 className="font-headline-sm text-headline-sm text-primary mb-3">Verification Checks</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {checks.map((check, i) => (
                  <div key={i} className="flex items-start gap-2 p-2 rounded-lg bg-surface border border-outline-variant/50">
                    <span className={`material-symbols-outlined text-[18px] mt-0.5 ${
                      check.status === 'passed' ? 'text-emerald-500' :
                      check.status === 'failed' ? 'text-red-500' : 'text-on-surface-variant'
                    }`}>
                      {check.status === 'passed' ? 'check_circle' : check.status === 'failed' ? 'cancel' : 'remove_circle'}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="font-label-md text-label-md text-on-surface font-medium">{check.name}</div>
                      <div className="text-on-surface-variant text-xs truncate">{check.message}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Face Verification */}
          {faceV.status && (
            <div>
              <h3 className="font-headline-sm text-headline-sm text-primary mb-3">Face Verification</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg bg-surface border border-outline-variant/50">
                  <span className="font-label-md text-[11px] text-on-surface-variant uppercase">Status</span>
                  <p className="font-body-md text-body-md text-primary font-medium mt-1">{faceV.status}</p>
                </div>
                {faceV.similarity_score != null && (
                  <div className="p-3 rounded-lg bg-surface border border-outline-variant/50">
                    <span className="font-label-md text-[11px] text-on-surface-variant uppercase">Similarity</span>
                    <p className="font-data-mono text-data-mono text-primary font-bold mt-1">{faceV.similarity_score}%</p>
                  </div>
                )}
                <div className="p-3 rounded-lg bg-surface border border-outline-variant/50">
                  <span className="font-label-md text-[11px] text-on-surface-variant uppercase">Doc Face</span>
                  <p className={`font-body-md text-body-md mt-1 ${faceV.face_detected_in_document ? 'text-emerald-600' : 'text-on-surface-variant'}`}>
                    {faceV.face_detected_in_document ? 'Detected' : 'Not Detected'}
                  </p>
                </div>
                <div className="p-3 rounded-lg bg-surface border border-outline-variant/50">
                  <span className="font-label-md text-[11px] text-on-surface-variant uppercase">Selfie Face</span>
                  <p className={`font-body-md text-body-md mt-1 ${faceV.face_detected_in_selfie ? 'text-emerald-600' : 'text-on-surface-variant'}`}>
                    {faceV.face_detected_in_selfie ? 'Detected' : 'Not Detected'}
                  </p>
                </div>
              </div>
              {faceV.message && (
                <p className="mt-2 text-on-surface-variant text-xs">{faceV.message}</p>
              )}
            </div>
          )}

          {/* Extracted Fields */}
          {identityFields.length > 0 && (
            <div>
              <h3 className="font-headline-sm text-headline-sm text-primary mb-3">Extracted Identity Fields</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {identityFields.map(({ key, label, icon }) => (
                  <div key={key} className="flex items-center gap-2 p-2 rounded-lg bg-surface border border-outline-variant/50">
                    <span className="material-symbols-outlined text-[18px] text-secondary">{icon}</span>
                    <div className="flex-1 min-w-0">
                      <span className="font-label-md text-[10px] text-on-surface-variant uppercase">{label}</span>
                      <p className="font-data-mono text-data-mono text-primary text-sm truncate">{fields[key]}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function RiskReport() {
  const navigate = useNavigate()
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedRecord, setSelectedRecord] = useState(null)
  const [thresholds, setThresholds] = useState(loadThresholds)

  // Filters
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState('all')
  const [filterRisk, setFilterRisk] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')

  const fetchHistory = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/history?limit=100`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const json = await res.json()
      setRecords(json.records || [])
    } catch (err) {
      setError(err.message || 'Failed to load risk reports')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchHistory() }, [fetchHistory])

  // Reload thresholds when component mounts (in case user changed them in Settings)
  useEffect(() => { setThresholds(loadThresholds()) }, [])

  // Filter records
  const filtered = records.filter((r) => {
    const q = searchQuery.toLowerCase()
    if (q && !(r.document_id || '').toLowerCase().includes(q) && !(r.filename || '').toLowerCase().includes(q)) return false
    if (filterType !== 'all' && (r.document_type || '').toLowerCase() !== filterType) return false
    if (filterStatus !== 'all' && r.status !== filterStatus) return false
    if (filterRisk !== 'all') {
      const level = getRiskLevel(r.score, thresholds).level
      if (level !== filterRisk) return false
    }
    return true
  })

  // Calculate overview stats
  const totalCount = records.length
  const verifiedCount = records.filter(r => r.status === 'VERIFIED').length
  const reviewCount = records.filter(r => r.status === 'MANUAL_REVIEW').length
  const rejectedCount = records.filter(r => r.status === 'REJECTED').length
  const scoresArr = records.filter(r => r.score != null).map(r => r.score)
  const avgScore = scoresArr.length > 0 ? Math.round(scoresArr.reduce((a, b) => a + b, 0) / scoresArr.length) : null
  const highRiskCount = records.filter(r => r.score != null && r.score > thresholds.mediumMax).length

  // Risk distribution
  const lowCount = records.filter(r => r.score != null && r.score <= thresholds.lowMax).length
  const medCount = records.filter(r => r.score != null && r.score > thresholds.lowMax && r.score <= thresholds.mediumMax).length
  const highCount = records.filter(r => r.score != null && r.score > thresholds.mediumMax).length
  const distTotal = lowCount + medCount + highCount || 1

  // Loading
  if (loading) {
    return (
      <PageLayout>
        <div className="mb-stack-gap-lg">
          <h1 className="font-display-lg text-display-lg text-on-surface">Risk Reports</h1>
          <p className="text-on-surface-variant mt-2">AI-powered risk analysis and verification intelligence.</p>
        </div>
        <div className="flex items-center justify-center py-12">
          <span className="material-symbols-outlined text-4xl text-secondary animate-spin mr-3">progress_activity</span>
          <span className="font-body-lg text-body-lg text-on-surface-variant">Loading risk reports...</span>
        </div>
      </PageLayout>
    )
  }

  // Error
  if (error && records.length === 0) {
    return (
      <PageLayout>
        <div className="mb-stack-gap-lg">
          <h1 className="font-display-lg text-display-lg text-on-surface">Risk Reports</h1>
          <p className="text-on-surface-variant mt-2">AI-powered risk analysis and verification intelligence.</p>
        </div>
        <div className="p-6 bg-error-container border border-error/30 rounded-xl">
          <div className="flex items-center gap-3">
            <span className="material-symbols-outlined text-error">error</span>
            <span className="font-body-md text-body-md text-on-surface">{error}</span>
          </div>
          <button onClick={fetchHistory} className="mt-4 px-4 py-2 bg-primary text-on-primary rounded-lg font-label-md text-label-md hover:bg-primary/90 transition-colors">
            Retry
          </button>
        </div>
      </PageLayout>
    )
  }

  // Empty
  if (records.length === 0) {
    return <EmptyState onNavigate={navigate} />
  }

  return (
    <PageLayout>
      {/* Header */}
      <div className="mb-stack-gap-lg flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
        <div>
          <h1 className="font-display-lg text-display-lg text-on-surface mb-2">Risk Reports</h1>
          <p className="text-on-surface-variant">AI-powered risk analysis and verification intelligence.</p>
        </div>
        <button
          onClick={() => navigate('/new-verification')}
          className="px-4 py-2 bg-primary text-on-primary rounded-lg font-label-md text-label-md hover:bg-primary-container transition-colors shadow-sm flex items-center gap-2"
        >
          <span className="material-symbols-outlined text-[16px]">add</span>
          New Verification
        </button>
      </div>

      {/* Risk Overview KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-stack-gap-lg">
        {[
          { label: 'Total Reports', value: totalCount, icon: 'assessment', color: 'text-primary' },
          { label: 'Verified', value: verifiedCount, icon: 'check_circle', color: 'text-emerald-600' },
          { label: 'Review', value: reviewCount, icon: 'warning', color: 'text-amber-600' },
          { label: 'Rejected', value: rejectedCount, icon: 'cancel', color: 'text-red-600' },
          { label: 'Avg Score', value: avgScore != null ? avgScore : '—', icon: 'speed', color: 'text-primary' },
          { label: 'High Risk', value: highRiskCount, icon: 'report', color: 'text-red-600' },
        ].map(({ label, value, icon, color }) => (
          <div key={label} className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 flex flex-col">
            <span className="font-label-md text-label-md text-on-surface-variant uppercase">{label}</span>
            <div className="flex items-center gap-2 mt-2">
              <span className={`material-symbols-outlined text-[20px] ${color}`}>{icon}</span>
              <span className={`font-display-lg text-display-lg ${color}`}>{value}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Risk Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-stack-gap-lg mb-stack-gap-lg">
        <div className="lg:col-span-5 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm">
          <h3 className="font-headline-sm text-headline-sm text-primary mb-4 flex items-center gap-2">
            <AnalyticsIcon />
            Risk Distribution
          </h3>
          <div className="space-y-4">
            {[
              { label: `Low Risk (0–${thresholds.lowMax})`, count: lowCount, color: 'bg-emerald-500', textColor: 'text-emerald-600' },
              { label: `Medium Risk (${thresholds.lowMax + 1}–${thresholds.mediumMax})`, count: medCount, color: 'bg-amber-500', textColor: 'text-amber-600' },
              { label: `High Risk (${thresholds.mediumMax + 1}–100)`, count: highCount, color: 'bg-red-500', textColor: 'text-red-600' },
            ].map(({ label, count, color, textColor }) => (
              <div key={label}>
                <div className="flex justify-between items-center mb-1">
                  <span className="font-label-md text-label-md text-on-surface">{label}</span>
                  <span className="font-data-mono text-data-mono text-on-surface-variant">{count}</span>
                </div>
                <div className="w-full bg-surface-variant rounded-full h-2.5">
                  <div className={`${color} h-2.5 rounded-full transition-all`} style={{ width: `${(count / distTotal) * 100}%` }}></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Risk Score Gauge Summary */}
        <div className="lg:col-span-3 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm flex flex-col items-center justify-center">
          <h3 className="font-headline-sm text-headline-sm text-primary mb-4">Average Score</h3>
          <RiskGauge score={avgScore || 0} size={140} />
          <p className="mt-3 text-on-surface-variant text-sm">
            {avgScore != null ? `Based on ${scoresArr.length} scored verifications` : 'No scored verifications'}
          </p>
        </div>

        {/* Status Breakdown */}
        <div className="lg:col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm">
          <h3 className="font-headline-sm text-headline-sm text-primary mb-4 flex items-center gap-2">
            <GavelIcon />
            Status Breakdown
          </h3>
          <div className="space-y-3">
            {[
              { label: 'Verified', count: verifiedCount, total: totalCount, color: 'bg-emerald-500', textColor: 'text-emerald-600' },
              { label: 'Manual Review', count: reviewCount, total: totalCount, color: 'bg-amber-500', textColor: 'text-amber-600' },
              { label: 'Rejected', count: rejectedCount, total: totalCount, color: 'bg-red-500', textColor: 'text-red-600' },
            ].map(({ label, count, total, color, textColor }) => (
              <div key={label} className="flex items-center gap-3">
                <span className={`w-3 h-3 rounded-full ${color}`}></span>
                <div className="flex-1">
                  <div className="flex justify-between items-center">
                    <span className="font-label-md text-label-md text-on-surface">{label}</span>
                    <span className="font-data-mono text-data-mono text-on-surface-variant">{count}</span>
                  </div>
                  <div className="w-full bg-surface-variant rounded-full h-1.5 mt-1">
                    <div className={`${color} h-1.5 rounded-full`} style={{ width: `${total > 0 ? (count / total) * 100 : 0}%` }}></div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-stack-gap-md mb-stack-gap-lg shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-stack-gap-md">
          <div className="relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-lg">search</span>
            <input
              className="w-full pl-10 pr-4 py-2 bg-background border border-outline-variant rounded-lg text-body-md text-on-surface placeholder-outline focus:outline-none focus:border-secondary focus:ring-1 focus:ring-secondary transition-shadow"
              placeholder="Search by ID or filename..."
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="w-full px-3 py-2 bg-background border border-outline-variant rounded-lg text-body-md text-on-surface appearance-none focus:outline-none focus:border-secondary cursor-pointer"
          >
            <option value="all">All Document Types</option>
            <option value="aadhaar">Aadhaar</option>
            <option value="passport">Passport</option>
            <option value="pan">PAN</option>
          </select>
          <select
            value={filterRisk}
            onChange={(e) => setFilterRisk(e.target.value)}
            className="w-full px-3 py-2 bg-background border border-outline-variant rounded-lg text-body-md text-on-surface appearance-none focus:outline-none focus:border-secondary cursor-pointer"
          >
            <option value="all">All Risk Levels</option>
            <option value="LOW">Low Risk</option>
            <option value="MEDIUM">Medium Risk</option>
            <option value="HIGH">High Risk</option>
          </select>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="w-full px-3 py-2 bg-background border border-outline-variant rounded-lg text-body-md text-on-surface appearance-none focus:outline-none focus:border-secondary cursor-pointer"
          >
            <option value="all">All Statuses</option>
            <option value="VERIFIED">Verified</option>
            <option value="MANUAL_REVIEW">Manual Review</option>
            <option value="REJECTED">Rejected</option>
          </select>
        </div>
      </div>

      {/* Recent Risk Reports Table */}
      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-outline-variant bg-surface-container-low">
          <h3 className="font-headline-sm text-headline-sm text-primary">Recent Risk Reports</h3>
        </div>
        {filtered.length === 0 ? (
          <div className="p-12 text-center">
            <span className="material-symbols-outlined text-[48px] text-outline">search_off</span>
            <p className="mt-2 font-body-md text-body-md text-on-surface-variant">No records match your filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[900px]">
              <thead>
                <tr className="bg-surface-container-low border-b border-outline-variant font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">
                  <th className="px-4 py-3">Date/Time</th>
                  <th className="px-4 py-3">Document ID</th>
                  <th className="px-4 py-3">Type</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3 text-center">Score</th>
                  <th className="px-4 py-3">Risk Level</th>
                  <th className="px-4 py-3">Face Match</th>
                  <th className="px-4 py-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="font-body-md text-body-md text-on-surface divide-y divide-outline-variant divide-opacity-40">
                {filtered.map((record, i) => {
                  const risk = getRiskLevel(record.score, thresholds)
                  const statusCfg = getStatusConfig(record.status)
                  const faceV = record.face_verification || {}
                  return (
                    <tr key={record.document_id || i} className="hover:bg-surface-container-low transition-colors group">
                      <td className="px-4 py-3 text-on-surface-variant text-sm">{formatDate(record.created_at)}</td>
                      <td className="px-4 py-3 font-data-mono text-data-mono text-primary text-sm">{record.document_id || '—'}</td>
                      <td className="px-4 py-3 text-on-surface-variant text-sm uppercase">{record.document_type || '—'}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded font-label-md text-[11px] uppercase tracking-wide ${statusCfg.color}`}>
                          {statusCfg.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`font-data-mono text-data-mono font-bold ${
                          record.score != null ? (record.score >= 80 ? 'text-emerald-600' : record.score >= 50 ? 'text-amber-600' : 'text-red-600') : 'text-on-surface-variant'
                        }`}>
                          {record.score ?? '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded font-label-md text-[11px] uppercase tracking-wide ${risk.bg} ${risk.color} ${risk.border} border`}>
                          {risk.level}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {faceV.status ? (
                          <span className={`font-label-md text-[11px] uppercase ${
                            faceV.status === 'MATCH' ? 'text-emerald-600' :
                            faceV.status === 'NO_MATCH' ? 'text-red-600' :
                            'text-on-surface-variant'
                          }`}>
                            {faceV.status === 'MATCH' ? `Match (${faceV.similarity_score}%)` :
                             faceV.status === 'NO_MATCH' ? 'Mismatch' :
                             faceV.status === 'NOT_PROVIDED' ? 'N/A' : faceV.status}
                          </span>
                        ) : '—'}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => setSelectedRecord(record)}
                          className="text-secondary hover:text-on-secondary-fixed-variant font-medium text-[13px] transition-opacity opacity-0 group-hover:opacity-100"
                        >
                          View Report
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {selectedRecord && (
        <ReportDetail record={selectedRecord} onClose={() => setSelectedRecord(null)} thresholds={thresholds} />
      )}
    </PageLayout>
  )
}
