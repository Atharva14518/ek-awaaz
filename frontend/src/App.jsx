import { useEffect, useState } from 'react'
import { Link, NavLink, Route, Routes } from 'react-router-dom'
import { Headphones, Languages, ShieldCheck } from 'lucide-react'
import { api } from './api'
import HomePage from './pages/HomePage'
import LiveConsole from './pages/LiveConsole'
import ReportsPage from './pages/ReportsPage'
import ReportDetail from './pages/ReportDetail'

export default function App() {
  const [config, setConfig] = useState({ demo_mode: true, real_actions_enabled: false })
  const [language, setLanguage] = useState(() => localStorage.getItem('ek-language') || 'EN')

  useEffect(() => {
    api.config().then(setConfig).catch(() => {})
  }, [])

  const toggleLanguage = () => {
    const next = language === 'EN' ? 'हिं' : 'EN'
    setLanguage(next)
    localStorage.setItem('ek-language', next)
  }

  return (
    <div className="app-shell">
      <div className="demo-banner" role="status">
        <ShieldCheck size={15} aria-hidden="true" />
        <span><strong>{config.live_call_ready ? 'CONTROLLED LIVE MODE' : 'DEMO MODE'}</strong> · Calls go to configured test numbers only</span>
        <span className="banner-status">{config.live_dispatch_enabled ? 'Live intake + stand-in dispatch' : config.live_call_ready ? 'Live intake · simulated dispatch' : 'No real actions'}</span>
      </div>
      <header className="topbar">
        <Link className="brand" to="/" aria-label="Ek Awaaz home">
          <span className="brand-mark"><Headphones size={20} /></span>
          <span>Ek Awaaz<small>एक आवाज़</small></span>
        </Link>
        <nav aria-label="Main navigation">
          <NavLink to="/" end>Home</NavLink>
          <NavLink to="/console">Live Console</NavLink>
          <NavLink to="/reports">Reports</NavLink>
        </nav>
        <button className="language-button" onClick={toggleLanguage} aria-label="Toggle Hindi and English">
          <Languages size={17} /> {language}
        </button>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<HomePage config={config} language={language} />} />
          <Route path="/console" element={<LiveConsole config={config} />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/reports/:sessionId" element={<ReportDetail />} />
        </Routes>
      </main>
      <footer className="site-footer">
        <span>Built to help people stay heard under pressure.</span>
        <span>Session-only data · Test contacts only</span>
      </footer>
    </div>
  )
}
