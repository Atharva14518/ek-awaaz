import { useState } from 'react'
import { ArrowRight, X } from 'lucide-react'

const steps = [
  ['Listen', 'The caller’s words appear here as they speak.'],
  ['Understand', 'Important facts quietly fill the incident card.'],
  ['Coordinate', 'Confirmed actions and their live status stay visible.'],
]

export default function FirstVisitTour() {
  const recordingMode = new URLSearchParams(window.location.search).get('recording') === '1'
  const [open, setOpen] = useState(() => localStorage.getItem('ek-tour-seen') !== 'yes')
  const [step, setStep] = useState(0)
  if (!open || recordingMode) return null
  const dismiss = () => {
    localStorage.setItem('ek-tour-seen', 'yes')
    setOpen(false)
  }
  return (
    <aside className="tour" aria-label="Live Console tour" aria-live="polite">
      <button className="tour-close" onClick={dismiss} aria-label="Dismiss tour"><X size={17} /></button>
      <span className="eyebrow">A quick tour · {step + 1} of 3</span>
      <h3>{steps[step][0]}</h3>
      <p>{steps[step][1]}</p>
      <div className="tour-footer">
        <div className="tour-dots">{steps.map((_, index) => <i key={index} className={index === step ? 'active' : ''} />)}</div>
        <button className="text-button" onClick={() => step === 2 ? dismiss() : setStep(step + 1)}>
          {step === 2 ? 'Got it' : 'Next'} <ArrowRight size={15} />
        </button>
      </div>
    </aside>
  )
}
