import { useState, useEffect, useCallback } from 'react'
import PageLayout from '../../components/PageLayout'
import Toggle from '../../components/Toggle'
import { TuneIcon, FactCheckIcon } from '../../components/Icons'

const API_BASE = '/api'

const settingsTabs = [
  { label: 'Profile', icon: 'person' },
  { label: 'Security', icon: 'shield' },
  { label: 'Verification Rules', icon: 'fact_check' },
  { label: 'Risk Thresholds', icon: 'tune' },
  { label: 'API Configuration', icon: 'dns' },
  { label: 'Audit Logs', icon: 'history' },
]

const STORAGE_KEYS = {
  profile: 'parakhseva-profile',
  verificationRules: 'parakhseva-verification-rules',
  riskThresholds: 'parakhseva-risk-thresholds',
}

const defaultProfile = {
  displayName: 'Admin User',
  role: 'System Administrator',
  email: 'admin@parakhseva.gov.in',
  department: 'Identity Verification Division',
  status: 'Active',
}

const defaultRules = [
  { id: 'ocr_validation', label: 'OCR Validation', description: 'Multi-pass text extraction with EasyOCR for identity documents.', defaultOn: true },
  { id: 'field_extraction', label: 'Field Extraction', description: 'Rule-based extraction of identity fields from OCR output.', defaultOn: true },
  { id: 'document_validation', label: 'Document Validation', description: 'Verify document structure, required fields, and data consistency.', defaultOn: true },
  { id: 'face_verification', label: 'Face Verification', description: 'Biometric face matching between document photo and selfie using YuNet.', defaultOn: true },
  { id: 'mrz_detection', label: 'MRZ Detection', description: 'Machine-readable zone extraction for passports and travel documents.', defaultOn: true },
  { id: 'cross_field_consistency', label: 'Cross-field Consistency', description: 'Logical data matching across extracted identity fields.', defaultOn: true },
]

const defaultThresholds = {
  lowMax: 30,
  mediumMax: 60,
  highMax: 100,
}

function loadFromStorage(key, fallback) {
  try {
    const stored = localStorage.getItem(key)
    if (stored) return JSON.parse(stored)
  } catch { /* ignore */ }
  return fallback
}

function saveToStorage(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)) } catch { /* ignore */ }
}

