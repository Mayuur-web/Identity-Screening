import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import PageLayout from '../../components/PageLayout'
import RiskGauge from '../../components/RiskGauge'
import { ZoomInIcon, ZoomOutIcon, FitScreenIcon, CheckCircleIcon, WarningIcon, DocumentScannerIcon, ArrowForwardIcon } from '../../components/Icons'

const integrityChecks = [
  { label: 'Structure', status: 'not_implemented' },
  { label: 'Text Consistency', status: 'not_implemented' },
  { label: 'Metadata', status: 'not_implemented' },
  { label: 'Req. Fields', status: 'not_implemented' },
]

// Field configurations per document type
const passportFieldGroups = [
  {
    title: 'Identity',
    fields: [
      { key: 'surname', label: 'Surname', icon: 'badge' },
      { key: 'given_names', label: 'Given Names', icon: 'badge' },
      { key: 'date_of_birth', label: 'Date of Birth', icon: 'cake' },
      { key: 'gender', label: 'Gender / Sex', icon: 'wc' },
      { key: 'nationality', label: 'Nationality', icon: 'flag' },
    ],
  },
  {
    title: 'Document',
    fields: [
      { key: 'document_number', label: 'Passport Number', icon: 'badge' },
      { key: 'document_type', label: 'Document Type', icon: 'description' },
    ],
  },
  {
    title: 'Location & Dates',
    fields: [
      { key: 'place_of_birth', label: 'Place of Birth', icon: 'location_on' },
      { key: 'place_of_issue', label: 'Place of Issue', icon: 'location_on' },
      { key: 'date_of_issue', label: 'Date of Issue', icon: 'event' },
      { key: 'date_of_expiry', label: 'Date of Expiry', icon: 'event_busy' },
    ],
  },
]

const aadhaarFieldGroups = [
  {
    title: 'Identity',
    fields: [
      { key: 'full_name', label: 'Full Name', icon: 'person' },
      { key: 'date_of_birth', label: 'Date of Birth', icon: 'cake' },
      { key: 'gender', label: 'Gender / Sex', icon: 'wc' },
    ],
  },
  {
    title: 'Document',
    fields: [
      { key: 'document_number', label: 'Aadhaar Number', icon: 'badge' },
      { key: 'document_type', label: 'Document Type', icon: 'description' },
      { key: 'father_name', label: "Father's Name", icon: 'family_restroom' },
    ],
  },
  {
    title: 'Address',
    fields: [
      { key: 'address', label: 'Address', icon: 'location_on' },
    ],
  },
]

function FaceVerificationResult({ data }) {
  const { status, similarity_score, message } = data

  const statusConfig = {
    MATCH: {
      color: 'bg-emerald-50 border-emerald-200',
      textColor: 'text-emerald-800',
      icon: 'check_circle',
      iconColor: 'text-emerald-500',
      label: 'Face Match',
    },
    NO_MATCH: {
      color: 'bg-red-50 border-red-200',
      textColor: 'text-red-800',
      icon: 'cancel',
      iconColor: 'text-red-500',
      label: 'Face Match',
    },
    NO_FACE: {
      color: 'bg-red-50 border-red-200',
      textColor: 'text-red-800',
      icon: 'error',
      iconColor: 'text-red-500',
      label: 'Face Match',
    },
    NOT_PROVIDED: {
      color: 'bg-surface-container-low border-outline-variant',
      textColor: 'text-on-surface-variant',
      icon: 'info',
      iconColor: 'text-on-surface-variant',
      label: 'Face Match',
    },
  }

  const config = statusConfig[status] || statusConfig.NOT_PROVIDED

  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-gutter">
      <div className="flex items-center justify-between">
        <h3 className="font-headline-sm text-headline-sm text-primary flex items-center gap-2">
          <span className="material-symbols-outlined text-secondary">face</span>
          Face Match
        </h3>
        <div className="flex items-center gap-3">
          {similarity_score != null && (
            <div className="text-right">
              <div className="font-data-mono text-data-mono text-2xl font-bold text-primary">{similarity_score}%</div>
              <div className="text-on-surface-variant text-[10px] uppercase tracking-wider">Similarity</div>
            </div>
          )}
          <div className={`px-3 py-1.5 rounded-lg border ${config.color} flex items-center gap-1.5`}>
            <span className={`material-symbols-outlined text-[18px] ${config.iconColor}`}>{config.icon}</span>
            <span className={`font-label-md text-label-md font-semibold ${config.textColor}`}>{config.label}</span>
          </div>
        </div>
      </div>
      {status === 'NOT_PROVIDED' ? (
        <p className="mt-3 font-body-md text-body-md text-on-surface-variant">Not checked — selfie not provided</p>
      ) : message ? (
        <p className="mt-3 font-body-md text-body-md text-on-surface-variant">{message}</p>
      ) : null}
    </div>
  )
}

