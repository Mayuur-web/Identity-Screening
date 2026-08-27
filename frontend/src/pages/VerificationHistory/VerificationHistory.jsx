import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import PageLayout from '../../components/PageLayout'
import StatusBadge from '../../components/StatusBadge'
import DataTable from '../../components/DataTable'
import { DownloadIcon, SearchIcon, CalendarTodayIcon, ExpandMoreIcon, FilterListIcon, ChevronLeftIcon, ChevronRightIcon, BadgeIcon, DirectionsCarIcon, CreditCardIcon } from '../../components/Icons'

const API_BASE = '/api'

const DOC_TYPE_ICONS = {
  aadhaar: BadgeIcon,
  passport: BadgeIcon,
}

const DOC_TYPE_LABELS = {
  aadhaar: 'Aadhaar',
  passport: 'Passport',
}

const STATUS_MAP = {
  VERIFIED: 'verified',
  MANUAL_REVIEW: 'review',
  REJECTED: 'rejected',
}

const filterChips = [
  { label: 'All Records', active: true },
  { label: 'Verified', color: 'bg-[#10b981]' },
  { label: 'Manual Review', icon: true },
  { label: 'Rejected', color: 'bg-[#ef4444]' },
]

function formatDateTime(isoString) {
  if (!isoString) return { date: '—', time: '—' }
  try {
    const d = new Date(isoString)
    const date = d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
    const time = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }) + ' UTC'
    return { date, time }
  } catch {
    return { date: isoString, time: '' }
  }
}

function mapRecordToRow(record) {
  const statusKey = STATUS_MAP[record.status] || 'review'
  const docTypeKey = (record.document_type || '').toLowerCase()
  const DocIcon = DOC_TYPE_ICONS[docTypeKey] || BadgeIcon
  const { date, time } = formatDateTime(record.created_at)

  return {
    id: record.document_id || record.id || '—',
    applicant: record.filename || 'Unknown',
    email: '',
    docType: DOC_TYPE_LABELS[docTypeKey] || record.document_type || 'Document',
    docIcon: DocIcon,
    date,
    time,
    score: record.score,
    status: statusKey,
    nameColor: statusKey === 'rejected' ? 'text-error' : '',
  }
}

