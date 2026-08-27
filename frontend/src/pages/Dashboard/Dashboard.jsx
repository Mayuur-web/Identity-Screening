import { useNavigate } from 'react-router-dom'
import PageLayout from '../../components/PageLayout'
import ScoreCard from '../../components/ScoreCard'
import StatusBadge from '../../components/StatusBadge'
import { AddIcon } from '../../components/Icons'

const kpiData = [
  { label: 'Total Verifications', value: '12,486' },
  { label: 'Verified', value: '9,842', trend: 'up' },
  { label: 'Suspicious', value: '1,734', borderColor: 'border-l-4 border-l-amber-500' },
  { label: 'High Risk', value: '910', borderColor: 'border-l-4 border-l-red-600' },
  { label: 'Avg Time', value: '18.4', unit: 'sec' },
]

const recentData = [
  { id: 'V-00145', type: 'Aadhaar', applicant: 'Rahul Sharma', status: 'verified', risk: '12', faceMatch: '98.5%', date: 'Oct 24, 10:42 AM', action: 'Review' },
  { id: 'V-00146', type: 'PAN', applicant: 'Priya Verma', status: 'suspicious', risk: '68', faceMatch: '72.1%', date: 'Oct 24, 10:45 AM', action: 'Investigate', riskColor: 'score-amber', faceColor: 'text-amber-700' },
  { id: 'V-00147', type: 'Passport', applicant: 'Aman Kumar', status: 'highRisk', risk: '94', faceMatch: '45.0%', date: 'Oct 24, 10:51 AM', action: 'Escalate', riskColor: 'score-red', faceColor: 'text-red-700' },
  { id: 'V-00148', type: 'Aadhaar', applicant: 'Sneha Patel', status: 'verified', risk: '08', faceMatch: '99.2%', date: 'Oct 24, 10:55 AM', action: 'Review' },
]

const barHeights = [30, 50, 40, 70, 60, 80, 90, 75, 85, 95]

export default function Dashboard() {
  const navigate = useNavigate()

  return (
    <PageLayout showSearch>
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
        {kpiData.map((kpi, i) => (
          <ScoreCard key={i} {...kpi} />
        ))}
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-12 gap-6 mb-8">
        {/* Left Chart: Verification Activity */}
        <div className="col-span-12 lg:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex flex-col">
          <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Verification Activity</h3>
          <div className="flex-1 w-full bg-surface-container-low rounded border border-outline-variant border-dashed flex items-center justify-center relative overflow-hidden min-h-[250px]">
            <div className="absolute bottom-0 left-0 w-full h-full flex items-end px-4 gap-2 opacity-20">
              {barHeights.map((h, i) => (
                <div key={i} className="w-1/12 bg-primary rounded-t" style={{ height: `${h}%` }} />
              ))}
            </div>
            <span className="text-on-surface-variant font-data-mono text-data-mono z-10">[Line Chart: Weekly Trends]</span>
          </div>
        </div>

        {/* Right Chart: Risk Distribution */}
        <div className="col-span-12 lg:col-span-4 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 flex flex-col">
          <h3 className="font-headline-sm text-headline-sm text-on-surface mb-4">Risk Distribution</h3>
          <div className="flex-1 w-full flex items-center justify-center relative min-h-[250px]">
            <div className="w-48 h-48 rounded-full border-[16px] border-green-100 relative">
              <div className="absolute inset-0 rounded-full border-[16px] border-amber-300" style={{ clipPath: 'polygon(50% 50%, 100% 0, 100% 100%, 80% 100%)' }} />
              <div className="absolute inset-0 rounded-full border-[16px] border-red-500" style={{ clipPath: 'polygon(50% 50%, 80% 100%, 0 100%, 0 80%)' }} />
              <div className="absolute inset-0 rounded-full border-[16px] border-green-500" style={{ clipPath: 'polygon(50% 50%, 0 80%, 0 0, 100% 0)' }} />
            </div>
            <div className="absolute bottom-0 w-full flex justify-center gap-4 pt-4 bg-surface-container-lowest/80 backdrop-blur-sm">
              <div className="flex items-center gap-1 font-label-md text-label-md text-on-surface-variant">
                <span className="w-3 h-3 rounded-full bg-green-500"></span> 79%
              </div>
              <div className="flex items-center gap-1 font-label-md text-label-md text-on-surface-variant">
                <span className="w-3 h-3 rounded-full bg-amber-400"></span> 14%
              </div>
              <div className="flex items-center gap-1 font-label-md text-label-md text-on-surface-variant">
                <span className="w-3 h-3 rounded-full bg-red-600"></span> 7%
              </div>
            </div>
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
              {recentData.map((row, i) => (
                <tr key={i} className={`border-b border-outline-variant hover:bg-surface-container-low transition-colors group ${i === recentData.length - 1 ? 'border-b-0' : ''}`}>
                  <td className="px-6 py-3 font-data-mono text-data-mono text-on-surface">{row.id}</td>
                  <td className="px-6 py-3 text-on-surface-variant">{row.type}</td>
                  <td className="px-6 py-3 text-on-surface font-medium">{row.applicant}</td>
                  <td className="px-6 py-3"><StatusBadge status={row.status} /></td>
                  <td className={`px-6 py-3 font-data-mono text-data-mono ${row.riskColor || 'score-green'}`}>{row.risk} / 100</td>
                  <td className={`px-6 py-3 font-data-mono text-data-mono ${row.faceColor || ''}`}>{row.faceMatch}</td>
                  <td className="px-6 py-3 text-on-surface-variant">{row.date}</td>
                  <td className="px-6 py-3 text-right">
                    <button
                      onClick={() => navigate('/risk-report')}
                      className="text-secondary font-label-md text-label-md hover:underline opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      {row.action}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </PageLayout>
  )
}
