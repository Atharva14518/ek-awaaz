import { useEffect, useState } from 'react'

export default function SessionTimer({ startedAt, endedAt }) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => {
    if (endedAt) return undefined
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [endedAt])
  const elapsed = Math.max(0, new Date(endedAt || now).getTime() - new Date(startedAt).getTime())
  const seconds = Math.floor(elapsed / 1000)
  return <span>{String(Math.floor(seconds / 60)).padStart(2, '0')}:{String(seconds % 60).padStart(2, '0')}</span>
}