export default function VerificationHistory() {
  const navigate = useNavigate()
  const [activeFilter, setActiveFilter] = useState('All Records')
  const [searchQuery, setSearchQuery] = useState('')
  const [historyData, setHistoryData] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    async function fetchHistory() {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(`${API_BASE}/history?limit=100`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (!cancelled) {
          setHistoryData((data.records || []).map(mapRecordToRow))
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Failed to load verification history')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchHistory()
    return () => { cancelled = true }
  }, [])

  const filteredData = historyData.filter((row) => {
    const matchesFilter =
      activeFilter === 'All Records' ||
      (activeFilter === 'Verified' && row.status === 'verified') ||
      (activeFilter === 'Manual Review' && row.status === 'review') ||
      (activeFilter === 'Rejected' && row.status === 'rejected')

    if (!matchesFilter) return false
    if (!searchQuery.trim()) return true

    const q = searchQuery.toLowerCase()
    return (
      (row.id && String(row.id).toLowerCase().includes(q)) ||
      (row.applicant && row.applicant.toLowerCase().includes(q)) ||
      (row.docType && row.docType.toLowerCase().includes(q))
    )
  })

  return (
    <PageLayout>
      {/* Page Header */}
      <div className="py-stack-gap-lg flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="font-headline-md text-headline-md text-on-surface mb-1">Verification History</h1>
          <p className="font-body-md text-body-md text-on-surface-variant">Review and manage past identity verification records.</p>
        </div>
        <div className="flex gap-3">
          <button className="bg-surface-container-lowest border border-outline-variant text-primary font-label-md text-label-md px-4 py-2 rounded flex items-center gap-2 hover:bg-surface-container-high transition-colors shadow-sm">
            <DownloadIcon className="text-[18px]" />
            Export
          </button>
        </div>
      </div>

      {/* Filters Section */}
      <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-stack-gap-md mb-stack-gap-lg shadow-sm">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-stack-gap-md mb-stack-gap-md">
          <div className="md:col-span-5 relative">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-outline" />
            <input
              className="w-full pl-10 pr-4 py-2 bg-background border border-outline-variant rounded-lg text-body-md font-body-md text-on-surface placeholder-outline focus:outline-none focus:border-secondary focus:ring-1 focus:ring-secondary transition-shadow"
              placeholder="Search by ID or Document Type..."
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="md:col-span-2 relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-[18px]">calendar_today</span>
            <select className="w-full pl-9 pr-4 py-2 bg-background border border-outline-variant rounded-lg text-body-md font-body-md text-on-surface appearance-none focus:outline-none focus:border-secondary focus:ring-1 focus:ring-secondary cursor-pointer">
              <option>All Time</option>
              <option>Last 30 Days</option>
              <option>Last 7 Days</option>
              <option>Last 24 Hours</option>
            </select>
            <ExpandMoreIcon className="absolute right-3 top-1/2 -translate-y-1/2 text-outline pointer-events-none" />
          </div>
          <div className="md:col-span-2 relative">
            <select className="w-full pl-3 pr-8 py-2 bg-background border border-outline-variant rounded-lg text-body-md font-body-md text-on-surface appearance-none focus:outline-none focus:border-secondary focus:ring-1 focus:ring-secondary cursor-pointer">
              <option>Any Doc Type</option>
              <option>Aadhaar</option>
              <option>Passport</option>
            </select>
            <ExpandMoreIcon className="absolute right-3 top-1/2 -translate-y-1/2 text-outline pointer-events-none" />
          </div>
          <div className="md:col-span-2 relative">
            <select className="w-full pl-3 pr-8 py-2 bg-background border border-outline-variant rounded-lg text-body-md font-body-md text-on-surface appearance-none focus:outline-none focus:border-secondary focus:ring-1 focus:ring-secondary cursor-pointer">
              <option>Any Status</option>
              <option>Verified</option>
              <option>Manual Review</option>
              <option>Rejected</option>
            </select>
            <ExpandMoreIcon className="absolute right-3 top-1/2 -translate-y-1/2 text-outline pointer-events-none" />
          </div>
          <div className="md:col-span-1 flex justify-end">
            <button className="w-full md:w-auto bg-surface-container-highest text-primary p-2 rounded-lg border border-outline-variant hover:bg-surface-container-high transition-colors flex items-center justify-center" title="More Filters">
              <FilterListIcon />
            </button>
          </div>
        </div>

        {/* Quick Filter Chips */}
        <div className="flex flex-wrap gap-2 pt-3 border-t border-outline-variant border-opacity-50">
          {filterChips.map((chip) => (
            <button
              key={chip.label}
              onClick={() => setActiveFilter(chip.label)}
              className={`px-3 py-1 rounded-full font-label-md text-label-md border transition-colors flex items-center gap-1 ${
                activeFilter === chip.label
                  ? 'bg-secondary-container text-on-secondary-container border-secondary'
                  : 'bg-background text-on-surface-variant border-outline-variant hover:bg-surface-container-high'
              }`}
            >
              {chip.color && <span className={`w-2 h-2 rounded-full ${chip.color}`}></span>}
              {chip.icon && <span className="material-symbols-outlined text-[14px]">psychology</span>}
              {chip.label}
            </button>
          ))}
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-12 text-center shadow-sm">
          <div className="inline-flex items-center gap-3 text-on-surface-variant">
            <span className="material-symbols-outlined text-[24px] animate-spin">progress_activity</span>
            <span className="font-body-md text-body-md">Loading verification history...</span>
          </div>
        </div>
      )}

      {/* Error State */}
      {!loading && error && (
        <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-12 text-center shadow-sm">
          <div className="inline-flex flex-col items-center gap-3">
            <span className="material-symbols-outlined text-[32px] text-error">error</span>
            <span className="font-body-md text-body-md text-on-surface-variant">{error}</span>
            <button
              onClick={() => window.location.reload()}
              className="mt-2 px-4 py-2 bg-secondary text-on-secondary rounded-lg font-label-md text-label-md hover:bg-secondary/90 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && filteredData.length === 0 && (
        <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-12 text-center shadow-sm">
          <div className="inline-flex flex-col items-center gap-3">
            <span className="material-symbols-outlined text-[48px] text-outline">folder_off</span>
            <span className="font-headline-sm text-headline-sm text-on-surface">No verification records</span>
            <span className="font-body-md text-body-md text-on-surface-variant">
              {historyData.length === 0
                ? 'Documents verified through Parakh Seva will appear here.'
                : 'No records match your current filters.'}
            </span>
          </div>
        </div>
      )}

      {/* Data Table */}
      {!loading && !error && filteredData.length > 0 && (
        <>
          <DataTable columns={[
            { label: 'ID' },
            { label: 'Document' },
            { label: 'Type' },
            { label: 'Date & Time' },
            { label: 'Score', align: 'center' },
            { label: 'Status' },
            { label: 'Action', align: 'right' },
          ]}>
            {filteredData.map((row) => {
              const DocIcon = row.docIcon
              return (
                <tr
                  key={row.id}
                  className={`hover:bg-surface-container-low transition-colors group cursor-default ${row.status === 'rejected' ? 'bg-error-container bg-opacity-10' : ''}`}
                >
                  <td className="px-4 py-2 font-data-mono text-data-mono text-outline">{row.id}</td>
                  <td className="px-4 py-2">
                    <div className={`font-medium ${row.nameColor || ''}`}>{row.applicant}</div>
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex items-center gap-2">
                      <DocIcon />
                      <span>{row.docType}</span>
                    </div>
                  </td>
                  <td className="px-4 py-2 text-on-surface-variant text-[13px]">
                    {row.date}<br />{row.time}
                  </td>
                  <td className="px-4 py-2 text-center">
                    <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded font-data-mono text-data-mono font-bold ${
                      row.score !== null && row.score !== undefined
                        ? row.score >= 80
                          ? 'bg-[#f0fdf4] text-[#166534]'
                          : row.score >= 50
                            ? 'bg-[#fffbeb] text-[#b45309]'
                            : 'bg-[#fef2f2] text-[#991b1b] border border-[#fca5a5]'
                        : 'bg-[#f1f5f9] text-[#334155] border border-outline-variant'
                    }`}>
                      {row.score !== null && row.score !== undefined ? row.score : '--'}
                    </div>
                  </td>
                  <td className="px-4 py-2">
                    <StatusBadge status={row.status} />
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() => navigate('/document-analysis')}
                      className="text-secondary hover:text-on-secondary-fixed-variant font-medium text-[13px] transition-opacity opacity-0 group-hover:opacity-100"
                    >
                      View Report
                    </button>
                  </td>
                </tr>
              )
            })}
          </DataTable>

          {/* Pagination */}
          <div className="bg-surface border-t border-outline-variant px-4 py-3 flex items-center justify-between sm:px-6 rounded-b-lg">
            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-on-surface-variant font-body-md text-body-md">
                  Showing <span className="font-medium text-on-surface">1</span> to <span className="font-medium text-on-surface">{filteredData.length}</span> of <span className="font-medium text-on-surface">{filteredData.length}</span> records
                </p>
              </div>
              <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                <button className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-outline-variant bg-surface-container-lowest text-sm font-medium text-on-surface-variant hover:bg-surface-container-high transition-colors">
                  <ChevronLeftIcon />
                </button>
                <button className="z-10 bg-surface-container-highest border-secondary text-primary relative inline-flex items-center px-4 py-2 border text-sm font-medium">1</button>
                <button className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-outline-variant bg-surface-container-lowest text-sm font-medium text-on-surface-variant hover:bg-surface-container-high transition-colors">
                  <ChevronRightIcon />
                </button>
              </nav>
            </div>
          </div>
        </>
      )}
    </PageLayout>
  )
}
