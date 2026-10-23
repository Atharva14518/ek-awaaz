import { useState } from 'react'
import { ArrowRight, Check, Clipboard, Headphones, MapPin, Phone, Play, Radio, Users } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function HomePage({ config }) {
  const [copied, setCopied] = useState(false)
  const copyNumber = async () => {
    await navigator.clipboard.writeText(config.demo_phone_number)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1600)
  }

  return (
    <div className="home-page">
      <section className="hero">
        <div className="hero-copy">
          <span className="eyebrow"><Radio size={14} /> Voice-first emergency support</span>
          <h1>One voice.<br /><em>Many hands.</em></h1>
          <p className="hero-lede">In an emergency, speaking may be all someone can do. Ek Awaaz listens, understands, and coordinates trusted contacts—while a calm guide stays on the line.</p>
          <div className="hero-actions">
            <Link className="button primary" to="/console">Open Live Console <ArrowRight size={18} /></Link>
            <Link className="button secondary" to="/console?autostart=1"><Play size={17} fill="currentColor" /> Watch demo scenario</Link>
          </div>
          <p className="microcopy"><Check size={15} /> No emergency services are called. This build uses test contacts only.</p>
        </div>
        <div className="hero-visual" aria-label="A calm emergency call becoming coordinated support">
          <div className="call-card">
            <div className="caller-avatar"><span>EA</span><i /></div>
            <div>
              <span className="call-label">Listening now</span>
              <strong>“Bike ka accident hua hai…”</strong>
              <div className="waveform" aria-hidden="true">{[14, 28, 20, 38, 18, 31, 23, 36, 16, 26, 12, 30].map((height, i) => <i style={{ height }} key={i} />)}</div>
            </div>
          </div>
          <div className="signal-path" aria-hidden="true"><i /><i /><i /></div>
          <div className="response-stack">
            <div><span className="mini-icon coral"><Phone size={17} /></span><p><strong>Demo ambulance</strong><small>Calling stand-in contact</small></p><span className="live-dot">Live</span></div>
            <div><span className="mini-icon blue"><MapPin size={17} /></span><p><strong>Location understood</strong><small>Blue temple, after flyover</small></p><Check size={17} className="sage" /></div>
            <div><span className="mini-icon sage-bg"><Users size={17} /></span><p><strong>Family informed</strong><small>Only essential details shared</small></p><Check size={17} className="sage" /></div>
          </div>
          <span className="visual-note">Voice stays the interface. The screen keeps everyone aligned.</span>
        </div>
      </section>

      {config.demo_phone_number && (
        <section className="number-strip" aria-label="Demo number">
          <div><span className="eyebrow">Try the demo line</span><strong>{config.demo_phone_number}</strong></div>
          <button className="copy-button" onClick={copyNumber}>{copied ? <Check size={17} /> : <Clipboard size={17} />}{copied ? 'Copied' : 'Copy number'}</button>
          <span className="number-note">Not a real emergency number</span>
        </section>
      )}

      <section className="how-it-works">
        <div className="section-heading"><span className="eyebrow">How it works</span><h2>Less to remember.<br />More help in motion.</h2></div>
        <div className="steps-grid">
          <article><span className="step-number">01</span><div className="step-icon"><Phone size={23} /></div><h3>Call</h3><p>Speak naturally in Hindi, Marathi, English, or a mix.</p></article>
          <article><span className="step-number">02</span><div className="step-icon"><Headphones size={23} /></div><h3>We listen and understand</h3><p>A calm voice asks one short question at a time.</p></article>
          <article><span className="step-number">03</span><div className="step-icon"><Users size={23} /></div><h3>Help is contacted</h3><p>After confirmation, tailored calls and a location link go out.</p></article>
        </div>
      </section>
    </div>
  )
}
