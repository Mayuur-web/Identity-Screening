import { useState, useEffect, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import PageLayout from '../../components/PageLayout'
import ScoreCard from '../../components/ScoreCard'
import StatusBadge from '../../components/StatusBadge'
import { AddIcon } from '../../components/Icons'

const API_BASE = '/api'

const STATUS_MAP = {
  VERIFIED: 'verified',
  MANUAL_REVIEW: 'suspicious',
  REJECTED: 'highRisk',
}

function getRiskLevel(score) {
  if (score == null) return 'unknown'
  if (score <= 30) return 'low'
  if (score <= 60) return 'medium'
  return 'high'
}

function getRiskThresholds() {
  try {
    const raw = localStorage.getItem('parakhseva-risk-thresholds')
    if (raw) {
      const t = JSON.parse(raw)
      return {
        lowMax: t.low?.max ?? 30,
        mediumMax: t.medium?.max ?? 60,
      }
    }
  } catch {}
  return { lowMax: 30, mediumMax: 60 }
}

function getRiskLevelWithThresholds(score) {
  const { lowMax, mediumMax } = getRiskThresholds()
  if (score == null) return 'unknown'
  if (score <= lowMax) return 'low'
  if (score <= mediumMax) return 'medium'
  return 'high'
}

function getApplicantName(record) {
  const fields = record.extracted_fields || {}
  return fields.full_name || fields.given_names || fields.surname || 'Not detected'
}

function getFaceMatch(checks) {
  if (!checks || !Array.isArray(checks)) return null
  const faceCheck = checks.find(c => c.name === 'Face Match')
  return faceCheck || null
}

function getFaceMatchDisplay(checks) {
  const face = getFaceMatch(checks)
  if (!face) return 'N/A'
  if (face.status === 'passed') {
    const match = face.message.match(/\(?\d+\.?\d*%\)?/)
    return match ? match[0].replace(/[()]/g, '') : 'Match'
  }
  if (face.status === 'failed') return 'No Match'
  return 'N/A'
}

function formatDate(isoString) {
  if (!isoString) return '—'
  try {
    const d = new Date(isoString)
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch {
    return '—'
  }
}

function formatDateTime(isoString) {
  if (!isoString) return '—'
  try {
    const d = new Date(isoString)
    const date = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    const time = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true })
    return `${date}, ${time}`
  } catch {
    return '—'
  }
}

function getActivityByDay(records) {
  const now = new Date()
  const days = []
  for (let i = 6; i >= 0; i--) {
    const d = new Date(now)
    d.setDate(d.getDate() - i)
    d.setHours(0, 0, 0, 0)
    days.push(d)
  }

  const dayCounts = days.map(day => {
    const dayStr = day.toDateString()
    const count = records.filter(r => {
      if (!r.created_at) return false
      try {
        const rd = new Date(r.created_at)
        return rd.toDateString() === dayStr
      } catch {
        return false
      }
    }).length
    return {
      label: day.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }),
      shortLabel: day.toLocaleDateString('en-US', { weekday: 'short' }),
      count,
    }
  })

  return dayCounts
}

