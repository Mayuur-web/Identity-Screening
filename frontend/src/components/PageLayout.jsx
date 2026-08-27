import Sidebar from './Sidebar'
import Header from './Header'

export default function PageLayout({ children, showSearch = false }) {
  return (
    <div className="min-h-screen bg-surface">
      <Sidebar />
      <Header showSearch={showSearch} />
      <main className="ml-0 md:ml-64 pt-16 min-h-screen bg-background">
        <div className="p-container-padding max-w-7xl mx-auto">
          {children}
        </div>
      </main>
    </div>
  )
}
