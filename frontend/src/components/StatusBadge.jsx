export default function StatusBadge({ status }) {
  const config = {
    verified: {
      className: 'bg-[#dcfce7] text-[#166534]',
      label: 'Verified',
    },
    flagged: {
      className: 'bg-[#fef3c7] text-[#92400e]',
      label: 'Flagged',
    },
    suspicious: {
      className: 'bg-[#fef3c7] text-[#92400e]',
      label: 'Suspicious',
    },
    rejected: {
      className: 'bg-[#fee2e2] text-[#991b1b]',
      label: 'Rejected',
    },
    highRisk: {
      className: 'bg-[#fee2e2] text-[#991b1b]',
      label: 'High Risk',
    },
    review: {
      className: 'bg-surface-container-highest text-primary border border-outline-variant',
      label: 'Review',
      icon: true,
    },
  }

  const { className, label, icon } = config[status] || config.verified

  return (
    <span className={`px-2 py-1 rounded font-label-md text-[11px] uppercase tracking-wide inline-flex items-center gap-1 ${className}`}>
      {icon && <span className="material-symbols-outlined text-[14px]">psychology</span>}
      {label}
    </span>
  )
}
