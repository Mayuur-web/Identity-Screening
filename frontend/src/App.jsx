import { Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login/Login'
import Dashboard from './pages/Dashboard/Dashboard'
import NewVerification from './pages/NewVerification/NewVerification'
import DocumentAnalysis from './pages/DocumentAnalysis/DocumentAnalysis'
import IdentityMatching from './pages/IdentityMatching/IdentityMatching'
import RiskReport from './pages/RiskReport/RiskReport'
import VerificationHistory from './pages/VerificationHistory/VerificationHistory'
import Settings from './pages/Settings/Settings'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/new-verification" element={<NewVerification />} />
      <Route path="/document-analysis" element={<DocumentAnalysis />} />
      <Route path="/identity-matching" element={<IdentityMatching />} />
      <Route path="/risk-report" element={<RiskReport />} />
      <Route path="/verification-history" element={<VerificationHistory />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
