import { useEffect, useState } from 'react'
import { ArrowLeft, Check, Download, MapPin, Printer } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api'
import HighlightText from '../components/HighlightText'

const labelize = (value = '') => value.replaceAll('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())

export default function ReportDetail() {
  const { sessionId } = useParams()
  const [session, setSession] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { api.report(sessionId).then(setSession).catch((err) => setError(err.message)) }, [sessionId])
  if (error) return <div className="loading-page"><p>{error}</p><Link to="/reports">Back to reports</Link></div>
  if (!session) return <div className="loading-page">Preparing report…</div>
  const incident = session.incident
  return (
    <div className="report-detail">
      <div className="report-actions no-print"><Link to="/reports" className="back-link"><ArrowLeft size={17} /> All reports</Link><div><button className="small-button" onClick={() => window.print()}><Printer size={16} /> Print</button><a className="button primary compact" href={api.pdfUrl(sessionId)}><Download size={16} /> Export PDF</a></div></div>
      <article className="print-report">
        <header className="report-header"><div><span className="eyebrow">Ek Awaaz</span><h1>Incident report</h1><p>Session {sessionId.slice(0, 8).toUpperCase()}</p></div><div className="report-seal"><Check size={20} /><span>{session.status === 'complete' ? 'Complete' : labelize(session.status)}</span></div></header>
        <div className="report-warning">DEMO MODE · Test contacts only · Session-only data</div>
        <section className="report-facts">
          <div><span>What happened</span><strong>{labelize(incident.type)}</strong></div><div><span>Severity</span><strong>{labelize(incident.severity)}</strong></div>
          <div className="wide"><span>Location</span><strong><MapPin size={16} />{incident.location.text || 'Not captured'}</strong><small>{incident.location.landmarks?.join(' · ')}</small></div>
          <div><span>People involved</span><strong>{incident.people.count || 'Unknown'}</strong></div><div><span>Injured</span><strong>{incident.people.injured || 'Unknown'}</strong></div>
          <div><span>Caller safe</span><strong>{labelize(incident.caller_safe)}</strong></div><div><span>Language</span><strong>{incident.language_detected.toUpperCase()}</strong></div>
        </section>
        <section className="report-section"><div className="report-section-title"><span>01</span><h2>Timeline</h2></div><div className="report-timeline">
          {(incident.actions || []).length ? incident.actions.map((action) => <div key={action.id}><time>{new Date(action.ts).toLocaleTimeString()}</time><i className={action.status} /><p><strong>{action.target}</strong><span>{action.script_summary}</span></p><b>{labelize(action.status)}</b></div>) : <p>No contact actions recorded.</p>}
        </div></section>
        <section className="report-section"><div className="report-section-title"><span>02</span><h2>Transcript</h2></div><div className="report-transcript">
          {incident.transcript.map((item, index) => <div key={`${item.ts}-${index}`} className={item.speaker}><span>{item.speaker === 'caller' ? 'Caller' : 'Listener'}<time>{new Date(item.ts).toLocaleTimeString()}</time></span><p><HighlightText item={item} /></p></div>)}
        </div></section>
        <footer className="report-footer"><span>Created {new Date().toLocaleString()}</span><span>Ek Awaaz · One voice, many hands</span></footer>
      </article>
    </div>
  )
}

