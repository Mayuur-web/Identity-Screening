import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import PageLayout from '../../components/PageLayout'
import { UploadFileIcon, DocumentScannerIcon, PsychologyIcon, VerifiedIcon, NoteAddIcon, PhotoCameraIcon, UploadIcon, LockIcon, ArrowForwardIcon, ExpandMoreIcon } from '../../components/Icons'

const API_BASE = '/api'

const steps = [
  { icon: UploadFileIcon, label: 'Upload' },
  { icon: DocumentScannerIcon, label: 'Extract' },
  { icon: PsychologyIcon, label: 'Analyze' },
  { icon: VerifiedIcon, label: 'Result' },
]

const docTypes = [
  { value: '', label: 'Select Document Type', disabled: true },
  { value: 'aadhaar', label: 'Aadhaar' },
  { value: 'pan', label: 'PAN Card' },
  { value: 'passport', label: 'Passport' },
  { value: 'driving_licence', label: 'Driving Licence' },
  { value: 'voter_id', label: 'Voter ID' },
  { value: 'other', label: 'Other' },
]

export default function NewVerification() {
  const navigate = useNavigate()
  const [activeStep, setActiveStep] = useState(0)
  const [docType, setDocType] = useState('')
  const [fileName, setFileName] = useState(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [statusMessage, setStatusMessage] = useState('')
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0]
      setFileName(file.name)
      setSelectedFile(file)
      setError(null)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0]
      setFileName(file.name)
      setSelectedFile(file)
      setError(null)
    }
  }

  const handleStartVerification = async () => {
    if (!selectedFile) {
      setError('Please select a document to upload')
      return
    }

    setIsProcessing(true)
    setError(null)

    try {
      // Step 1: Uploading
      setActiveStep(1)
      setStatusMessage('Uploading document...')

      const formData = new FormData()
      formData.append('file', selectedFile)
      if (docType) {
        formData.append('document_type', docType)
      }

      const analyzeResponse = await fetch(`${API_BASE}/documents/verify`, {
        method: 'POST',
        body: formData,
      })

      if (!analyzeResponse.ok) {
        const errorData = await analyzeResponse.json().catch(() => ({}))
        throw new Error(errorData.detail || `Analysis failed (${analyzeResponse.status})`)
      }

      // Step 2: Extracting fields
      setActiveStep(2)
      setStatusMessage('Running OCR...')
      await new Promise(resolve => setTimeout(resolve, 400))

      setStatusMessage('Extracting identity fields...')

      const result = await analyzeResponse.json()

      // Step 3: Preparing results
      setActiveStep(3)
      setStatusMessage('Preparing analysis...')
      await new Promise(resolve => setTimeout(resolve, 300))

      // Store results in sessionStorage for DocumentAnalysis page
      sessionStorage.setItem('ocrResults', JSON.stringify(result))

      // Navigate to Document Analysis with results
      navigate('/document-analysis')

    } catch (err) {
      console.error('Verification failed:', err)
      setError(err.message || 'Failed to process document. Please try again.')
      setIsProcessing(false)
      setActiveStep(0)
      setStatusMessage('')
    }
  }

  return (
    <PageLayout>
      {/* Page Header */}
      <header className="mb-stack-gap-lg">
        <h1 className="font-display-lg text-display-lg text-on-surface mb-2 tracking-tight">New Identity Verification</h1>
        <p className="font-body-md text-body-md text-on-surface-variant max-w-2xl">
          Upload official documents and biometric data to initiate a high-assurance identity analysis workflow.
        </p>
      </header>

      {/* Workflow Stepper */}
      <div className="relative mb-12 stepper-line">
        <div className="flex justify-between relative z-10">
          {steps.map(({ icon: Icon, label }, i) => (
            <div key={i} className="flex flex-col items-center gap-2 w-1/4">
              <div className={`w-12 h-12 rounded-full flex items-center justify-center shadow-[0_0_0_4px_#f9f9ff] ${
                i <= activeStep
                  ? 'bg-primary text-on-primary'
                  : 'bg-surface-container-highest text-on-surface-variant border border-outline-variant'
              }`}>
                <Icon />
              </div>
              <span className={`font-label-md text-label-md ${i <= activeStep ? 'text-primary' : 'text-on-surface-variant'}`}>
                {label}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Status Message */}
      {isProcessing && (
        <div className="mb-6 p-4 bg-surface-container-low border border-outline-variant rounded-xl flex items-center gap-3">
          <span className="material-symbols-outlined text-secondary animate-spin">progress_activity</span>
          <span className="font-body-md text-body-md text-on-surface">{statusMessage}</span>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="mb-6 p-4 bg-error-container border border-error/30 rounded-xl flex items-center gap-3">
          <span className="material-symbols-outlined text-error">error</span>
          <span className="font-body-md text-body-md text-on-surface">{error}</span>
        </div>
      )}

      {/* Main Upload Form Area */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-stack-gap-lg">
        {/* Document Upload Section */}
        <div className="col-span-12 md:col-span-8 flex flex-col gap-stack-gap-md">
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-container-padding flex-1">
            <div className="flex justify-between items-center mb-stack-gap-md">
              <h2 className="font-headline-sm text-headline-sm text-on-surface">Identity Document</h2>
              <div className="relative w-48">
                <select
                  className="appearance-none w-full bg-surface-bright border border-outline-variant text-on-surface font-body-md text-body-md rounded-lg pl-3 pr-10 py-2 focus:outline-none focus:border-secondary focus:ring-2 focus:ring-secondary/20 cursor-pointer"
                  value={docType}
                  onChange={(e) => setDocType(e.target.value)}
                >
                  {docTypes.map((dt) => (
                    <option key={dt.value} value={dt.value} disabled={dt.disabled}>{dt.label}</option>
                  ))}
                </select>
                <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-on-surface-variant">
                  <ExpandMoreIcon className="text-[20px]" />
                </div>
              </div>
            </div>

            {/* Drag & Drop Zone */}
            <div
              className={`border-2 border-dashed rounded-xl bg-surface-container-low transition-colors duration-200 h-[300px] flex flex-col items-center justify-center text-center p-8 group cursor-pointer ${
                fileName ? 'border-green-500 hover:border-green-600' : 'border-outline-variant hover:border-secondary'
              }`}
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <div className="w-16 h-16 rounded-full bg-surface-container-highest flex items-center justify-center mb-4 text-on-surface-variant group-hover:text-secondary group-hover:bg-secondary/10 transition-colors">
                {fileName ? (
                  <span className="material-symbols-outlined text-[32px] text-green-600">check_circle</span>
                ) : (
                  <NoteAddIcon />
                )}
              </div>
              {fileName ? (
                <>
                  <h3 className="font-headline-sm text-headline-sm text-on-surface mb-1">{fileName}</h3>
                  <p className="font-body-md text-body-md text-on-surface-variant mb-4">File selected. Click to change.</p>
                </>
              ) : (
                <>
                  <h3 className="font-headline-sm text-headline-sm text-on-surface mb-1">Drag and drop your document here</h3>
                  <p className="font-body-md text-body-md text-on-surface-variant mb-6">or click to browse from your computer</p>
                  <div className="flex gap-2">
                    <span className="px-3 py-1 bg-surface-container border border-outline-variant rounded text-label-md font-label-md text-on-surface-variant uppercase">JPG</span>
                    <span className="px-3 py-1 bg-surface-container border border-outline-variant rounded text-label-md font-label-md text-on-surface-variant uppercase">PNG</span>
                    <span className="px-3 py-1 bg-surface-container border border-outline-variant rounded text-label-md font-label-md text-on-surface-variant uppercase">PDF</span>
                  </div>
                </>
              )}
              <input ref={fileInputRef} accept=".jpg,.jpeg,.png,.pdf" className="hidden" type="file" onChange={handleFileChange} />
            </div>
          </div>
        </div>

        {/* Selfie Upload Section */}
        <div className="col-span-12 md:col-span-4 flex flex-col gap-stack-gap-md">
          <div className="bg-surface-container-lowest border border-outline-variant rounded-xl p-container-padding flex-1 flex flex-col">
            <h2 className="font-headline-sm text-headline-sm text-on-surface mb-stack-gap-sm">Liveness Check</h2>
            <p className="font-body-md text-body-md text-on-surface-variant mb-stack-gap-md">
              Provide a live selfie to match against the provided identity document.
            </p>
            <div className="flex-1 border border-outline-variant rounded-xl bg-surface-container-low flex flex-col items-center justify-center p-6 gap-4 relative overflow-hidden">
              <div className="absolute inset-0 opacity-10 pointer-events-none" style={{ backgroundImage: 'radial-gradient(#74777e 1px, transparent 1px)', backgroundSize: '16px 16px' }} />
              <span className="material-symbols-outlined text-[48px] text-on-surface-variant">face</span>
              <div className="w-full flex flex-col gap-2 mt-4 z-10">
                <button className="w-full bg-surface-container-highest hover:bg-surface-dim border border-outline-variant text-on-surface font-label-md text-label-md py-2.5 rounded-lg flex items-center justify-center gap-2 transition-colors">
                  <PhotoCameraIcon className="text-[18px]" />
                  Capture Selfie
                </button>
                <button className="w-full bg-surface-container-lowest hover:bg-surface-bright border border-outline-variant text-on-surface font-label-md text-label-md py-2.5 rounded-lg flex items-center justify-center gap-2 transition-colors">
                  <UploadIcon className="text-[18px]" />
                  Upload File
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Actions & Notice Footer */}
      <div className="mt-stack-gap-lg flex flex-col md:flex-row items-center justify-between gap-stack-gap-md border-t border-outline-variant pt-stack-gap-lg">
        <div className="flex items-center gap-2 text-on-surface-variant">
          <LockIcon className="text-[18px]" />
          <p className="font-data-mono text-data-mono text-xs">
            End-to-end encrypted. Data is processed securely in compliance with regional privacy frameworks.
          </p>
        </div>
        <div className="flex items-center gap-4 w-full md:w-auto">
          <button
            onClick={() => navigate('/dashboard')}
            className="px-6 py-2.5 rounded-lg font-label-md text-label-md text-secondary hover:bg-secondary/10 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleStartVerification}
            disabled={isProcessing || !selectedFile}
            className={`px-6 py-2.5 rounded-lg font-label-md text-label-md flex items-center gap-2 shadow-sm transition-all ${
              isProcessing || !selectedFile
                ? 'bg-surface-container-highest text-on-surface-variant cursor-not-allowed'
                : 'bg-primary text-on-primary hover:bg-primary/90'
            }`}
          >
            {isProcessing ? (
              <>
                <span className="material-symbols-outlined animate-spin text-[18px]">progress_activity</span>
                Processing...
              </>
            ) : (
              <>
                Start AI Verification
                <ArrowForwardIcon className="text-[18px]" />
              </>
            )}
          </button>
        </div>
      </div>
    </PageLayout>
  )
}
