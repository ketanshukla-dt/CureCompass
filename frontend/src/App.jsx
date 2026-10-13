import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { Activity, History, Zap, Shield } from 'lucide-react'
import Dashboard from './pages/Dashboard.jsx'
import IncidentDetail from './pages/IncidentDetail.jsx'
import HistoryPage from './pages/History.jsx'

function Sidebar() {
  const navItems = [
    { to: '/', icon: Activity, label: 'Incidents', exact: true },
    { to: '/history', icon: History, label: 'History' },
  ]

  return (
    <aside className="w-56 bg-dt-dark border-r border-dt-border flex flex-col shrink-0">
      {/* Logo */}
      <div className="p-5 border-b border-dt-border">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-dt-blue flex items-center justify-center">
            <Zap size={16} className="text-white" />
          </div>
          <div>
            <div className="text-white font-bold text-sm leading-tight">CureCompass</div>
            <div className="text-dt-text/50 text-xs">by Dynatrace</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1">
        {navItems.map(({ to, icon: Icon, label, exact }) => (
          <NavLink
            key={to}
            to={to}
            end={exact}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-dt-blue/20 text-dt-blue font-semibold border border-dt-blue/30'
                  : 'text-dt-text/70 hover:text-white hover:bg-white/5'
              }`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-dt-border">
        <div className="flex items-center gap-2 text-xs text-dt-text/40">
          <Shield size={12} />
          <span>AI-powered by Claude</span>
        </div>
        <div className="text-xs text-dt-text/30 mt-1">Davis AI · Anthropic</div>
      </div>
    </aside>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/incidents/:id" element={<IncidentDetail />} />
            <Route path="/history" element={<HistoryPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