// ─── Profile Tab ──────────────────────────────────────────────────────────────
function ProfileTab() {
  const [profile, setProfile] = useState(() => loadFromStorage(STORAGE_KEYS.profile, defaultProfile))
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(profile)
  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    setProfile(draft)
    saveToStorage(STORAGE_KEYS.profile, draft)
    setEditing(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <>
      <div className="flex justify-between items-end mb-2 border-b border-outline-variant pb-4">
        <div>
          <h3 className="font-headline-md text-headline-md text-primary">Profile</h3>
          <p className="text-on-surface-variant mt-1 max-w-2xl">Manage your administrator profile and account details.</p>
        </div>
        {editing ? (
          <div className="flex gap-2">
            <button onClick={() => { setEditing(false); setDraft(profile) }} className="px-4 py-2 rounded-lg font-label-md text-label-md text-secondary hover:bg-secondary/10 transition-colors">Cancel</button>
            <button onClick={handleSave} className="bg-primary text-on-primary font-label-md text-label-md px-4 py-2 rounded-lg hover:bg-primary-container transition-colors shadow-sm">Save Changes</button>
          </div>
        ) : (
          <button onClick={() => { setDraft(profile); setEditing(true) }} className="bg-primary text-on-primary font-label-md text-label-md px-4 py-2 rounded-lg hover:bg-primary-container transition-colors shadow-sm whitespace-nowrap">Edit Profile</button>
        )}
      </div>

      {saved && (
        <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px] text-emerald-600">check_circle</span>
          <span className="font-label-md text-label-md text-emerald-800">Profile saved successfully</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-12 gap-stack-gap-md">
        {/* Profile Card */}
        <div className="md:col-span-5 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm flex flex-col items-center">
          <div className="w-20 h-20 rounded-full bg-secondary-container flex items-center justify-center mb-4">
            <span className="material-symbols-outlined text-[40px] text-on-secondary-container">person</span>
          </div>
          <h4 className="font-headline-sm text-headline-sm text-primary">{profile.displayName}</h4>
          <p className="text-on-surface-variant text-sm mt-1">{profile.role}</p>
          <div className="mt-3 px-3 py-1 bg-emerald-50 border border-emerald-200 rounded-full">
            <span className="font-label-md text-[11px] text-emerald-800 uppercase tracking-wide">{profile.status}</span>
          </div>
        </div>

        {/* Details Card */}
        <div className="md:col-span-7 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm">
          <h4 className="font-headline-sm text-headline-sm text-primary mb-4">Account Details</h4>
          <div className="space-y-4">
            {[
              { label: 'Display Name', key: 'displayName', icon: 'badge' },
              { label: 'Email', key: 'email', icon: 'mail' },
              { label: 'Role', key: 'role', icon: 'admin_panel_settings' },
              { label: 'Department', key: 'department', icon: 'business' },
            ].map(({ label, key, icon }) => (
              <div key={key} className="flex items-center gap-3 p-3 rounded-lg border border-outline-variant/50 bg-surface">
                <span className="material-symbols-outlined text-[20px] text-secondary">{icon}</span>
                <div className="flex-1">
                  <span className="font-label-md text-[11px] text-on-surface-variant uppercase tracking-wider">{label}</span>
                  {editing ? (
                    <input
                      type="text"
                      value={draft[key]}
                      onChange={(e) => setDraft({ ...draft, [key]: e.target.value })}
                      className="block w-full mt-1 px-2 py-1 bg-surface-container-low border border-outline-variant rounded text-body-md text-on-surface focus:outline-none focus:border-secondary"
                    />
                  ) : (
                    <p className="font-body-md text-body-md text-primary font-medium">{profile[key]}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  )
}

// ─── Security Tab ─────────────────────────────────────────────────────────────
function SecurityTab() {
  const [sessionTimeout, setSessionTimeout] = useState(() => loadFromStorage('parakhseva-session-timeout', 30))
  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    saveToStorage('parakhseva-session-timeout', sessionTimeout)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <>
      <div className="flex justify-between items-end mb-2 border-b border-outline-variant pb-4">
        <div>
          <h3 className="font-headline-md text-headline-md text-primary">Security</h3>
          <p className="text-on-surface-variant mt-1 max-w-2xl">Session management and security status for the admin dashboard.</p>
        </div>
        <button onClick={handleSave} className="bg-primary text-on-primary font-label-md text-label-md px-4 py-2 rounded-lg hover:bg-primary-container transition-colors shadow-sm whitespace-nowrap">Save Changes</button>
      </div>

      {saved && (
        <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px] text-emerald-600">check_circle</span>
          <span className="font-label-md text-label-md text-emerald-800">Security settings saved</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-12 gap-stack-gap-md">
        {/* Security Status */}
        <div className="md:col-span-12 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm">
          <h4 className="font-headline-sm text-headline-sm text-primary mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary">verified_user</span>
            Security Status
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { label: 'API Connection', status: 'Secured', color: 'text-emerald-600', bg: 'bg-emerald-50', icon: 'lock' },
              { label: 'Data Encryption', status: 'TLS 1.3', color: 'text-emerald-600', bg: 'bg-emerald-50', icon: 'enhanced_encryption' },
              { label: 'Supabase RLS', status: 'Row-Level Security Active', color: 'text-emerald-600', bg: 'bg-emerald-50', icon: 'security' },
            ].map(({ label, status, color, bg, icon }) => (
              <div key={label} className={`p-4 rounded-lg border border-outline-variant ${bg}`}>
                <div className="flex items-center gap-2 mb-2">
                  <span className={`material-symbols-outlined text-[18px] ${color}`}>{icon}</span>
                  <span className="font-label-md text-label-md text-on-surface-variant uppercase">{label}</span>
                </div>
                <p className={`font-body-md text-body-md font-medium ${color}`}>{status}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Session Settings */}
        <div className="md:col-span-6 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm">
          <h4 className="font-headline-sm text-headline-sm text-primary mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary">timer</span>
            Session Settings
          </h4>
          <div className="space-y-4">
            <div>
              <label className="font-label-md text-label-md text-on-surface block mb-2">Session Timeout (minutes)</label>
              <select
                value={sessionTimeout}
                onChange={(e) => setSessionTimeout(Number(e.target.value))}
                className="w-full px-3 py-2 bg-surface-bright border border-outline-variant rounded-lg text-body-md text-on-surface focus:outline-none focus:border-secondary"
              >
                <option value={15}>15 minutes</option>
                <option value={30}>30 minutes</option>
                <option value={60}>60 minutes</option>
                <option value={120}>2 hours</option>
              </select>
              <p className="text-on-surface-variant text-xs mt-1">Automatically log out after period of inactivity.</p>
            </div>
          </div>
        </div>

        {/* Security Information */}
        <div className="md:col-span-6 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm">
          <h4 className="font-headline-sm text-headline-sm text-primary mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary">info</span>
            Security Information
          </h4>
          <div className="space-y-3">
            {[
              { label: 'Authentication', value: 'Local session-based (prototype)', icon: 'login' },
              { label: 'API Protection', value: 'CORS restricted to trusted origins', icon: 'http' },
              { label: 'File Validation', value: 'Extension + size limits enforced', icon: 'file_upload' },
              { label: 'Secrets Management', value: 'Environment variables (.env)', icon: 'key' },
            ].map(({ label, value, icon }) => (
              <div key={label} className="flex items-start gap-2 p-2 rounded-lg bg-surface">
                <span className="material-symbols-outlined text-[18px] text-secondary mt-0.5">{icon}</span>
                <div>
                  <span className="font-label-md text-label-md text-on-surface">{label}</span>
                  <p className="text-on-surface-variant text-xs">{value}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  )
}

// ─── Verification Rules Tab ───────────────────────────────────────────────────
function VerificationRulesTab() {
  const [rules, setRules] = useState(() => loadFromStorage(STORAGE_KEYS.verificationRules, defaultRules))
  const [saved, setSaved] = useState(false)

  const handleToggle = (id) => {
    setRules(rules.map(r => r.id === id ? { ...r, enabled: !r.enabled } : r))
  }

  const handleSave = () => {
    saveToStorage(STORAGE_KEYS.verificationRules, rules)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <>
      <div className="flex justify-between items-end mb-2 border-b border-outline-variant pb-4">
        <div>
          <h3 className="font-headline-md text-headline-md text-primary">Verification Rules</h3>
          <p className="text-on-surface-variant mt-1 max-w-2xl">Configure which verification checks are active in the pipeline.</p>
        </div>
        <button onClick={handleSave} className="bg-primary text-on-primary font-label-md text-label-md px-4 py-2 rounded-lg hover:bg-primary-container transition-colors shadow-sm whitespace-nowrap">Save Changes</button>
      </div>

      {saved && (
        <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px] text-emerald-600">check_circle</span>
          <span className="font-label-md text-label-md text-emerald-800">Verification rules saved</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-12 gap-stack-gap-md">
        <div className="md:col-span-12 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-6">
            <FactCheckIcon className="text-on-surface-variant" />
            <h4 className="font-headline-sm text-headline-sm text-primary">Active Verification Checks</h4>
          </div>
          <p className="text-on-surface-variant text-sm mb-4">Toggle which checks run during document verification. Changes persist across sessions.</p>
          <div className="space-y-3">
            {rules.map((rule) => (
              <div key={rule.id} className="flex items-center justify-between p-4 border border-outline-variant rounded-lg bg-surface-container-low hover:bg-surface-container transition-colors">
                <div className="flex-1">
                  <p className="font-label-md text-label-md text-primary">{rule.label}</p>
                  <p className="text-[11px] text-on-surface-variant mt-0.5">{rule.description}</p>
                </div>
                <button
                  onClick={() => handleToggle(rule.id)}
                  className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-secondary focus:ring-offset-2 ml-4 ${
                    rule.enabled !== false ? 'bg-secondary-container' : 'bg-outline-variant'
                  }`}
                >
                  <span
                    className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform ${
                      rule.enabled !== false ? 'translate-x-4' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  )
}

// ─── Risk Thresholds Tab ──────────────────────────────────────────────────────
function RiskThresholdsTab() {
  const [thresholds, setThresholds] = useState(() => loadFromStorage(STORAGE_KEYS.riskThresholds, defaultThresholds))
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  const validate = (t) => {
    if (t.lowMax < 0 || t.lowMax > 100) return 'Low threshold must be 0–100'
    if (t.mediumMax <= t.lowMax) return 'Medium must be greater than Low'
    if (t.highMax <= t.mediumMax) return 'High must be greater than Medium'
    if (t.highMax > 100) return 'High threshold cannot exceed 100'
    return ''
  }

  const handleSave = () => {
    const err = validate(thresholds)
    if (err) { setError(err); return }
    saveToStorage(STORAGE_KEYS.riskThresholds, thresholds)
    setError('')
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const lowPct = thresholds.lowMax
  const medPct = thresholds.mediumMax - thresholds.lowMax
  const highPct = thresholds.highMax - thresholds.mediumMax

  const ranges = [
    { label: 'Low Risk Range', color: 'bg-green-500', from: 0, to: thresholds.lowMax, left: '0%', width: `${lowPct}%` },
    { label: 'Medium Risk Range', color: 'bg-yellow-500', from: thresholds.lowMax + 1, to: thresholds.mediumMax, left: `${lowPct}%`, width: `${medPct}%` },
    { label: 'High Risk Range', color: 'bg-red-500', from: thresholds.mediumMax + 1, to: thresholds.highMax, left: `${lowPct + medPct}%`, width: `${highPct}%` },
  ]

  return (
    <>
      <div className="flex justify-between items-end mb-2 border-b border-outline-variant pb-4">
        <div>
          <h3 className="font-headline-md text-headline-md text-primary">Risk Thresholds</h3>
          <p className="text-on-surface-variant mt-1 max-w-2xl">Configure the score ranges for risk categorization.</p>
        </div>
        <button onClick={handleSave} className="bg-primary text-on-primary font-label-md text-label-md px-4 py-2 rounded-lg hover:bg-primary-container transition-colors shadow-sm whitespace-nowrap">Save Changes</button>
      </div>

      {saved && (
        <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px] text-emerald-600">check_circle</span>
          <span className="font-label-md text-label-md text-emerald-800">Risk thresholds saved</span>
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 bg-error-container border border-error/30 rounded-lg flex items-center gap-2">
          <span className="material-symbols-outlined text-[18px] text-error">error</span>
          <span className="font-label-md text-label-md text-on-surface">{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-12 gap-stack-gap-md">
        {/* Score Ranges Card */}
        <div className="md:col-span-12 lg:col-span-7 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-6">
            <TuneIcon className="text-on-surface-variant" />
            <h4 className="font-headline-sm text-headline-sm text-primary">Score Calibration</h4>
          </div>
          <div className="space-y-8">
            {ranges.map((range, i) => (
              <div key={i}>
                <div className="flex justify-between items-center mb-2">
                  <label className="font-label-md text-label-md text-on-surface flex items-center gap-2">
                    <div className={`w-3 h-3 rounded-full ${range.color}`}></div>
                    {range.label}
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min={0}
                      max={100}
                      value={range.from}
                      onChange={(e) => {
                        const val = Math.max(0, Math.min(100, Number(e.target.value)))
                        if (i === 0) setThresholds({ ...thresholds, lowMax: val })
                        else if (i === 1) setThresholds({ ...thresholds, lowMax: val - 1 })
                        else setThresholds({ ...thresholds, mediumMax: val - 1 })
                      }}
                      className="w-14 px-1 py-0.5 bg-surface-container border border-outline-variant rounded text-center text-body-md text-primary font-data-mono focus:outline-none focus:border-secondary"
                    />
                    <span className="text-on-surface-variant text-xs">–</span>
                    <input
                      type="number"
                      min={0}
                      max={100}
                      value={range.to}
                      onChange={(e) => {
                        const val = Math.max(0, Math.min(100, Number(e.target.value)))
                        if (i === 0) setThresholds({ ...thresholds, lowMax: val })
                        else if (i === 1) setThresholds({ ...thresholds, mediumMax: val })
                        else setThresholds({ ...thresholds, highMax: val })
                      }}
                      className="w-14 px-1 py-0.5 bg-surface-container border border-outline-variant rounded text-center text-body-md text-primary font-data-mono focus:outline-none focus:border-secondary"
                    />
                  </div>
                </div>
                <div className="relative w-full h-2 bg-surface-variant rounded-full mt-2">
                  <div className={`absolute top-0 h-full ${range.color} rounded-full`} style={{ left: range.left, width: range.width }}></div>
                </div>
              </div>
            ))}
            <div className="flex justify-between text-[10px] text-outline mt-1">
              <span>0</span>
              <span>100</span>
            </div>
          </div>
        </div>

        {/* Threshold Info */}
        <div className="md:col-span-12 lg:col-span-5 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm">
          <h4 className="font-headline-sm text-headline-sm text-primary mb-4">Threshold Guide</h4>
          <div className="space-y-3">
            <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-3 h-3 rounded-full bg-green-500"></div>
                <span className="font-label-md text-label-md text-emerald-800">Low Risk ({thresholds.lowMax} or below)</span>
              </div>
              <p className="text-xs text-emerald-700">Documents pass verification with high confidence.</p>
            </div>
            <div className="p-3 rounded-lg bg-amber-50 border border-amber-200">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                <span className="font-label-md text-label-md text-amber-800">Medium Risk ({thresholds.lowMax + 1}–{thresholds.mediumMax})</span>
              </div>
              <p className="text-xs text-amber-700">Some warnings detected. Manual review recommended.</p>
            </div>
            <div className="p-3 rounded-lg bg-red-50 border border-red-200">
              <div className="flex items-center gap-2 mb-1">
                <div className="w-3 h-3 rounded-full bg-red-500"></div>
                <span className="font-label-md text-label-md text-red-800">High Risk ({thresholds.mediumMax + 1}–{thresholds.highMax})</span>
              </div>
              <p className="text-xs text-red-700">Critical issues found. Verification likely rejected.</p>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

// ─── API Configuration Tab ────────────────────────────────────────────────────
function ApiConfigTab() {
  const [healthStatus, setHealthStatus] = useState('checking')
  const [healthData, setHealthData] = useState(null)
  const [lastChecked, setLastChecked] = useState(null)

  const testConnection = useCallback(async () => {
    setHealthStatus('checking')
    try {
      const res = await fetch(`${API_BASE}/health`)
      if (res.ok) {
        const data = await res.json()
        setHealthData(data)
        setHealthStatus('connected')
      } else {
        setHealthStatus('error')
      }
    } catch {
      setHealthStatus('error')
    }
    setLastChecked(new Date().toLocaleTimeString())
  }, [])

  useEffect(() => { testConnection() }, [testConnection])

  return (
    <>
      <div className="flex justify-between items-end mb-2 border-b border-outline-variant pb-4">
        <div>
          <h3 className="font-headline-md text-headline-md text-primary">API Configuration</h3>
          <p className="text-on-surface-variant mt-1 max-w-2xl">Backend connection status and API health monitoring.</p>
        </div>
        <button onClick={testConnection} className="bg-primary text-on-primary font-label-md text-label-md px-4 py-2 rounded-lg hover:bg-primary-container transition-colors shadow-sm whitespace-nowrap flex items-center gap-2">
          <span className="material-symbols-outlined text-[16px]">refresh</span>
          Test Connection
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-stack-gap-md">
        {/* Connection Status */}
        <div className="md:col-span-6 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm">
          <h4 className="font-headline-sm text-headline-sm text-primary mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary">dns</span>
            Backend API
          </h4>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-lg bg-surface border border-outline-variant/50">
              <span className="font-label-md text-label-md text-on-surface-variant">Status</span>
              <div className="flex items-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${
                  healthStatus === 'connected' ? 'bg-emerald-500' :
                  healthStatus === 'checking' ? 'bg-amber-500 animate-pulse' :
                  'bg-red-500'
                }`}></span>
                <span className={`font-label-md text-label-md ${
                  healthStatus === 'connected' ? 'text-emerald-600' :
                  healthStatus === 'checking' ? 'text-amber-600' :
                  'text-red-600'
                }`}>
                  {healthStatus === 'connected' ? 'Connected' :
                   healthStatus === 'checking' ? 'Checking...' :
                   'Disconnected'}
                </span>
              </div>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-surface border border-outline-variant/50">
              <span className="font-label-md text-label-md text-on-surface-variant">Base URL</span>
              <span className="font-data-mono text-data-mono text-xs text-on-surface bg-surface-container px-2 py-1 rounded">/api</span>
            </div>
            {healthData && (
              <>
                <div className="flex items-center justify-between p-3 rounded-lg bg-surface border border-outline-variant/50">
                  <span className="font-label-md text-label-md text-on-surface-variant">Service</span>
                  <span className="font-data-mono text-data-mono text-xs text-primary">{healthData.service}</span>
                </div>
                <div className="flex items-center justify-between p-3 rounded-lg bg-surface border border-outline-variant/50">
                  <span className="font-label-md text-label-md text-on-surface-variant">Version</span>
                  <span className="font-data-mono text-data-mono text-xs text-primary">{healthData.version}</span>
                </div>
              </>
            )}
            {lastChecked && (
              <p className="text-on-surface-variant text-xs">Last checked: {lastChecked}</p>
            )}
          </div>
        </div>

        {/* Supabase Status */}
        <div className="md:col-span-6 bg-surface-container-lowest border border-outline-variant rounded-xl p-6 shadow-sm">
          <h4 className="font-headline-sm text-headline-sm text-primary mb-4 flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary">storage</span>
            Supabase Database
          </h4>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-lg bg-surface border border-outline-variant/50">
              <span className="font-label-md text-label-md text-on-surface-variant">Status</span>
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                <span className="font-label-md text-label-md text-amber-600">Not Configured</span>
              </div>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-surface border border-outline-variant/50">
              <span className="font-label-md text-label-md text-on-surface-variant">Table</span>
              <span className="font-data-mono text-data-mono text-xs text-primary">verification_records</span>
            </div>
            <div className="p-3 rounded-lg bg-amber-50 border border-amber-200">
              <div className="flex items-start gap-2">
                <span className="material-symbols-outlined text-[16px] text-amber-600 mt-0.5">info</span>
                <p className="text-xs text-amber-700">Supabase URL and Key are configured in the backend .env file. Credentials are never exposed to the frontend.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  )
}

// ─── Audit Logs Tab ───────────────────────────────────────────────────────────
function AuditLogsTab() {
  const [records, setRecords] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    let cancelled = false
    async function fetchHistory() {
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(`${API_BASE}/history?limit=100`)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const data = await res.json()
        if (!cancelled) setRecords(data.records || [])
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load audit logs')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchHistory()
    return () => { cancelled = true }
  }, [])

  const filtered = records.filter((r) => {
    if (!searchQuery.trim()) return true
    const q = searchQuery.toLowerCase()
    return (
      (r.document_id && r.document_id.toLowerCase().includes(q)) ||
      (r.document_type && r.document_type.toLowerCase().includes(q)) ||
      (r.status && r.status.toLowerCase().includes(q)) ||
      (r.filename && r.filename.toLowerCase().includes(q))
    )
  })

  const statusColor = (status) => {
    if (status === 'VERIFIED') return 'bg-emerald-50 text-emerald-800 border border-emerald-200'
    if (status === 'REJECTED') return 'bg-red-50 text-red-800 border border-red-200'
    return 'bg-amber-50 text-amber-800 border border-amber-200'
  }

  return (
    <>
      <div className="flex justify-between items-end mb-2 border-b border-outline-variant pb-4">
        <div>
          <h3 className="font-headline-md text-headline-md text-primary">Audit Logs</h3>
          <p className="text-on-surface-variant mt-1 max-w-2xl">Verification activity history from the backend database.</p>
        </div>
      </div>

      {/* Search */}
      <div className="mb-4">
        <div className="relative">
          <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-lg">search</span>
          <input
            className="w-full pl-10 pr-4 py-2 bg-surface-container-highest border border-outline-variant rounded-lg text-body-md text-on-surface focus:outline-none focus:border-secondary focus:ring-1 focus:ring-secondary transition-all"
            placeholder="Search by ID, type, status, or filename..."
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-12 text-center">
          <div className="inline-flex items-center gap-3 text-on-surface-variant">
            <span className="material-symbols-outlined text-[24px] animate-spin">progress_activity</span>
            <span className="font-body-md text-body-md">Loading audit logs...</span>
          </div>
        </div>
      )}

      {/* Error */}
      {!loading && error && (
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-12 text-center">
          <div className="inline-flex flex-col items-center gap-3">
            <span className="material-symbols-outlined text-[32px] text-error">error</span>
            <span className="font-body-md text-body-md text-on-surface-variant">{error}</span>
          </div>
        </div>
      )}

      {/* Empty */}
      {!loading && !error && filtered.length === 0 && (
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-12 text-center">
          <div className="inline-flex flex-col items-center gap-3">
            <span className="material-symbols-outlined text-[48px] text-outline">folder_off</span>
            <span className="font-headline-sm text-headline-sm text-on-surface">No audit records</span>
            <span className="font-body-md text-body-md text-on-surface-variant">
              {records.length === 0
                ? 'Verification records will appear here once documents are verified.'
                : 'No records match your search.'}
            </span>
          </div>
        </div>
      )}

      {/* Records Table */}
      {!loading && !error && filtered.length > 0 && (
        <div className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-surface-container-low border-b border-outline-variant">
                  {['Timestamp', 'Document ID', 'Type', 'Filename', 'Status', 'Score'].map((h) => (
                    <th key={h} className="px-4 py-3 font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="font-body-md text-body-md">
                {filtered.map((record, i) => (
                  <tr key={record.document_id || i} className="border-b border-outline-variant hover:bg-surface-container-low transition-colors">
                    <td className="px-4 py-3 text-on-surface-variant text-sm">
                      {record.created_at ? new Date(record.created_at).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-3 font-data-mono text-data-mono text-primary text-sm">{record.document_id || '—'}</td>
                    <td className="px-4 py-3 text-on-surface-variant text-sm uppercase">{record.document_type || '—'}</td>
                    <td className="px-4 py-3 text-on-surface text-sm max-w-[200px] truncate">{record.filename || '—'}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded font-label-md text-[11px] uppercase tracking-wide ${statusColor(record.status)}`}>
                        {record.status || '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-data-mono text-data-mono text-sm">
                      {record.score != null ? (
                        <span className={`font-bold ${
                          record.score >= 80 ? 'text-emerald-600' :
                          record.score >= 50 ? 'text-amber-600' : 'text-red-600'
                        }`}>{record.score}</span>
                      ) : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  )
}

// ─── Tab Content Router ───────────────────────────────────────────────────────
function TabContent({ activeTab }) {
  switch (activeTab) {
    case 'Profile': return <ProfileTab />
    case 'Security': return <SecurityTab />
    case 'Verification Rules': return <VerificationRulesTab />
    case 'Risk Thresholds': return <RiskThresholdsTab />
    case 'API Configuration': return <ApiConfigTab />
    case 'Audit Logs': return <AuditLogsTab />
    default: return <RiskThresholdsTab />
  }
}

// ─── Main Settings Page ───────────────────────────────────────────────────────
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
                className={`whitespace-nowrap px-4 py-2 rounded-lg font-label-md text-label-md transition-colors flex items-center gap-2 ${
                  activeTab === tab.label
                    ? 'bg-surface-container-high text-primary font-bold border-l-4 border-secondary'
                    : 'text-on-surface-variant hover:bg-surface-container-high'
                }`}
              >
                <span className="material-symbols-outlined text-[18px]">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </nav>
        </aside>

        {/* Settings Detail Pane */}
        <section className="flex-1 flex flex-col gap-stack-gap-lg">
          <TabContent activeTab={activeTab} />
        </section>
      </div>
    </PageLayout>
  )
}
