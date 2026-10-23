import { AlertTriangle, Check, ChevronRight, CircleStop, Headphones, MapPin, Navigation, PhoneCall, Play, Radio, RotateCcw, ShieldAlert, Video, Volume2 } from 'lucide-react'
import HighlightText from '../components/HighlightText'
import StatusIcon from '../components/StatusIcon'
import SessionTimer from '../components/SessionTimer'
import FirstVisitTour from '../components/FirstVisitTour'
import MotionIncidentFlow from '../components/MotionIncidentFlow'
import useLiveSession from '../hooks/useLiveSession'
import { api } from '../api'

const labelize = (value = '') => value.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())

function TranscriptPanel({ transcript }) {
  return (
    <section className="console-card transcript-card">
      <div className="card-heading">
        <div><span className="eyebrow">What is being said</span><h2>Live transcript</h2></div>
        <span className="listening"><i /> Listening</span>
      </div>
      <div className="legend" aria-label="Transcript highlight legend">
        {['Location', 'Injury', 'People', 'Hazard'].map((item) => <span key={item} className={`legend-${item.toLowerCase()}`}><i />{item}</span>)}
      </div>
      <div className="transcript" aria-live="polite" aria-relevant="additions text">
        {!transcript.length && (
          <div className="empty-panel"><span className="empty-icon"><Volume2 size={24} /></span><h3>No active call</h3><p>Dial the demo number, or run the scenario below.</p></div>
        )}
        {transcript.map((item, index) => (
          <div className={`bubble-row ${item.speaker}`} key={`${item.ts}-${index}`}>
            <span className="speaker-label">{item.speaker === 'caller' ? 'Caller' : 'Listener'} · {new Date(item.ts).toLocaleTimeString([], { minute: '2-digit', second: '2-digit' })}</span>
            <div className="bubble"><HighlightText item={item} /></div>
          </div>
        ))}
      </div>
    </section>
  )
}

function Field({ label, value, tone, children }) {
  return (
    <div className={`incident-field ${tone || ''}`}>
      <span>{label}</span>
      <strong className={!value ? 'waiting' : ''}>{value || 'Waiting…'}</strong>
      {children}
    </div>
  )
}

function IncidentPanel({ incident, sessionId, onConfirm, onLocation }) {
  const readyToConfirm = incident.type !== 'unknown' && incident.location.text && !incident.dispatch_confirmed
  return (
    <section className="console-card incident-card">
      <div className="card-heading">
        <div><span className="eyebrow">What we understand</span><h2>Incident card</h2></div>
        <span className={`confidence confidence-${incident.location.confidence}`}>{incident.location.confidence} confidence</span>
      </div>
      <div className="incident-grid">
        <Field label="What happened" value={incident.type === 'unknown' ? '' : labelize(incident.type)} tone={incident.type !== 'unknown' ? 'filled' : ''} />
        <Field label="Severity" value={incident.severity === 'unknown' ? '' : labelize(incident.severity)} tone={incident.severity === 'critical' ? 'critical' : incident.severity !== 'unknown' ? 'filled' : ''} />
        <Field label="Location" value={incident.location.text} tone={incident.location.text ? 'location-field' : ''}>
          {incident.location.landmarks?.length > 0 && <small><MapPin size={13} /> {incident.location.landmarks.join(' · ')}</small>}
        </Field>
        <div className="two-fields">
          <Field label="People" value={incident.people.count || ''} tone={incident.people.count ? 'filled' : ''} />
          <Field label="Injured" value={incident.people.injured || ''} tone={incident.people.injured ? 'filled' : ''} />
        </div>
        <div className="two-fields">
          <Field label="Conscious" value={incident.people.conscious === 'unknown' ? '' : labelize(incident.people.conscious)} tone={incident.people.conscious !== 'unknown' ? 'filled' : ''} />
          <Field label="Caller safe" value={incident.caller_safe === 'unknown' ? '' : labelize(incident.caller_safe)} tone={incident.caller_safe !== 'unknown' ? 'filled' : ''} />
        </div>
        <Field label="Immediate hazards" value={incident.hazards?.length ? incident.hazards.map(labelize).join(', ') : ''} tone={incident.hazards?.length ? 'hazard-field' : ''} />
      </div>
      <div className="incident-actions">
        {readyToConfirm && <button className="confirm-button" onClick={() => onConfirm(true)}><Check size={17} /> Confirm type + location</button>}
        {incident.dispatch_confirmed && <span className="confirmed-pill"><Check size={15} /> Confirmed with caller</span>}
        <button className="location-button" onClick={onLocation}><Navigation size={16} /> Share exact GPS</button>
      </div>
      {incident.silent_mode && <div className="silent-notice"><ShieldAlert size={18} /><div><strong>Silent mode active</strong><span>Address will not be spoken aloud.</span></div></div>}
      {(incident.evidence?.motion_detected || incident.evidence?.video_captured) && (
        <div className="evidence-notice"><Video size={18} /><div><strong>Context evidence attached</strong><span>{incident.evidence.motion_detected ? `Movement spike${incident.evidence.motion_peak ? ` · ${incident.evidence.motion_peak} m/s²` : ''}` : 'Manual silent report'}{incident.evidence.video_captured ? ' · 10-second clip' : ''}</span></div>{incident.evidence.video_captured && <a href={api.evidenceVideoUrl(sessionId)} target="_blank" rel="noreferrer">View clip</a>}</div>
      )}
    </section>
  )
}

