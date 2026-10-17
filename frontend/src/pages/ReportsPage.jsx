import { useEffect, useState } from 'react'
import { ArrowRight, FileText, Search } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api } from '../api'

const labelize = (value = '') => value.replaceAll('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())

export default function ReportsPage() {
  const [reports, setReports] = useState([])
  const [query, setQuery] = useState('')
  const [error, setError] = useState('')
  useEffect(() => { api.reports().then(setReports).catch((err) => setError(err.message)) }, [])
  const filtered = reports.filter((item) => `${item.type} ${item.location} ${item.severity}`.toLowerCase().includes(query.toLowerCase()))
  return (
    <div className="reports-page">
      <div className="page-heading"><div><span className="eyebrow">Session history</span><h1>Incident reports</h1><p>Clean, timestamped records. Clear a session from the console when it is no longer needed.</p></div><label className="search-box"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search reports" /></label></div>
      {error && <p className="error-banner">{error}</p>}
      {!filtered.length ? (
        <div className="reports-empty"><span className="empty-icon"><FileText size={27} /></span><h2>No reports yet</h2><p>Run a demo scenario and its report will appear here.</p><Link className="button primary" to="/console?autostart=1">Run the demo <ArrowRight size={17} /></Link></div>
      ) : (
        <div className="reports-list">
          <div className="report-table-head"><span>Incident</span><span>Location</span><span>Started</span><span>Status</span><span /></div>
          {filtered.map((report) => (
            <Link to={`/reports/${report.session_id}`} className="report-row" key={report.session_id}>
              <span><i className={`severity-dot severity-${report.severity}`} /><strong>{labelize(report.type)}</strong><small>{report.demo_mode ? 'Simulated' : 'Stand-in contacts'}</small></span>
              <span>{report.location || 'Location not captured'}</span>
              <span>{new Date(report.started_at).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</span>
              <span><b className={`report-status ${report.status}`}>{labelize(report.status)}</b></span>
              <ArrowRight size={17} />
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

