import { CheckCircle2, AlertTriangle } from 'lucide-react'

export default function ValidationResult({ validation }) {
  return (
    <div className={`card border ${
      validation.recovery_confirmed ? 'border-green-700/50 bg-green-900/10' : 'border-yellow-700/50 bg-yellow-900/10'
    }`}>
      <div className="flex items-center gap-2 mb-2">
        {validation.recovery_confirmed
          ? <CheckCircle2 size={16} className="text-green-400" aria-hidden="true" />
          : <AlertTriangle size={16} className="text-yellow-400" aria-hidden="true" />
        }
        <span className="text-white font-semibold text-sm">
          {validation.recovery_confirmed ? 'Recovery Confirmed' : 'Recovery Uncertain'}
          <span className="ml-2 text-dt-text/50 font-normal">{validation.confidence}% confidence</span>
        </span>
      </div>
      <p className="text-dt-text/70 text-sm mb-3">{validation.summary}</p>
      {validation.remaining_checks?.length > 0 && (
        <ul className="space-y-1.5">
          {validation.remaining_checks.map((c, i) => (
            <li key={i} className="text-xs text-dt-text/60 flex items-start gap-1.5">
              <span className="text-dt-blue/60" aria-hidden="true">→</span> {c}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