function TimelinePanel({ incident, startedAt }) {
  const base = [
    { label: 'Understanding the situation', status: incident.type !== 'unknown' ? 'done' : 'ringing', detail: incident.type !== 'unknown' ? labelize(incident.type) : 'Listening for details' },
    { label: 'Confirmed with caller', status: incident.dispatch_confirmed ? 'done' : 'queued', detail: incident.dispatch_confirmed ? 'Type and location confirmed' : 'Waiting for a clear yes' },
  ]
  const rows = [...base, ...(incident.actions || []).map((action) => ({
    label: action.kind === 'sms' ? 'Location link sent' : `${action.status === 'done' ? 'Contacted' : 'Calling'} ${action.target}`,
    status: action.status,
    detail: action.script_summary,
    simulated: action.simulated,
    ts: action.ts,
  }))]
  return (
    <section className="console-card timeline-card">
      <div className="card-heading"><div><span className="eyebrow">What is happening</span><h2>Who we called</h2></div><PhoneCall size={20} /></div>
      <div className="timeline">
        {rows.map((row, index) => (
          <div className="timeline-row" key={`${row.label}-${index}`}>
            <div className="timeline-rail"><StatusIcon status={row.status} />{index < rows.length - 1 && <i />}</div>
            <div><span className="timeline-label">{row.label}</span><p>{row.detail}</p><small>{row.simulated && 'Simulated · '}{row.ts ? new Date(row.ts).toLocaleTimeString([], { minute: '2-digit', second: '2-digit' }) : index === 0 ? <SessionTimer startedAt={startedAt} /> : 'Pending'}</small></div>
          </div>
        ))}
      </div>
    </section>
  )
}

export default function LiveConsole({ config }) {
  const { session, connected, error, runDemo, startLiveCall, submitSilentIncident, stop, clear, confirm, sendDigit, shareLocation } = useLiveSession()
  const incident = session?.incident
  if (!session || !incident) return <div className="loading-page"><span className="listening"><i /> Preparing a safe session…</span>{error && <p>{error}</p>}</div>

  return (
    <div className="console-page">
      <FirstVisitTour />
      <div className="console-titlebar">
        <div><span className="eyebrow"><Radio size={14} /> Mission control</span><h1>Live Console</h1><p>One call, understood together.</p></div>
        <div className="console-tools">
          <span className={`connection ${connected ? 'online' : ''}`}><i />{connected ? 'Live link connected' : 'Reconnecting'}</span>
          <button className="small-button" onClick={() => runDemo('accident')} disabled={session.status !== 'idle'}><Play size={15} fill="currentColor" /> Run demo</button>
          <button className="small-button subtle" onClick={() => runDemo('silent')} disabled={session.status !== 'idle'}><Headphones size={15} /> Silent demo</button>
        </div>
      </div>
      {error && <div className="error-banner"><AlertTriangle size={17} />{error}</div>}
      {session.source === 'bolna' && session.status === 'listening' && !incident.transcript.length && (
        <div className="live-call-notice"><PhoneCall size={17} /><span><strong>Live call active.</strong> Answer the configured phone and complete the conversation. The verified Bolna transcript will appear here when the call finishes.</span></div>
      )}
      <MotionIncidentFlow session={session} liveCallReady={config.live_call_ready} onStartLiveCall={startLiveCall} onSubmit={submitSilentIncident} />
      <div className="console-grid">
        <TranscriptPanel transcript={incident.transcript || []} />
        <IncidentPanel incident={incident} sessionId={incident.session_id} onConfirm={confirm} onLocation={shareLocation} />
        <TimelinePanel incident={incident} startedAt={session.started_at} />
      </div>

      {incident.silent_mode && !incident.dispatch_confirmed && (
        <div className="dtmf-panel"><span>Quiet confirmation</span><p>Use keypad-style answers. No address will be read aloud.</p><button onClick={() => sendDigit('1')}>1 <small>Yes</small></button><button onClick={() => sendDigit('2')}>2 <small>No</small></button></div>
      )}

      <div className="control-bar">
        <button className="stop-button" onClick={stop} disabled={session.status === 'stopped' || session.status === 'complete'}><CircleStop size={20} /> Stop all actions</button>
        <div className="session-meta"><span>Session time <strong><SessionTimer startedAt={session.started_at} endedAt={session.ended_at} /></strong></span><i /><span>Language <strong>{incident.language_detected.toUpperCase()}</strong></span><i /><span className={incident.silent_mode ? 'silent-active' : ''}>{incident.silent_mode ? 'Silent mode' : 'Voice mode'}</span></div>
        <button className="clear-button" onClick={clear}><RotateCcw size={17} /> Clear session</button>
      </div>
      <div className="safety-note"><ShieldAlert size={15} /><span>Never call 100, 101, 102, 108, or 112 from this demo. External actions require caller confirmation.</span><ChevronRight size={15} /></div>
    </div>
  )
}
