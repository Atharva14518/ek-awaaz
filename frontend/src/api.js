const API = import.meta.env.VITE_API_URL || ''

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = await response.json()
      message = body.detail || message
    } catch {
      // Keep the useful status fallback.
    }
    throw new Error(message)
  }
  if (response.status === 204) return null
  return response.json()
}

export const api = {
  config: () => request('/api/config'),
  health: () => request('/api/health'),
  createSession: (source = 'simulator') => request(`/api/sessions?source=${source}`, { method: 'POST' }),
  getSession: (id) => request(`/api/sessions/${id}`),
  clearSession: (id) => request(`/api/sessions/${id}`, { method: 'DELETE' }),
  simulate: (id, scenario = 'accident') => request(`/api/sessions/${id}/simulate?scenario=${scenario}`, { method: 'POST' }),
  startLiveCall: (id) => request(`/api/sessions/${id}/live-call`, {
    method: 'POST',
    body: JSON.stringify({ confirm: true }),
  }),
  stop: (id) => request(`/api/sessions/${id}/stop`, { method: 'POST' }),
  confirm: (id, confirmed, correction = null) => request(`/api/sessions/${id}/confirm`, {
    method: 'POST',
    body: JSON.stringify({ confirmed, correction }),
  }),
  dtmf: (id, digit) => request(`/api/sessions/${id}/dtmf`, {
    method: 'POST',
    body: JSON.stringify({ digit }),
  }),
  location: (id, lat, lng) => request(`/api/sessions/${id}/location`, {
    method: 'POST',
    body: JSON.stringify({ lat, lng }),
  }),
  reports: () => request('/api/reports'),
  report: (id) => request(`/api/reports/${id}`),
  pdfUrl: (id) => `${API}/api/reports/${id}/pdf`,
}

export function websocketUrl(sessionId) {
  if (import.meta.env.VITE_WS_URL) return `${import.meta.env.VITE_WS_URL}/ws/sessions/${sessionId}`
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.port === '5173' ? `${window.location.hostname}:8000` : window.location.host
  return `${protocol}//${host}/ws/sessions/${sessionId}`
}
