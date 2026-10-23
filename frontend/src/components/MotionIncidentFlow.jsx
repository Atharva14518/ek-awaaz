import { useEffect, useRef, useState } from 'react'
import { Activity, Camera, Check, LocateFixed, MapPin, PhoneCall, ShieldAlert, Video, X } from 'lucide-react'
import { api } from '../api'

const TEN_MINUTES = 10 * 60 * 1000

function magnitudeOf(event) {
  const value = event.acceleration || event.accelerationIncludingGravity
  if (!value) return null
  const { x = 0, y = 0, z = 0 } = value
  return Math.sqrt(x * x + y * y + z * z)
}

export default function MotionIncidentFlow({ session, liveCallReady, onStartLiveCall, onSubmit }) {
  const demoPopupRequested = new URLSearchParams(window.location.search).get('motiondemo') === '1'
  const [open, setOpen] = useState(demoPopupRequested)
  const [trigger, setTrigger] = useState(demoPopupRequested ? 'motion' : 'manual')
  const [monitoring, setMonitoring] = useState(false)
  const [sensorMessage, setSensorMessage] = useState('Motion watch is off')
  const [motionPeak, setMotionPeak] = useState(demoPopupRequested ? 24.6 : null)
  const [address, setAddress] = useState('')
  const [coords, setCoords] = useState(null)
  const [locationStatus, setLocationStatus] = useState('')
  const [addressConfirmed, setAddressConfirmed] = useState(false)
  const [incidentType, setIncidentType] = useState('road_accident')
  const [people, setPeople] = useState(1)
  const [injured, setInjured] = useState(1)
  const [conscious, setConscious] = useState('unknown')
  const [severity, setSeverity] = useState('high')
  const [notes, setNotes] = useState('')
  const [recording, setRecording] = useState(false)
  const [secondsLeft, setSecondsLeft] = useState(10)
  const [videoBlob, setVideoBlob] = useState(null)
  const [videoUrl, setVideoUrl] = useState('')
  const [videoError, setVideoError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [formError, setFormError] = useState('')
  const samples = useRef([])
  const lastTriggerAt = useRef(0)
  const lastSensorUpdateAt = useRef(0)
  const streamRef = useRef(null)
  const recorderRef = useRef(null)
  const timerRef = useRef(null)
  const videoRef = useRef(null)

  useEffect(() => {
    if (!monitoring) return undefined
    const handleMotion = (event) => {
      const magnitude = magnitudeOf(event)
      if (magnitude === null) return
      const now = Date.now()
      samples.current = samples.current.filter((sample) => sample.ts >= now - TEN_MINUTES)
      const previous = samples.current.map((sample) => sample.value)
      if (previous.length >= 12) {
        const mean = previous.reduce((total, value) => total + value, 0) / previous.length
        const variance = previous.reduce((total, value) => total + ((value - mean) ** 2), 0) / previous.length
        const threshold = Math.max(15, mean + 3 * Math.max(Math.sqrt(variance), 0.8))
        if (magnitude > threshold && now - lastTriggerAt.current > 30000) {
          lastTriggerAt.current = now
          setMotionPeak(Number(magnitude.toFixed(1)))
          setTrigger('motion')
          setOpen(true)
        }
      }
      samples.current.push({ ts: now, value: magnitude })
      if (now - lastSensorUpdateAt.current >= 1000) {
        lastSensorUpdateAt.current = now
        setSensorMessage(`Watching · ${Math.min(10, Math.ceil((now - samples.current[0].ts) / 60000)) || '<1'} min baseline`)
      }
    }
    window.addEventListener('devicemotion', handleMotion)
    return () => window.removeEventListener('devicemotion', handleMotion)
  }, [monitoring])

  useEffect(() => () => {
    window.clearInterval(timerRef.current)
    streamRef.current?.getTracks().forEach((track) => track.stop())
    if (videoUrl) URL.revokeObjectURL(videoUrl)
  }, [videoUrl])

  const enableMotion = async () => {
    setFormError('')
    try {
      if (typeof DeviceMotionEvent === 'undefined') throw new Error('This device does not expose motion sensors to the browser.')
      if (typeof DeviceMotionEvent.requestPermission === 'function') {
        const permission = await DeviceMotionEvent.requestPermission()
        if (permission !== 'granted') throw new Error('Motion permission was not granted.')
      }
      samples.current = []
      setMonitoring(true)
      setSensorMessage('Watching · building baseline')
    } catch (error) {
      setFormError(error.message)
    }
  }

  const openManual = () => {
    setTrigger('manual')
    setMotionPeak(null)
    setOpen(true)
  }

  const simulateSpike = () => {
    setTrigger('motion')
    setMotionPeak(24.6)
    setOpen(true)
  }

  const captureLocation = () => {
    setLocationStatus('Finding your location…')
    setFormError('')
    if (!navigator.geolocation) {
      setLocationStatus('')
      setFormError('Location is not available in this browser.')
      return
    }
    navigator.geolocation.getCurrentPosition(({ coords: next }) => {
      const captured = { lat: next.latitude, lng: next.longitude }
      setCoords(captured)
      setAddressConfirmed(false)
      setAddress(`GPS ${captured.lat.toFixed(5)}, ${captured.lng.toFixed(5)}`)
      setLocationStatus('GPS captured. Check the address or add a nearby landmark.')
    }, () => {
      setLocationStatus('')
      setFormError('Location permission was not granted. Enter the address manually.')
    }, { enableHighAccuracy: true, timeout: 10000 })
  }

  const stopCamera = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
  }

  const recordVideo = async () => {
    setVideoError('')
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setVideoError('Video recording is not supported in this browser.')
      return
    }
    try {
      if (videoUrl) URL.revokeObjectURL(videoUrl)
      setVideoUrl('')
      setVideoBlob(null)
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      const preferred = ['video/webm;codecs=vp9', 'video/webm', 'video/mp4'].find((type) => MediaRecorder.isTypeSupported(type))
      const recorder = new MediaRecorder(stream, preferred ? { mimeType: preferred } : undefined)
      recorderRef.current = recorder
      const chunks = []
      recorder.ondataavailable = (event) => { if (event.data.size) chunks.push(event.data) }
      recorder.onstop = () => {
        const blob = new Blob(chunks, { type: recorder.mimeType || 'video/webm' })
        setVideoBlob(blob)
        setVideoUrl(URL.createObjectURL(blob))
        setRecording(false)
        stopCamera()
      }
      recorder.start(250)
      setRecording(true)
      setSecondsLeft(10)
      let remaining = 10
      timerRef.current = window.setInterval(() => {
        remaining -= 1
        setSecondsLeft(remaining)
        if (remaining <= 0) {
          window.clearInterval(timerRef.current)
          if (recorder.state !== 'inactive') recorder.stop()
        }
      }, 1000)
    } catch {
      setVideoError('Camera permission was not granted. You can still submit the silent form.')
      stopCamera()
    }
  }

  const close = () => {
    if (recording && recorderRef.current?.state !== 'inactive') recorderRef.current.stop()
    window.clearInterval(timerRef.current)
    stopCamera()
    setOpen(false)
  }

  const submit = async (event) => {
    event.preventDefault()
    setFormError('')
    if (!address.trim() || !addressConfirmed) {
      setFormError('Confirm the address before proceeding.')
      return
    }
    setSubmitting(true)
    try {
      if (videoBlob) await api.uploadEvidenceVideo(session.incident.session_id, videoBlob)
      await onSubmit({
        incident_type: incidentType,
        address: address.trim(),
        address_confirmed: true,
        lat: coords?.lat ?? null,
        lng: coords?.lng ?? null,
        people: Number(people),
        injured: Number(injured),
        conscious,
        severity,
        notes: notes.trim(),
        motion_detected: trigger === 'motion',
        motion_peak: motionPeak,
        video_captured: Boolean(videoBlob),
        video_duration_seconds: videoBlob ? 10 : 0,
      })
      setOpen(false)
    } catch (error) {
      setFormError(error.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <section className="intake-paths" aria-label="Choose an incident intake path">
        <div className="intake-path voice-path">
          <span className="path-icon"><PhoneCall size={19} /></span>
          <div><strong>I can speak</strong><small>Live Bolna call and voice transcription</small></div>
          <button onClick={onStartLiveCall} disabled={session.status !== 'idle' || !liveCallReady}>{liveCallReady ? 'Call me live' : 'Live call unavailable'}</button>
        </div>
        <div className="intake-path motion-path">
          <span className={`path-icon ${monitoring ? 'watching' : ''}`}><Activity size={19} /></span>
          <div><strong>I cannot speak</strong><small>{monitoring ? sensorMessage : 'Location, taps and a 10-second scene clip'}</small></div>
          <button onClick={openManual} disabled={session.status !== 'idle'}>Open safety popup</button>
          <button className="text-trigger" onClick={monitoring ? simulateSpike : enableMotion} disabled={session.status !== 'idle'}>{monitoring ? 'Demo movement spike' : 'Enable motion watch'}</button>
          {!monitoring && <button className="text-trigger" onClick={simulateSpike} disabled={session.status !== 'idle'}>Simulate spike</button>}
        </div>
      </section>

      {formError && !open && <div className="error-banner"><ShieldAlert size={17} />{formError}</div>}

      {open && (
        <div className="incident-modal-backdrop" role="presentation">
          <section className="incident-modal" role="dialog" aria-modal="true" aria-labelledby="incident-popup-title">
            <header>
              <div className="motion-alert-icon"><Activity size={22} /></div>
              <div><span className="eyebrow">{trigger === 'motion' ? 'Movement spike detected' : 'No-voice incident path'}</span><h2 id="incident-popup-title">Get help without speaking</h2><p>No call is required. Confirm only what you know.</p></div>
              <button className="modal-close" onClick={close} aria-label="Close"><X size={19} /></button>
            </header>

            <form onSubmit={submit}>
              <div className="silent-form-grid">
                <div className="silent-form-main">
                  <div className="form-section-heading"><MapPin size={17} /><div><strong>1. Confirm the location</strong><small>GPS is never treated as an emergency by itself.</small></div></div>
                  <button type="button" className="capture-location" onClick={captureLocation}><LocateFixed size={16} /> Use my live location</button>
                  <label>Address or nearest landmark<input value={address} onChange={(event) => { setAddress(event.target.value); setAddressConfirmed(false) }} placeholder="Enter a clear address or landmark" /></label>
                  {locationStatus && <p className="field-status">{locationStatus}</p>}
                  <label className="confirm-check"><input type="checkbox" checked={addressConfirmed} onChange={(event) => setAddressConfirmed(event.target.checked)} disabled={!address.trim()} /><span><Check size={15} /> I confirm this location is correct</span></label>

                  <div className="form-section-heading details-heading"><ShieldAlert size={17} /><div><strong>2. Add essential details</strong><small>Large controls for a person who cannot talk.</small></div></div>
                  <div className="compact-fields">
                    <label>Incident<select value={incidentType} onChange={(event) => setIncidentType(event.target.value)}><option value="road_accident">Road accident</option><option value="medical">Medical</option><option value="fire">Fire</option><option value="assault">Unsafe / assault</option><option value="other">Other</option></select></label>
                    <label>Severity<select value={severity} onChange={(event) => setSeverity(event.target.value)}><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option><option value="low">Low</option></select></label>
                    <label>People<input type="number" min="0" max="100" value={people} onChange={(event) => setPeople(event.target.value)} /></label>
                    <label>Injured<input type="number" min="0" max="100" value={injured} onChange={(event) => setInjured(event.target.value)} /></label>
                    <label>Conscious<select value={conscious} onChange={(event) => setConscious(event.target.value)}><option value="unknown">Unknown</option><option value="yes">Yes</option><option value="no">No</option></select></label>
                  </div>
                  <label>Short note<textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Fuel leak, chest pain, blocked road…" rows="2" /></label>
                </div>

                <aside className="video-capture-card">
                  <div className="form-section-heading"><Camera size={17} /><div><strong>3. Record the scene</strong><small>Stops automatically after 10 seconds.</small></div></div>
                  <div className="video-frame">
                    {videoUrl ? <video src={videoUrl} controls playsInline /> : <video ref={videoRef} muted playsInline />}
                    {!recording && !videoUrl && <div className="video-placeholder"><Camera size={28} /><span>Camera preview</span></div>}
                    {recording && <span className="recording-count"><i /> REC · {secondsLeft}s</span>}
                  </div>
                  <button type="button" className="record-button" onClick={recordVideo} disabled={recording}><Video size={16} />{videoUrl ? 'Record again' : recording ? `Recording ${secondsLeft}s` : 'Record 10-second video'}</button>
                  {videoUrl && <span className="video-ready"><Check size={14} /> Clip ready to attach</span>}
                  {videoError && <p className="video-error">{videoError}</p>}
                  <p className="privacy-copy">The clip is uploaded only after you press “Submit incident.” This demo still uses test contacts only.</p>
                </aside>
              </div>

              {formError && <div className="modal-error"><ShieldAlert size={16} />{formError}</div>}
              <footer><span><ShieldAlert size={15} /> Not a replacement for 112/911</span><button type="submit" disabled={submitting || !addressConfirmed}>{submitting ? 'Submitting…' : 'Submit incident without calling'}</button></footer>
            </form>
          </section>
        </div>
      )}
    </>
  )
}
