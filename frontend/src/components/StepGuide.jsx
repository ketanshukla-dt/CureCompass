import { CheckCircle2, Circle, Terminal, ShieldCheck } from 'lucide-react'
import { useState } from 'react'

export default function StepGuide({ steps }) {
  const [completed, setCompleted] = useState(new Set())

  const toggle = (n) => {
    setCompleted(prev => {
      const next = new Set(prev)
      next.has(n) ? next.delete(n) : next.add(n)
      return next
    })
  }

  const progress = Math.round((completed.size / steps.length) * 100)

  return (
    <div>
      {/* Progress bar */}
      <div className="flex items-center justify-between mb-4 text-xs text-dt-text/60">
        <span>{completed.size} of {steps.length} steps completed</span>
        <span className="font-semibold text-dt-blue">{progress}%</span>
      </div>
      <div className="h-1.5 bg-dt-dark rounded-full mb-5">
        <div
          className="h-1.5 bg-dt-blue rounded-full transition-all duration-500"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Steps */}
      <div className="space-y-3">
        {steps.map((step) => {
          const done = completed.has(step.step_number)
          return (
            <div
              key={step.step_number}
              onClick={() => toggle(step.step_number)}
              className={`flex gap-3 p-3 rounded-lg cursor-pointer transition-all border ${
                done
                  ? 'border-green-800/40 bg-green-900/10 opacity-70'
                  : step.is_validation
                  ? 'border-dt-blue/30 bg-dt-blue/5 hover:border-dt-blue/50'
                  : 'border-dt-border hover:border-dt-border/80 bg-dt-dark/50'
              }`}
            >
              {/* Icon */}
              <div className="mt-0.5 shrink-0">
                {done ? (
                  <CheckCircle2 size={16} className="text-green-400" />
                ) : step.is_validation ? (
                  <ShieldCheck size={16} className="text-dt-blue" />
                ) : (
                  <Circle size={16} className="text-dt-text/30" />
                )}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-xs font-bold text-dt-text/40">STEP {step.step_number}</span>
                  {step.is_validation && (
                    <span className="text-xs text-dt-blue/70">Validation</span>
                  )}
                </div>
                <div className={`text-sm font-medium mb-1 ${done ? 'line-through text-dt-text/40' : 'text-white'}`}>
                  {step.title}
                </div>
                <div className="text-xs text-dt-text/60">{step.instruction}</div>

                {step.command && !done && (
                  <div className="mt-2 flex items-center gap-2 bg-black/40 rounded px-3 py-1.5 font-mono text-xs text-green-300 border border-green-900/30">
                    <Terminal size={11} className="shrink-0 text-green-500" />
                    <span className="overflow-x-auto whitespace-nowrap">{step.command}</span>
                  </div>
                )}

                <div className="mt-1.5 text-xs text-dt-text/40 italic">
                  Expected: {step.expected_outcome}
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
