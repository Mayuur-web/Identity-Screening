import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { VerifiedUserIcon, LockIcon, MailIcon, KeyIcon, ArrowForwardIcon, GavelIcon } from '../../components/Icons'

export default function Login() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    navigate('/dashboard')
  }

  return (
    <div className="bg-surface text-on-surface min-h-screen flex antialiased">
      {/* Left Column: Branding & Visual */}
      <div className="hidden lg:flex lg:w-1/2 relative bg-primary overflow-hidden flex-col justify-center items-center p-12">
        <div className="absolute inset-0 z-0">
          <div
            className="w-full h-full bg-cover bg-center opacity-40 mix-blend-luminosity"
            style={{
              backgroundImage: `url('https://lh3.googleusercontent.com/aida-public/AB6AXuDfu4j2eYqBMwaMGtGY8k_jUKyXVmD_CUpDqVHG8fJvcWNA6JUQqLxmMlK4EB5W95LRY__nODtzoMZA6VexfyQdohJxXe0tLFLHA9TUqUq8T-Kwy_hSv5sHuAjgaqwg2hBO8KR1ZLg3RHIA2Rj0Pei37bdDoDdJ9a2NTclxszruoy3ORHIhVv7Qp1fb6QDpNBWHn_kO1vAk2uDDddpRSYMir2Apwb339PAuF6058lQTblAM9LWypGUYzw')`
            }}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-primary via-primary/80 to-transparent" />
        </div>

        <div className="relative z-10 flex flex-col items-center text-center max-w-md">
          <div className="bg-primary-container p-6 rounded-2xl border border-outline-variant/20 mb-stack-gap-lg flex justify-center items-center shadow-2xl">
            <VerifiedUserIcon style={{ fontSize: '64px', fontVariationSettings: "'FILL' 1" }} />
          </div>
          <h1 className="font-display-lg text-display-lg text-on-primary mb-stack-gap-sm tracking-tight">
            Parakh Seva
          </h1>
          <p className="font-body-lg text-body-lg text-primary-fixed-dim max-w-sm">
            AI-Powered Identity & Document Verification
          </p>
        </div>
      </div>

      {/* Right Column: Login Interface */}
      <div className="flex-1 flex flex-col justify-center px-container-padding sm:px-12 lg:px-24 xl:px-32 relative bg-surface">
        <div className="w-full max-w-sm mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 bg-surface-container-highest border border-outline-variant/30 rounded-full mb-stack-gap-lg">
            <LockIcon className="text-secondary font-body-md" style={{ fontSize: '16px', fontVariationSettings: "'FILL' 1" }} />
            <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">
              Secure System
            </span>
          </div>

          <div className="mb-stack-gap-lg">
            <h2 className="font-headline-md text-headline-md text-on-surface mb-unit">Sign In</h2>
            <p className="font-body-md text-body-md text-on-surface-variant">
              Enter your credentials to access the forensic dashboard.
            </p>
          </div>

          <form className="flex flex-col gap-stack-gap-md" onSubmit={handleSubmit}>
            <div>
              <label className="block font-label-md text-label-md text-on-surface mb-unit" htmlFor="username">
                Email or Username
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-outline">
                  <MailIcon />
                </span>
                <input
                  className="block w-full pl-10 pr-3 py-2.5 bg-surface-container-lowest border border-outline-variant rounded-lg font-body-md text-body-md text-on-surface placeholder:text-outline focus:outline-none focus:border-secondary focus:ring-1 focus:ring-secondary/50 transition-shadow shadow-sm"
                  id="username"
                  placeholder="admin@parakhseva.com"
                  required
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="block font-label-md text-label-md text-on-surface mb-unit" htmlFor="password">
                Password
              </label>
              <div className="relative">
                <span className="absolute inset-y-0 left-0 flex items-center pl-3 text-outline">
                  <KeyIcon />
                </span>
                <input
                  className="block w-full pl-10 pr-3 py-2.5 bg-surface-container-lowest border border-outline-variant rounded-lg font-body-md text-body-md text-on-surface placeholder:text-outline focus:outline-none focus:border-secondary focus:ring-1 focus:ring-secondary/50 transition-shadow shadow-sm"
                  id="password"
                  placeholder="••••••••"
                  required
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            <div className="flex items-center justify-between mt-unit mb-stack-gap-sm">
              <label className="flex items-center gap-2 cursor-pointer group">
                <input
                  className="w-4 h-4 rounded border-outline-variant text-secondary focus:ring-secondary/30 focus:ring-offset-0 bg-surface-container-lowest cursor-pointer transition-colors"
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                />
                <span className="font-body-md text-body-md text-on-surface-variant group-hover:text-on-surface transition-colors">
                  Remember me
                </span>
              </label>
              <a className="font-label-md text-label-md text-secondary hover:text-secondary-fixed-variant transition-colors" href="#">
                Forgot password?
              </a>
            </div>

            <button
              className="w-full flex justify-center items-center gap-2 py-3 px-4 bg-primary text-on-primary rounded-lg font-label-md text-label-md hover:bg-inverse-surface transition-all active:scale-[0.98] shadow-sm hover:shadow-md"
              type="submit"
            >
              Sign In
              <ArrowForwardIcon style={{ fontSize: '18px' }} />
            </button>
          </form>

          <div className="mt-stack-gap-lg pt-stack-gap-md border-t border-outline-variant/30 text-center">
            <p className="font-data-mono text-data-mono text-outline flex items-center justify-center gap-1.5 uppercase">
              <GavelIcon style={{ fontSize: '14px' }} />
              Authorized personnel only
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
