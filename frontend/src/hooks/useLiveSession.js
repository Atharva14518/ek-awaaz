import { useCallback, useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, websocketUrl } from '../api'

function addTranscript(incident, chunk) {
  const transcript = incident.transcript || []
  const exists = transcript.some((item) => item.ts === chunk.ts && item.speaker === chunk.speaker && item.text === chunk.text)
  return exists ? incident : { ...incident, transcript: [...transcript, chunk] }
}

export default function useLiveSession() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [session, setSession] = useState(null)
  const [connected, setConnected] = useState(false)
  const [error, setError] = useState('')
  const [lastEvent, setLastEvent] = useState(null)
  const socketRef = useRef(null)
  const initializing = useRef(false)
  const autostarted = useRef(false)
  const requestedSession = useRef(searchParams.get('session'))
  const autostartRequested = useRef(searchParams.get('autostart') === '1')
  const requestedScenario = useRef(searchParams.get('scenario') === 'silent' ? 'silent' : 'accident')

  const applyEvent = useCallback((message) => {
    setLastEvent(message)
    setSession((current) => {
      if (message.event === 'session.snapshot') return message.data.session
      if (!current) return current
      const fullIncident = message.data?.incident
      if (fullIncident) return { ...current, incident: fullIncident, status: message.event === 'session.completed' ? 'complete' : current.status }
      if (message.event === 'transcript.chunk') {
        return { ...current, incident: addTranscript(current.incident, message.data.chunk), status: 'listening' }
      }
      if (message.event === 'simulation.started') return { ...current, status: 'listening' }
      if (message.event === 'dispatch.started') return { ...current, status: 'dispatching' }
      if (message.event === 'session.stopped') return { ...current, status: 'stopped' }
      return current
    })
  }, [])

  const connect = useCallback((sessionId) => {
    if (socketRef.current) socketRef.current.close()
    const socket = new WebSocket(websocketUrl(sessionId))
    socketRef.current = socket
    socket.onopen = () => {
      if (socketRef.current === socket) setConnected(true)
    }
    socket.onmessage = (event) => {
      try { applyEvent(JSON.parse(event.data)) } catch { setError('A live update could not be read.') }
    }
    socket.onerror = () => {
      if (socketRef.current === socket) setError('Live updates are reconnecting…')
    }
    socket.onclose = () => {
      if (socketRef.current === socket) setConnected(false)
    }
  }, [applyEvent])

  const loadOrCreate = useCallback(async () => {
    if (initializing.current) return
    initializing.current = true
    setError('')
    try {
      const requested = requestedSession.current
      let created
      if (requested) {
        try { created = await api.getSession(requested) } catch { created = await api.createSession() }
      } else {
        created = await api.createSession()
      }
      requestedSession.current = created.incident.session_id
      setSession(created)
      setSearchParams((params) => {
        params.set('session', created.incident.session_id)
        return params
      }, { replace: true })
      connect(created.incident.session_id)
    } catch (err) {
      setError(err.message)
      initializing.current = false
    }
  }, [connect, setSearchParams])

  useEffect(() => {
    loadOrCreate()
    return () => socketRef.current?.close()
    // Session bootstrap is intentionally mount-only. React Router changes the
    // query string after creation; re-running this effect would close the live
    // socket that was just opened.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!session || !connected || autostarted.current || !autostartRequested.current) return
    autostarted.current = true
    api.simulate(session.incident.session_id, requestedScenario.current).catch((err) => {
      // A restored/duplicated tab can race the same autostart request. The
      // active session and its WebSocket remain valid, so do not alarm users.
      if (!/already been used|already running/i.test(err.message)) setError(err.message)
    })
  }, [connected, session])

  const refresh = useCallback(async () => {
    if (!session) return
    const updated = await api.getSession(session.incident.session_id)
    setSession(updated)
  }, [session])

  const runDemo = useCallback(async (scenario = 'accident') => {
    if (!session) return
    setError('')
    try { await api.simulate(session.incident.session_id, scenario) } catch (err) { setError(err.message) }
  }, [session])

  const stop = useCallback(async () => {
    if (!session) return
    try {
      await api.stop(session.incident.session_id)
      await refresh()
    } catch (err) { setError(err.message) }
  }, [refresh, session])

  const clear = useCallback(async () => {
    if (!session) return
    try {
      await api.clearSession(session.incident.session_id)
      socketRef.current?.close()
      initializing.current = false
      autostarted.current = false
      requestedSession.current = null
      autostartRequested.current = false
      setSession(null)
      setSearchParams({}, { replace: true })
      await loadOrCreate()
    } catch (err) { setError(err.message) }
  }, [loadOrCreate, session, setSearchParams])

  const confirm = useCallback(async (confirmed = true) => {
    if (!session) return
    try {
      const updated = await api.confirm(session.incident.session_id, confirmed)
      setSession(updated)
    } catch (err) { setError(err.message) }
  }, [session])

  const sendDigit = useCallback(async (digit) => {
    if (!session) return
    try { setSession(await api.dtmf(session.incident.session_id, digit)) } catch (err) { setError(err.message) }
  }, [session])

  const shareLocation = useCallback(() => {
    if (!session || !navigator.geolocation) {
      setError('Location sharing is not available in this browser.')
      return
    }
    navigator.geolocation.getCurrentPosition(async ({ coords }) => {
      try { setSession(await api.location(session.incident.session_id, coords.latitude, coords.longitude)) } catch (err) { setError(err.message) }
    }, () => setError('Location permission was not granted.'))
  }, [session])

  return { session, connected, error, lastEvent, runDemo, stop, clear, confirm, sendDigit, shareLocation }
}
