import { RefreshCw, Shield } from 'lucide-react'
import ValidationResult from './ValidationResult.jsx'

const OUTCOMES = [
  { key: 'success', label: '✅ Worked', cls: 'border-green-700 text-green-400 hover:bg-green-900/30' },
  { key: 'partial', label: '⚠️ Partial', cls: 'border-yellow-700 text-yellow-400 hover:bg-yellow-900/30' },
  { key: 'failed', label: '❌ Failed', cls: 'border-red-700 text-red-400 hover:bg-red-900/30' },
]

export default function ResolutionPanel({
  outcome, validation, busy, validating, onOutcome, onValidate,
}) {
  return (
    <>
      {!outcome && !validation && (
        <div className="card border-green-800/40 bg-green-900/5">
          <div className="text-white font-semibold text-sm mb-3">How did it go?</div>
          <div className="flex gap-3">
            {OUTCOMES.map(({ key, label, cls }) => (
              <button
                key={key}
                disabled={busy}
                onClick={() => onOutcome(key)}
                className={`flex-1 py-2 rounded-lg text-sm font-semibold border transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${cls}`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      )}

      {outcome && !validation && (
        <div className="card">
          <div className="text-white font-semibold text-sm mb-2">Outcome recorded: <span className="text-dt-blue">{outcome}</span></div>
          <button
            onClick={onValidate}
            disabled={validating}
            className="btn-primary flex items-center gap-2"
          >
            {validating
              ? <><RefreshCw size={13} className="spin-slow" /> Claude is validating...</>
              : <><Shield size={13} /> Validate Recovery with AI</>
            }
          </button>
        </div>
      )}

      {validation && <ValidationResult validation={validation} />}
    </>
  )
}