export default function Dashboard() {
  const navigate = useNavigate()
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchHistory = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API_BASE}/history?limit=100`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setRecords(data.records || [])
    } catch (err) {
      setError(err.message || 'Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

  // Compute KPIs
  const kpis = useMemo(() => {
    const total = records.length
    const verified = records.filter(r => r.status === 'VERIFIED').length
    const suspicious = records.filter(r => r.status === 'MANUAL_REVIEW').length
    const highRisk = records.filter(r => getRiskLevelWithThresholds(r.score) === 'high').length

    return [
      { label: 'Total Verifications', value: total.toLocaleString() },
      { label: 'Verified', value: verified.toLocaleString(), trend: verified > 0 ? 'up' : undefined },
      { label: 'Suspicious', value: suspicious.toLocaleString(), borderColor: suspicious > 0 ? 'border-l-4 border-l-amber-500' : undefined },
      { label: 'High Risk', value: highRisk.toLocaleString(), borderColor: highRisk > 0 ? 'border-l-4 border-l-red-600' : undefined },
      { label: 'Avg Time', value: '—', unit: '' },
    ]
  }, [records])

  // Risk distribution
  const riskDistribution = useMemo(() => {
    const total = records.length
    if (total === 0) return { low: { count: 0, pct: 0 }, medium: { count: 0, pct: 0 }, high: { count: 0, pct: 0 }, total: 0 }

    const low = records.filter(r => getRiskLevelWithThresholds(r.score) === 'low').length
    const medium = records.filter(r => getRiskLevelWithThresholds(r.score) === 'medium').length
    const high = records.filter(r => getRiskLevelWithThresholds(r.score) === 'high').length

    return {
      low: { count: low, pct: Math.round((low / total) * 100) },
      medium: { count: medium, pct: Math.round((medium / total) * 100) },
      high: { count: high, pct: Math.round((high / total) * 100) },
      total,
    }
  }, [records])

  // Activity by day
  const activityData = useMemo(() => getActivityByDay(records), [records])
  const maxActivityCount = useMemo(() => Math.max(...activityData.map(d => d.count), 1), [activityData])

  // Recent records (most recent 10)
  const recentRecords = useMemo(() => {
    return records
      .slice()
      .sort((a, b) => {
        try { return new Date(b.created_at) - new Date(a.created_at) } catch { return 0 }
      })
      .slice(0, 10)
  }, [records])

  // Loading state
  if (loading) {
    return (
      <PageLayout>
        <div className="flex justify-between items-end mb-8">
          <div>
            <h2 className="font-headline-md text-headline-md text-on-surface mb-1">Verification Dashboard</h2>
            <p className="font-body-md text-body-md text-on-surface-variant">Monitor identity and document verification activity.</p>
          </div>
          <button
            onClick={() => navigate('/new-verification')}
            className="bg-primary text-white font-label-md text-label-md px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-primary-container transition-colors shadow-sm"
          >
            <AddIcon />
            New Verification
          </button>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="bg-surface-container-lowest border border-outline-variant rounded-xl p-4 animate-pulse">
              <div className="h-3 bg-surface-container-high rounded w-20 mb-3" />
              <div className="h-8 bg-surface-container-high rounded w-16" />
            </div>
          ))}
        </div>
        <div className="grid grid-cols-12 gap-6 mb-8">
          <div className="col-span-12 lg:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 animate-pulse">
            <div className="h-5 bg-surface-container-high rounded w-40 mb-4" />
            <div className="h-64 bg-surface-container-high rounded" />
          </div>
          <div className="col-span-12 lg:col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 animate-pulse">
            <div className="h-5 bg-surface-container-high rounded w-32 mb-4" />
            <div className="h-64 bg-surface-container-high rounded" />
          </div>
        </div>
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 animate-pulse">
          <div className="h-5 bg-surface-container-high rounded w-48 mb-4" />
          <div className="h-48 bg-surface-container-high rounded" />
        </div>
      </PageLayout>
    )
  }

  // Error state
  if (error) {
    return (
      <PageLayout>
        <div className="flex justify-between items-end mb-8">
          <div>
            <h2 className="font-headline-md text-headline-md text-on-surface mb-1">Verification Dashboard</h2>
            <p className="font-body-md text-body-md text-on-surface-variant">Monitor identity and document verification activity.</p>
          </div>
          <button
            onClick={() => navigate('/new-verification')}
            className="bg-primary text-white font-label-md text-label-md px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-primary-container transition-colors shadow-sm"
          >
            <AddIcon />
            New Verification
          </button>
        </div>
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-12 text-center">
          <div className="inline-flex flex-col items-center gap-3">
            <span className="material-symbols-outlined text-[40px] text-error">cloud_off</span>
            <span className="font-headline-sm text-headline-sm text-on-surface">Failed to load dashboard</span>
            <span className="font-body-md text-body-md text-on-surface-variant">{error}</span>
            <button
              onClick={fetchHistory}
              className="mt-2 px-4 py-2 bg-secondary text-on-secondary rounded-lg font-label-md text-label-md hover:bg-secondary/90 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      </PageLayout>
    )
  }

  return (
    <PageLayout>
      {/* Header Section */}
      <div className="flex justify-between items-end mb-8">
        <div>
          <h2 className="font-headline-md text-headline-md text-on-surface mb-1">Verification Dashboard</h2>
          <p className="font-body-md text-body-md text-on-surface-variant">Monitor identity and document verification activity.</p>
        </div>
        <button
          onClick={() => navigate('/new-verification')}
          className="bg-primary text-white font-label-md text-label-md px-4 py-2 rounded-lg flex items-center gap-2 hover:bg-primary-container transition-colors shadow-sm"
        >
          <AddIcon />
          New Verification
        </button>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
        {kpis.map((kpi, i) => (
          <ScoreCard key={i} {...kpi} />
        ))}
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-12 gap-6 mb-8">
        {/* Left Chart: Verification Activity */}
        <div className="col-span-12 lg:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex flex-col">
          <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Verification Activity</h3>
          <div className="flex-1 w-full min-h-[250px] flex flex-col">
            {records.length === 0 ? (
              <div className="flex-1 flex items-center justify-center text-on-surface-variant font-body-md text-body-md">
                No activity data
              </div>
            ) : (
              <>
                {/* Bar chart */}
                <div className="flex-1 flex items-end gap-2 px-2 pb-2 relative" style={{ minHeight: 200 }}>
                  {activityData.map((day, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center gap-1">
                      <span className="font-data-mono text-data-mono text-on-surface-variant text-xs">
                        {day.count > 0 ? day.count : ''}
                      </span>
                      <div
                        className="w-full bg-primary rounded-t transition-all duration-300 min-h-[2px]"
                        style={{
                          height: `${day.count > 0 ? Math.max((day.count / maxActivityCount) * 100, 8) : 2}%`,
                          opacity: day.count > 0 ? 1 : 0.15,
                        }}
                      />
                    </div>
                  ))}
                </div>
                {/* X-axis labels */}
                <div className="flex gap-2 px-2 border-t border-outline-variant pt-2">
                  {activityData.map((day, i) => (
                    <div key={i} className="flex-1 text-center font-label-sm text-label-sm text-on-surface-variant">
                      <span className="hidden sm:inline">{day.shortLabel}</span>
                      <span className="sm:hidden">{day.shortLabel.charAt(0)}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Right Chart: Risk Distribution */}
        <div className="col-span-12 lg:col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex flex-col">
          <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Risk Distribution</h3>
          <div className="flex-1 flex flex-col items-center justify-center min-h-[250px]">
            {riskDistribution.total === 0 ? (
              <div className="text-on-surface-variant font-body-md text-body-md">No data</div>
            ) : (
              <>
                {/* Donut chart via SVG */}
                <div className="relative w-40 h-40 mb-4">
                  <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                    {/* Low risk arc */}
                    {riskDistribution.low.pct > 0 && (
                      <circle
                        cx="18" cy="18" r="15.91549"
                        fill="none"
                        stroke="rgb(34,197,94)"
                        strokeWidth="4"
                        strokeDasharray={`${riskDistribution.low.pct} ${100 - riskDistribution.low.pct}`}
                        strokeDashoffset="0"
                      />
                    )}
                    {/* Medium risk arc */}
                    {riskDistribution.medium.pct > 0 && (
                      <circle
                        cx="18" cy="18" r="15.91549"
                        fill="none"
                        stroke="rgb(251,191,36)"
                        strokeWidth="4"
                        strokeDasharray={`${riskDistribution.medium.pct} ${100 - riskDistribution.medium.pct}`}
                        strokeDashoffset={-riskDistribution.low.pct}
                      />
                    )}
                    {/* High risk arc */}
                    {riskDistribution.high.pct > 0 && (
                      <circle
                        cx="18" cy="18" r="15.91549"
                        fill="none"
                        stroke="rgb(220,38,38)"
                        strokeWidth="4"
                        strokeDasharray={`${riskDistribution.high.pct} ${100 - riskDistribution.high.pct}`}
                        strokeDashoffset={-(riskDistribution.low.pct + riskDistribution.medium.pct)}
                      />
                    )}
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center">
                      <div className="font-display-lg text-display-lg text-primary">{riskDistribution.total}</div>
                      <div className="font-label-sm text-label-sm text-on-surface-variant">total</div>
                    </div>
                  </div>
                </div>
                {/* Legend */}
                <div className="flex flex-col gap-2 w-full">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 font-label-md text-label-md text-on-surface-variant">
                      <span className="w-3 h-3 rounded-full bg-green-500"></span> Low Risk
                    </div>
                    <span className="font-data-mono text-data-mono text-on-surface">{riskDistribution.low.count} ({riskDistribution.low.pct}%)</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 font-label-md text-label-md text-on-surface-variant">
                      <span className="w-3 h-3 rounded-full bg-amber-400"></span> Medium Risk
                    </div>
                    <span className="font-data-mono text-data-mono text-on-surface">{riskDistribution.medium.count} ({riskDistribution.medium.pct}%)</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 font-label-md text-label-md text-on-surface-variant">
                      <span className="w-3 h-3 rounded-full bg-red-600"></span> High Risk
                    </div>
                    <span className="font-data-mono text-data-mono text-on-surface">{riskDistribution.high.count} ({riskDistribution.high.pct}%)</span>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Recent Verification Activity Table */}
      <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden flex flex-col mb-8">
        <div className="px-6 py-4 border-b border-outline-variant flex justify-between items-center bg-surface-container-low">
          <h3 className="font-headline-sm text-headline-sm text-on-surface">Recent Verification Activity</h3>
          <button onClick={() => navigate('/verification-history')} className="text-secondary font-label-md text-label-md hover:underline">
            View All
          </button>
        </div>
        <div className="overflow-x-auto">
          {recentRecords.length === 0 ? (
            <div className="p-12 text-center">
              <div className="inline-flex flex-col items-center gap-3">
                <span className="material-symbols-outlined text-[48px] text-outline">folder_off</span>
                <span className="font-body-md text-body-md text-on-surface-variant">No verification records available</span>
                <button
                  onClick={() => navigate('/new-verification')}
                  className="mt-2 px-4 py-2 bg-primary text-white rounded-lg font-label-md text-label-md hover:bg-primary-container transition-colors"
                >
                  Start New Verification
                </button>
              </div>
            </div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-container-lowest border-b border-outline-variant">
                  {['ID', 'Type', 'Applicant', 'Status', 'Risk Score', 'Face Match', 'Date', 'Action'].map((h) => (
                    <th key={h} className={`px-6 py-3 font-label-md text-label-md text-on-surface-variant uppercase ${h === 'Action' ? 'text-right' : ''}`}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="font-body-md text-body-md">
                {recentRecords.map((record, i) => {
                  const statusKey = STATUS_MAP[record.status] || 'review'
                  const riskLevel = getRiskLevelWithThresholds(record.score)
                  const applicant = getApplicantName(record)
                  const faceMatch = getFaceMatchDisplay(record.checks)

                  const riskColor =
                    riskLevel === 'high' ? 'score-red' :
                    riskLevel === 'medium' ? 'score-amber' :
                    'score-green'

                  return (
                    <tr key={record.document_id || i} className={`border-b border-outline-variant hover:bg-surface-container-low transition-colors group ${i === recentRecords.length - 1 ? 'border-b-0' : ''}`}>
                      <td className="px-6 py-3 font-data-mono text-data-mono text-on-surface">{record.document_id || '—'}</td>
                      <td className="px-6 py-3 text-on-surface-variant capitalize">{record.document_type || '—'}</td>
                      <td className="px-6 py-3 text-on-surface font-medium">{applicant}</td>
                      <td className="px-6 py-3"><StatusBadge status={statusKey} /></td>
                      <td className={`px-6 py-3 font-data-mono text-data-mono ${riskColor}`}>{record.score != null ? `${record.score} / 100` : '—'}</td>
                      <td className="px-6 py-3 font-data-mono text-data-mono text-on-surface-variant">{faceMatch}</td>
                      <td className="px-6 py-3 text-on-surface-variant text-sm">{formatDateTime(record.created_at)}</td>
                      <td className="px-6 py-3 text-right">
                        <button
                          onClick={() => navigate('/risk-report')}
                          className="text-secondary font-label-md text-label-md hover:underline opacity-0 group-hover:opacity-100 transition-opacity"
                        >
                          View Report
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </PageLayout>
  )
}
