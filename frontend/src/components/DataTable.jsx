export default function DataTable({ columns, children }) {
  return (
    <div className="bg-surface-container-lowest border border-outline-variant rounded-lg shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse min-w-[900px]">
          <thead>
            <tr className="bg-[#F8FAFC] border-b border-outline-variant font-label-md text-label-md text-on-surface-variant uppercase tracking-wider">
              {columns.map((col, i) => (
                <th key={i} className={`px-4 py-3 font-semibold ${col.align === 'center' ? 'text-center' : ''} ${col.align === 'right' ? 'text-right' : ''}`}>
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="font-body-md text-body-md text-on-surface divide-y divide-outline-variant divide-opacity-40">
            {children}
          </tbody>
        </table>
      </div>
    </div>
  )
}