function VerificationResults({ data }) {
  const status = data.status
  const score = data.score
  const checks = data.checks || []
  const reasons = data.reasons || []

  const statusConfig = {
    VERIFIED: {
      color: 'bg-emerald-50 border-emerald-200',
      textColor: 'text-emerald-800',
      icon: 'check_circle',
      iconColor: 'text-emerald-500',
      label: 'VERIFIED',
    },
    MANUAL_REVIEW: {
      color: 'bg-amber-50 border-amber-200',
      textColor: 'text-amber-800',
      icon: 'warning',
      iconColor: 'text-amber-500',
      label: 'MANUAL REVIEW',
    },
    REJECTED: {
      color: 'bg-red-50 border-red-200',
      textColor: 'text-red-800',
      icon: 'cancel',
      iconColor: 'text-red-500',
      label: 'REJECTED',
    },
  }

  const config = statusConfig[status] || statusConfig.MANUAL_REVIEW

  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-gutter">
      {/* Status and Score Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-headline-sm text-headline-sm text-primary flex items-center gap-2">
          <span className="material-symbols-outlined text-secondary">verified_user</span>
          Verification Result
        </h3>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <div className="font-data-mono text-data-mono text-2xl font-bold text-primary">{score}</div>
            <div className="text-on-surface-variant text-[10px] uppercase tracking-wider">Score</div>
          </div>
          <div className={`px-3 py-1.5 rounded-lg border ${config.color} flex items-center gap-1.5`}>
            <span className={`material-symbols-outlined text-[18px] ${config.iconColor}`}>{config.icon}</span>
            <span className={`font-label-md text-label-md font-semibold ${config.textColor}`}>{config.label}</span>
          </div>
        </div>
      </div>

      {/* Reasons */}
      {reasons.length > 0 && (
        <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <div className="flex items-center gap-2 mb-1">
            <span className="material-symbols-outlined text-[16px] text-amber-600">info</span>
            <span className="font-label-md text-label-md text-amber-800 font-semibold">Reasons</span>
          </div>
          <ul className="list-disc list-inside text-sm text-amber-700">
            {reasons.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Checks */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {checks.map((check, i) => (
          <div key={i} className="flex items-start gap-2 p-2 rounded-lg bg-surface">
            <span className={`material-symbols-outlined text-[18px] mt-0.5 ${
              check.status === 'passed' ? 'text-emerald-500' :
              check.status === 'warning' ? 'text-amber-500' :
              'text-red-500'
            }`}> 
              {check.status === 'passed' ? 'check_circle' :
               check.status === 'warning' ? 'warning' : 'cancel'}
            </span>
            <div className="flex-1 min-w-0">
              <div className="font-label-md text-label-md text-on-surface font-medium">{check.name}</div>
              <div className="text-on-surface-variant text-xs truncate">{check.message}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function DocumentAnalysis() {
  const navigate = useNavigate()
  const [analysisData, setAnalysisData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showRawOcr, setShowRawOcr] = useState(false)

  useEffect(() => {
    const stored = sessionStorage.getItem('ocrResults')
    if (stored) {
      try {
        setAnalysisData(JSON.parse(stored))
      } catch (e) {
        setError('Failed to parse analysis results')
      }
    } else {
      setError('No analysis results available. Please run a verification first.')
    }
    setLoading(false)
  }, [])

  const ocrData = analysisData?.ocr
  const fields = analysisData?.fields
  const mrz = analysisData?.mrz
  const averageConfidence = ocrData?.average_confidence
  const averageConfidencePercent = averageConfidence != null ? Math.round(averageConfidence * 100) : null
  const preprocessing = ocrData?.preprocessing_applied || []
  const passesRun = ocrData?.passes_run || 1

  return (
    <PageLayout>
      <div className="max-w-[1200px] mx-auto w-full">
        {/* Page Header */}
        <div className="mb-stack-gap-lg flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
          <div>
            <h1 className="font-display-lg text-display-lg text-primary mb-2">Document Analysis</h1>
            <p className="text-on-surface-variant">OCR extraction, identity field analysis, and MRZ detection results.</p>
          </div>
          <div className="flex items-center gap-2 text-label-md font-label-md bg-surface-container-low px-3 py-1 rounded-full border border-outline-variant">
            <span className={`w-2 h-2 rounded-full ${analysisData?.success ? 'bg-green-500' : 'bg-red-500'}`}></span>
            <span className="text-on-surface-variant uppercase tracking-wider">
              {analysisData?.success ? 'Analysis Complete' : 'Analysis Failed'}
            </span>
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <span className="material-symbols-outlined text-4xl text-secondary animate-spin mr-3">progress_activity</span>
            <span className="font-body-lg text-body-lg text-on-surface-variant">Loading analysis results...</span>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="p-6 bg-error-container border border-error/30 rounded-xl mb-6">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-error">error</span>
              <span className="font-body-md text-body-md text-on-surface">{error}</span>
            </div>
            <button onClick={() => navigate('/new-verification')} className="mt-4 px-4 py-2 bg-primary text-on-primary rounded-lg font-label-md text-label-md hover:bg-primary/90 transition-colors">
              Start New Verification
            </button>
          </div>
        )}

        {/* Results Content */}
        {!loading && !error && analysisData && (
          <>
            {/* OCR Quality Summary Bar */}
            <div className="mb-6 grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-3">
                <span className="font-label-md text-label-md text-on-surface-variant uppercase">Preprocessing</span>
                <div className="mt-1 font-data-mono text-data-mono text-primary text-sm">{preprocessing.length > 0 ? preprocessing.join(', ') : 'none'}</div>
              </div>
              <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-3">
                <span className="font-label-md text-label-md text-on-surface-variant uppercase">OCR Passes</span>
                <div className="mt-1 font-data-mono text-data-mono text-primary text-sm">{passesRun}</div>
              </div>
              <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-3">
                <span className="font-label-md text-label-md text-on-surface-variant uppercase">Lines Detected</span>
                <div className="mt-1 font-data-mono text-data-mono text-primary text-sm">{ocrData?.lines_count || 0}</div>
              </div>
              <div className="bg-surface-container-lowest border border-outline-variant rounded-lg p-3">
                <span className="font-label-md text-label-md text-on-surface-variant uppercase">Avg Confidence</span>
                <div className={`mt-1 font-data-mono text-data-mono text-sm font-bold ${
                  averageConfidencePercent >= 90 ? 'text-emerald-600' :
                  averageConfidencePercent >= 70 ? 'text-amber-600' : 'text-red-600'
                }`}>
                  {averageConfidencePercent != null ? `${averageConfidencePercent}%` : 'N/A'}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-stack-gap-lg">
              {/* Left Column: Document Preview & Raw OCR */}
              <div className="lg:col-span-7 bg-surface-container-lowest border border-outline-variant rounded-xl p-gutter flex flex-col">
                <div className="flex justify-between items-center mb-4 border-b border-outline-variant pb-2">
                  <h3 className="font-headline-sm text-headline-sm text-primary">Document Preview</h3>
                  <div className="flex gap-2">
                    <button className="p-1 rounded hover:bg-surface-container text-on-surface-variant"><ZoomInIcon /></button>
                    <button className="p-1 rounded hover:bg-surface-container text-on-surface-variant"><ZoomOutIcon /></button>
                    <button className="p-1 rounded hover:bg-surface-container text-on-surface-variant"><FitScreenIcon /></button>
                  </div>
                </div>
                <div className="relative bg-surface-container-low rounded-lg border border-outline-variant flex-grow overflow-hidden min-h-[500px] flex flex-col">
                  {/* MRZ Section */}
                  {mrz?.detected && (
                    <div className="p-4 border-b border-outline-variant bg-surface-container">
                      <h4 className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider mb-2 flex items-center gap-2">
                        <span className="material-symbols-outlined text-[16px] text-secondary">qr_code</span>
                        MRZ Detected
                      </h4>
                      <div className="font-data-mono text-data-mono text-sm bg-primary-container text-primary-fixed p-3 rounded-lg whitespace-pre overflow-x-auto">
                        <div>{mrz.line1}</div>
                        <div>{mrz.line2}</div>
                      </div>
                      <div className="mt-2 text-xs text-on-surface-variant">
                        Confidence: {mrz.confidence != null ? `${Math.round(mrz.confidence * 100)}%` : 'N/A'}
                      </div>
                    </div>
                  )}

                  {/* Raw OCR Toggle */}
                  <div className="p-4 flex-1 overflow-auto">
                    <button
                      onClick={() => setShowRawOcr(!showRawOcr)}
                      className="font-label-md text-label-md text-secondary hover:underline flex items-center gap-1 mb-3"
                    >
                      <span className="material-symbols-outlined text-[16px]">{showRawOcr ? 'expand_less' : 'expand_more'}</span>
                      {showRawOcr ? 'Hide' : 'Show'} Raw OCR Results
                    </button>
                    {showRawOcr && (
                      <pre className="font-data-mono text-data-mono text-on-surface whitespace-pre-wrap text-sm leading-relaxed">
                        {ocrData?.full_text || 'No text extracted'}
                      </pre>
                    )}
                    {!showRawOcr && (
                      <div className="text-on-surface-variant text-sm italic">Click above to inspect raw OCR output</div>
                    )}
                  </div>
                </div>
              </div>

              {/* Right Column: Structured Fields */}
              <div className="lg:col-span-5 flex flex-col gap-stack-gap-lg">
                {(fields?.document_type === 'passport' ? passportFieldGroups : aadhaarFieldGroups).map((group) => (
                  <div key={group.title} className="bg-surface-container-lowest border border-outline-variant rounded-xl p-gutter">
                    <h3 className="font-headline-sm text-headline-sm text-primary mb-4 flex items-center gap-2">
                      <DocumentScannerIcon className="text-secondary" />
                      {group.title}
                    </h3>
                    <div className="flex flex-col gap-3">
                      {group.fields.map(({ key, label, icon }) => {
                        const value = fields?.[key]
                        const confidence = fields?.field_confidence?.[key]
                        const status = fields?.field_status?.[key]
                        const confidencePercent = confidence != null ? Math.round(confidence * 100) : null
                        const isExtracted = value != null && value !== ''
                        const isConflict = status === 'conflict'
                        const isConsistent = status === 'consistent'

                        return (
                          <div key={key} className={`flex items-start gap-3 p-3 rounded-lg border ${
                            isConflict ? 'bg-red-50 border-red-200' :
                            isExtracted ? 'bg-surface border-outline-variant/50' : 'bg-surface-container-low border-outline-variant/30'
                          }`}>
                            <span className={`material-symbols-outlined text-[20px] mt-0.5 ${
                              isConflict ? 'text-red-500' : isExtracted ? 'text-secondary' : 'text-outline'
                            }`}>{icon}</span>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between gap-2">
                                <span className="font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">{label}</span>
                                {isConflict ? (
                                  <span className="flex items-center gap-1 text-red-600 shrink-0">
                                    <WarningIcon className="text-[14px]" />
                                    <span className="font-label-md text-[11px]">Conflict — Manual Review</span>
                                  </span>
                                ) : isConsistent ? (
                                  <span className="flex items-center gap-1 text-emerald-600 shrink-0">
                                    <CheckCircleIcon className="text-[14px]" />
                                    <span className="font-label-md text-[11px]">Consistent (OCR + MRZ)</span>
                                  </span>
                                ) : isExtracted ? (
                                  <span className="flex items-center gap-1 text-emerald-600 shrink-0">
                                    <CheckCircleIcon className="text-[14px]" />
                                    <span className="font-label-md text-[11px]">Extracted</span>
                                  </span>
                                ) : (
                                  <span className="flex items-center gap-1 text-amber-600 shrink-0">
                                    <WarningIcon className="text-[14px]" />
                                    <span className="font-label-md text-[11px]">Not detected</span>
                                  </span>
                                )}
                              </div>
                              <div className="mt-1">
                                {isExtracted ? (
                                  <span className={`font-data-mono text-data-mono font-bold ${isConflict ? 'text-red-600' : 'text-primary'}`}>{value}</span>
                                ) : (
                                  <span className="font-data-mono text-data-mono text-outline">—</span>
                                )}
                              </div>
                              {confidencePercent != null && (
                                <div className="mt-1">
                                  <span className={`font-data-mono text-[11px] ${
                                    confidencePercent >= 90 ? 'text-emerald-600' :
                                    confidencePercent >= 70 ? 'text-amber-600' : 'text-red-600'
                                  }`}>
                                    {confidencePercent}% confidence
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ))}

                {/* Face Verification Results */}
                {analysisData?.face_verification && (
                  <FaceVerificationResult data={analysisData.face_verification} />
                )}

                {/* Verification Results */}
                {analysisData?.status && (
                  <VerificationResults data={analysisData} />
                )}

                {/* OCR Confidence Gauge */}
                <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-gutter flex-grow flex flex-col justify-between">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="font-headline-sm text-headline-sm text-primary">OCR Confidence</h3>
                    {averageConfidencePercent != null && (
                      <div className={`px-2 py-1 rounded font-label-md text-[10px] uppercase tracking-wider border ${
                        averageConfidencePercent >= 90 ? 'bg-green-100 text-green-800 border-green-200' :
                        averageConfidencePercent >= 70 ? 'bg-amber-100 text-amber-800 border-amber-200' :
                        'bg-red-100 text-red-800 border-red-200'
                      }`}>
                        {averageConfidencePercent >= 90 ? 'High' : averageConfidencePercent >= 70 ? 'Medium' : 'Low'} Confidence
                      </div>
                    )}
                  </div>
                  <div className="flex items-center justify-center py-4">
                    <RiskGauge score={averageConfidencePercent || 0} size={128} />
                  </div>
                  <button
                    onClick={() => navigate('/risk-report')}
                    className="w-full py-3 bg-primary text-on-primary rounded-lg font-label-md text-label-md hover:bg-primary-container transition-colors mt-4 flex items-center justify-center gap-2"
                  >
                    View Detailed Analysis
                    <ArrowForwardIcon className="text-[16px]" />
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </PageLayout>
  )
}
