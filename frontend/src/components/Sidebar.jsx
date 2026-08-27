import { NavLink } from 'react-router-dom'
import {
  DashboardIcon,
  ShieldIcon,
  HistoryIcon,
  DescriptionIcon,
  FaceIcon,
  AssessmentIcon,
  SettingsIcon
} from './Icons'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: DashboardIcon },
  { to: '/new-verification', label: 'New Verification', icon: ShieldIcon },
  { to: '/verification-history', label: 'Verification History', icon: HistoryIcon },
  { to: '/document-analysis', label: 'Document Analysis', icon: DescriptionIcon },
  { to: '/identity-matching', label: 'Identity Matching', icon: FaceIcon },
  { to: '/risk-report', label: 'Risk Reports', icon: AssessmentIcon },
]

export default function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-surface-container-lowest border-r border-outline-variant flex flex-col p-gutter z-50">
      <div className="flex items-center gap-3 mb-8 px-4 mt-2">
        <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center text-white">
          <span className="material-symbols-outlined icon-fill" style={{ fontSize: '20px' }}>shield</span>
        </div>
        <div>
          <h1 className="font-headline-sm text-headline-sm font-bold text-primary">Parakh Seva</h1>
          <p className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">Identity Platform</p>
        </div>
      </div>

      <nav className="flex-1 space-y-2">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 rounded-lg font-label-md text-label-md transition-all duration-200 ease-in-out active:scale-95 ${
                isActive
                  ? 'bg-secondary-container text-on-secondary-container font-bold'
                  : 'text-on-surface-variant hover:bg-surface-container-high'
              }`
            }
          >
            <Icon />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="mt-auto">
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            `flex items-center gap-3 px-4 py-3 rounded-lg font-label-md text-label-md transition-all duration-200 ease-in-out active:scale-95 ${
              isActive
                ? 'bg-secondary-container text-on-secondary-container font-bold'
                : 'text-on-surface-variant hover:bg-surface-container-high'
            }`
          }
        >
          <SettingsIcon />
          <span>Settings</span>
        </NavLink>
        <div className="mt-4 px-4 py-3 border-t border-outline-variant">
          <div className="flex items-center gap-2 text-on-surface-variant text-xs">
            <span className="w-2 h-2 rounded-full bg-green-500"></span>
            System Operational
          </div>
        </div>
      </div>
    </aside>
  )
}
