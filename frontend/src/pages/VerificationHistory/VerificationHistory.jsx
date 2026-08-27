import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageLayout from '../../components/PageLayout'
import StatusBadge from '../../components/StatusBadge'
import DataTable from '../../components/DataTable'
import { DownloadIcon, SearchIcon, CalendarTodayIcon, ExpandMoreIcon, FilterListIcon, ChevronLeftIcon, ChevronRightIcon, BadgeIcon, DirectionsCarIcon, CreditCardIcon } from '../../components/Icons'

const historyData = [
  {
    id: 'V-99382',
    applicant: 'Sarah Jenkins',
    email: 's.jenkins@example.com',
    docType: 'US Passport',
    docIcon: BadgeIcon,
    date: 'Oct 24, 2023',
    time: '14:32:01 UTC',
    riskScore: 12,
    faceMatch: '98.2%',
    faceMatchColor: 'text-[#10b981]',
    status: 'verified',
    riskBg: 'bg-[#f0fdf4] text-[#166534]',
    showInvestigate: false,
  },
  {
    id: 'V-99381',
    applicant: 'Michael Chen',
    email: 'mchen88@domain.net',
    docType: "CA Driver's License",
    docIcon: DirectionsCarIcon,
    date: 'Oct 24, 2023',
    time: '14:28:44 UTC',
    riskScore: 68,
    faceMatch: '72.4%',
    faceMatchColor: 'text-[#f59e0b]',
    status: 'flagged',
    riskBg: 'bg-[#fffbeb] text-[#b45309]',
    showInvestigate: false,
  },
  {
    id: 'V-99380',
    applicant: 'Unknown Entity',
    email: 'temp_9182@anon.co',
    docType: 'UK National ID',
    docIcon: CreditCardIcon,
    date: 'Oct 24, 2023',
    time: '14:15:12 UTC',
    riskScore: 94,
    faceMatch: '41.0%',
    faceMatchColor: 'text-[#ef4444]',
    status: 'highRisk',
    riskBg: 'bg-[#fef2f2] text-[#991b1b] border border-[#fca5a5]',
    showInvestigate: true,
    nameColor: 'text-error',
  },
  {
    id: 'V-99379',
    applicant: 'Elena Rodriguez',
    email: 'erod@company.io',
    docType: 'ES Passport',
    docIcon: BadgeIcon,
    date: 'Oct 24, 2023',
    time: '13:55:09 UTC',
    riskScore: 8,
    faceMatch: '99.1%',
    faceMatchColor: 'text-[#10b981]',
    status: 'verified',
    riskBg: 'bg-[#f0fdf4] text-[#166534]',
    showInvestigate: false,
  },
  {
    id: 'V-99378',
    applicant: 'David Kim',
    email: 'dkim_design@mail.com',
    docType: "NY Driver's License",
    docIcon: DirectionsCarIcon,
    date: 'Oct 24, 2023',
    time: '13:12:33 UTC',
    riskScore: null,
    faceMatch: 'Pending',
    faceMatchColor: 'text-on-surface-variant',
    status: 'review',
    riskBg: 'bg-[#f1f5f9] text-[#334155] border border-outline-variant',
    showInvestigate: true,
    showStartReview: true,
  },
]

const filterChips = [
  { label: 'All Records', active: true },
  { label: 'Verified', color: 'bg-[#10b981]' },
  { label: 'Suspicious', color: 'bg-[#f59e0b]' },
  { label: 'High Risk', color: 'bg-[#ef4444]' },
  { label: 'Manual Review', icon: true },
]

