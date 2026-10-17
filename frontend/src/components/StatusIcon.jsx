import { Check, Circle, LoaderCircle, PhoneCall, X } from 'lucide-react'

export default function StatusIcon({ status, kind }) {
  if (status === 'failed') return <span className="status-icon failed"><X size={14} /></span>
  if (status === 'done') return <span className="status-icon done"><Check size={14} /></span>
  if (status === 'connected') return <span className="status-icon connected"><PhoneCall size={13} /></span>
  if (status === 'ringing') return <span className="status-icon active"><LoaderCircle size={14} /></span>
  return <span className="status-icon queued"><Circle size={11} /></span>
}

