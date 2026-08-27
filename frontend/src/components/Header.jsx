import { SearchIcon, NotificationsIcon, AccountCircleIcon } from './Icons'

export default function Header({ showSearch = false }) {
  return (
    <nav className="fixed top-0 right-0 w-full md:w-[calc(100%-16rem)] h-16 bg-surface border-b border-outline-variant flex justify-between items-center px-container-padding z-40">
      <div className="flex items-center gap-4 md:hidden">
        <button className="text-on-surface-variant hover:text-primary transition-opacity duration-150 hover:opacity-80">
          <span className="material-symbols-outlined">menu</span>
        </button>
      </div>

      <div className="flex-1 flex justify-end items-center gap-6">
        {showSearch && (
          <div className="relative w-64 hidden md:block">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-lg">search</span>
            <input
              className="w-full pl-10 pr-4 py-2 bg-surface-container-highest border border-outline-variant rounded-lg text-body-md text-on-surface focus:outline-none focus:border-secondary focus:ring-1 focus:ring-secondary transition-all"
              placeholder="Search verifications..."
              type="text"
            />
          </div>
        )}
        <div className="flex items-center gap-4">
          <a className="text-on-surface-variant hover:text-primary cursor-pointer transition-opacity duration-150 hover:opacity-80 font-body-md text-body-md hidden lg:block" href="#">System Status</a>
          <button className="text-on-surface-variant hover:text-primary transition-colors p-2 rounded-full hover:bg-surface-container-high">
            <NotificationsIcon />
          </button>
          <div className="w-8 h-8 rounded-full overflow-hidden border border-outline-variant cursor-pointer flex items-center justify-center bg-surface-container-highest">
            <AccountCircleIcon />
          </div>
        </div>
      </div>
    </nav>
  )
}
