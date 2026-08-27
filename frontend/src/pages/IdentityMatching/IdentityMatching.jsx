import PageLayout from '../../components/PageLayout'
import { IdCardIcon, PhotoCameraIcon, CheckIcon, HighQualityIcon, GroupIcon, HowToRegIcon, ThreeDRotationIcon } from '../../components/Icons'

const biometricStats = [
  { icon: CheckIcon, label: 'Face Detected', value: 'Yes' },
  { icon: HighQualityIcon, label: 'Face Quality', value: 'Good' },
  { icon: GroupIcon, label: 'Face Similarity', value: '92.6%' },
  { icon: HowToRegIcon, label: 'Liveness', value: 'Passed' },
  { icon: ThreeDRotationIcon, label: 'Orientation', value: 'Normal' },
]

const consistencyData = [
  { field: 'Full Name', document: 'JONATHAN DOE', submitted: 'JONATHAN DOE' },
  { field: 'Date of Birth', document: '1985-10-24', submitted: '1985-10-24' },
  { field: 'Document ID', document: 'A89330129B', submitted: 'A89330129B' },
]

export default function IdentityMatching() {
  return (
    <PageLayout>
      <div className="mb-stack-gap-lg">
        <h1 className="font-display-lg text-display-lg text-on-surface">Identity Verification</h1>
        <p className="text-on-surface-variant mt-2">Biometric cross-reference and liveness verification analysis.</p>
      </div>

      {/* Biometric Comparison */}
      <section className="bg-surface-container-lowest border border-outline-variant rounded-xl p-6 mb-stack-gap-lg relative overflow-hidden">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-headline-md text-headline-md text-primary">Biometric Comparison</h2>
          <div className="px-3 py-1 bg-surface-container-high rounded font-label-md text-label-md text-primary flex items-center gap-1 border border-outline-variant">
            <span className="material-symbols-outlined text-[16px]">verified</span>
            Analysis Complete
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-stack-gap-lg relative">
          {/* Document Photo */}
          <div className="flex flex-col border border-outline-variant rounded-lg overflow-hidden bg-background">
            <div className="bg-surface-container-low px-4 py-2 border-b border-outline-variant font-label-md text-label-md text-on-surface-variant flex justify-between items-center">
              <span>Document Photo</span>
              <IdCardIcon />
            </div>
            <div className="aspect-square w-full relative bg-surface-dim">
              <img
                className="w-full h-full object-cover filter grayscale-[20%]"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuAqasKHwP9-D-YjAj67VcLUZ1HPCKcV_Ig2him2GzyVplm5XVL0NCXiQuDEI3foPg0XqlMryGr-wzlxK9SZplDKKoUg3W7Ag6227UNQKMvsdzakcH9gQCdP0_InpVesMcT4YhH1LPV8apUk6X09oBkRCoouWRmGt4bvE8T5QcgjRL2oUG8Ql9punysScLglmAWEEZgy8AkBP1J146JCT9fR5dSCE6NmzB1AA5zaW_ae-hGmMzNyQy2z7A"
                alt="Document Photo"
              />
            </div>
          </div>

          {/* Live Selfie */}
          <div className="flex flex-col border border-outline-variant rounded-lg overflow-hidden bg-background">
            <div className="bg-surface-container-low px-4 py-2 border-b border-outline-variant font-label-md text-label-md text-on-surface-variant flex justify-between items-center">
              <span>Live Selfie</span>
              <PhotoCameraIcon />
            </div>
            <div className="aspect-square w-full relative bg-surface-dim">
              <img
                className="w-full h-full object-cover"
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuDB67GnnwpIXh-SqGj34ID3jq3o9-eT3mGIR4EoXTyF6fL8seM15RELw0Kjjn2R7bXu6pMqLBCsrHS59TeSvfJ_i4f_1oJNRQO-pZUmHsFGFwDogibdLGe34PHQ6H8KGhy65YEvoGXMlXyTRO4iPfWmLr0Z1bag5vBwiWH-5k4nWmZtodJ3q04QEaP_0AOG4l0v6k2TCqy4pnLyd5wzUMtzI_G_jQk380YHf4NfSFfgEJ134gOUVoMf3w"
                alt="Live Selfie"
              />
            </div>
          </div>

          {/* Match Score Circle Overlay */}
          <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 rounded-full bg-surface-container-lowest border border-outline-variant shadow-sm flex flex-col items-center justify-center z-10">
            <svg className="absolute inset-0 w-full h-full -rotate-90 transform" viewBox="0 0 100 100">
              <circle className="stroke-surface-container-high" cx="50" cy="50" fill="none" r="46" strokeWidth="8" />
              <circle className="stroke-primary" cx="50" cy="50" fill="none" r="46" strokeDasharray="289" strokeDashoffset="21" strokeLinecap="round" strokeWidth="8" />
            </svg>
            <div className="font-headline-md text-headline-md text-primary relative z-20 leading-none">92.6%</div>
            <div className="font-label-md text-label-md text-on-surface-variant relative z-20 mt-1 uppercase">Match</div>
          </div>
        </div>
      </section>

      {/* Biometric Stats Grid */}
      <section className="grid grid-cols-2 lg:grid-cols-5 gap-stack-gap-md mb-stack-gap-lg">
        {biometricStats.map(({ icon: Icon, label, value }, i) => (
          <div key={i} className="bg-surface-container-lowest border border-outline-variant rounded-lg p-4 flex flex-col">
            <span className="font-label-md text-label-md text-on-surface-variant mb-2">{label}</span>
            <div className="flex items-center gap-2 mt-auto">
              <Icon />
              <span className="font-body-lg text-body-lg text-primary font-medium">{value}</span>
            </div>
          </div>
        ))}
      </section>

      {/* Identity Consistency Table */}
      <section className="bg-surface-container-lowest border border-outline-variant rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-outline-variant flex justify-between items-center bg-background">
          <h3 className="font-headline-sm text-headline-sm text-primary">Identity Consistency</h3>
          <span className="font-data-mono text-data-mono text-on-surface-variant">ID: VER-8839-44A</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead className="bg-surface-container-low text-on-surface-variant font-label-md text-label-md">
              <tr>
                <th className="px-6 py-3 font-semibold border-b border-outline-variant">Field</th>
                <th className="px-6 py-3 font-semibold border-b border-outline-variant">Document Data</th>
                <th className="px-6 py-3 font-semibold border-b border-outline-variant">Submitted Data</th>
                <th className="px-6 py-3 font-semibold border-b border-outline-variant text-right">Result</th>
              </tr>
            </thead>
            <tbody className="font-body-md text-body-md text-on-surface divide-y divide-outline-variant">
              {consistencyData.map(({ field, document, submitted }, i) => (
                <tr key={i} className="hover:bg-surface-bright transition-colors">
                  <td className="px-6 py-4 font-medium">{field}</td>
                  <td className="px-6 py-4 font-data-mono text-data-mono text-on-surface-variant">{document}</td>
                  <td className="px-6 py-4 font-data-mono text-data-mono text-on-surface-variant">{submitted}</td>
                  <td className="px-6 py-4 text-right">
                    <div className="inline-flex items-center gap-1 px-2 py-1 bg-surface-container-high rounded border border-outline-variant">
                      <CheckIcon className="text-[16px] text-primary" />
                      <span className="font-label-md text-label-md text-primary">Match</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </PageLayout>
  )
}