export default function VerificationHistory() {
  const navigate = useNavigate()
  const [activeFilter, setActiveFilter] = useState('All Records')
  const [searchQuery, setSearchQuery] = useState('')

  const filteredData = historyData.filter((row) => {
    if (activeFilter === 'All Records') return true
    if (activeFilter === 'Verified') return row.status === 'verified'
    if (activeFilter === 'Suspicious') return row.status === 'flagged'
    if (activeFilter === 'High Risk') return row.status === 'highRisk'
    if (activeFilter === 'Manual Review') return row.status === 'review'
    return true
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
              placeholder="Search by ID, Applicant Name, or Email..."
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <div className="md:col-span-2 relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-[18px]">calendar_today</span>
            <select className="w-full pl-9 pr-4 py-2 bg-background border border-outline-variant rounded-lg text-body-md font-body-md text-on-surface appearance-none focus:outline-none focus:border-secondary focus:ring-1 focus:ring-secondary cursor-pointer">
              <option>Last 30 Days</option>
              <option>Last 7 Days</option>
              <option>Last 24 Hours</option>
            </select>
            <ExpandMoreIcon className="absolute right-3 top-1/2 -translate-y-1/2 text-outline pointer-events-none" />
          </div>
          <div className="md:col-span-2 relative">
            <select className="w-full pl-3 pr-8 py-2 bg-background border border-outline-variant rounded-lg text-body-md font-body-md text-on-surface appearance-none focus:outline-none focus:border-secondary focus:ring-1 focus:ring-secondary cursor-pointer">
              <option>Any Doc Type</option>
              <option>Passport</option>
              <option>Driver's License</option>
              <option>National ID</option>
            </select>
            <ExpandMoreIcon className="absolute right-3 top-1/2 -translate-y-1/2 text-outline pointer-events-none" />
          </div>
          <div className="md:col-span-2 relative">
            <select className="w-full pl-3 pr-8 py-2 bg-background border border-outline-variant rounded-lg text-body-md font-body-md text-on-surface appearance-none focus:outline-none focus:border-secondary focus:ring-1 focus:ring-secondary cursor-pointer">
              <option>Any Risk Level</option>
              <option>Low Risk</option>
              <option>Medium Risk</option>
              <option>High Risk</option>
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

      {/* Data Table */}
      <DataTable columns={[
        { label: 'ID' },
        { label: 'Applicant' },
        { label: 'Document' },
        { label: 'Date & Time' },
        { label: 'Risk Score', align: 'center' },
        { label: 'Face Match', align: 'center' },
        { label: 'Status' },
        { label: 'Action', align: 'right' },
      ]}>
        {filteredData.map((row) => {
          const DocIcon = row.docIcon
          return (
            <tr
              key={row.id}
              className={`hover:bg-surface-container-low transition-colors group cursor-default ${row.status === 'highRisk' ? 'bg-error-container bg-opacity-10' : ''}`}
            >
              <td className="px-4 py-2 font-data-mono text-data-mono text-outline">{row.id}</td>
              <td className="px-4 py-2">
                <div className={`font-medium ${row.nameColor || ''}`}>{row.applicant}</div>
                <div className="text-[12px] text-on-surface-variant">{row.email}</div>
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
                <div className={`inline-flex items-center gap-1 px-2 py-0.5 rounded font-data-mono text-data-mono font-bold ${row.riskBg}`}>
                  {row.riskScore !== null ? row.riskScore : '--'}
                </div>
              </td>
              <td className="px-4 py-2 text-center">
                <span className={`${row.faceMatchColor} font-data-mono text-data-mono font-medium`}>{row.faceMatch}</span>
              </td>
              <td className="px-4 py-2">
                <StatusBadge status={row.status} />
              </td>
              <td className="px-4 py-2 text-right">
                <button
                  onClick={() => navigate('/risk-report')}
                  className={`text-secondary hover:text-on-secondary-fixed-variant font-medium text-[13px] transition-opacity ${
                    row.showStartReview
                      ? 'opacity-100'
                      : 'opacity-0 group-hover:opacity-100'
                  }`}
                >
                  {row.showStartReview ? 'Start Review' : row.showInvestigate ? 'Investigate' : 'View Report'}
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
              Showing <span className="font-medium text-on-surface">1</span> to <span className="font-medium text-on-surface">10</span> of <span className="font-medium text-on-surface">2,486</span> records
            </p>
          </div>
          <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
            <button className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-outline-variant bg-surface-container-lowest text-sm font-medium text-on-surface-variant hover:bg-surface-container-high transition-colors">
              <ChevronLeftIcon />
            </button>
            <button className="z-10 bg-surface-container-highest border-secondary text-primary relative inline-flex items-center px-4 py-2 border text-sm font-medium">1</button>
            <button className="bg-surface-container-lowest border-outline-variant text-on-surface-variant hover:bg-surface-container-high relative inline-flex items-center px-4 py-2 border text-sm font-medium transition-colors">2</button>
            <button className="bg-surface-container-lowest border-outline-variant text-on-surface-variant hover:bg-surface-container-high relative inline-flex items-center px-4 py-2 border text-sm font-medium transition-colors">3</button>
            <span className="relative inline-flex items-center px-4 py-2 border border-outline-variant bg-surface-container-lowest text-sm font-medium text-on-surface-variant">...</span>
            <button className="bg-surface-container-lowest border-outline-variant text-on-surface-variant hover:bg-surface-container-high relative inline-flex items-center px-4 py-2 border text-sm font-medium transition-colors">249</button>
            <button className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-outline-variant bg-surface-container-lowest text-sm font-medium text-on-surface-variant hover:bg-surface-container-high transition-colors">
              <ChevronRightIcon />
            </button>
          </nav>
        </div>
      </div>
    </PageLayout>
  )
}
