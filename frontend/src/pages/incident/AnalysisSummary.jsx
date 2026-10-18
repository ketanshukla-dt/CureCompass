import { Brain, Zap, CheckCircle2, Shield, AlertTriangle } from 'lucide-react'

export default function AnalysisSummary({ analysis, onViewScripts }) {
  return (
    <div className="space-y-4">
      {/* Confidence + recommended action */}
      <div className="card border-dt-blue/30 bg-dt-blue/5">
        <div className="flex items-start justify-between gap-4 mb-3">
          <div className="flex items-center gap-2">
            <Brain size={16} className="text-dt-blue" aria-hidden="true" />
            <span className="text-dt-blue font-semibold text-sm">Claude's Recommendation</span>
          </div>
          <div className="text-right">
            <div className="text-white font-bold text-lg">{analysis.confidence}%</div>
            <div className="text-xs text-dt-text/40">confidence</div>
          </div>
        </div>
        <div className="text-white font-semibold mb-2">{analysis.recommended_action}</div>
        <div className="h-1.5 bg-dt-dark rounded-full mb-3">
          <div className="h-1.5 bg-dt-blue rounded-full" style={{ width: `${analysis.confidence}%` }} />
        </div>
        <p className="text-dt-text/70 text-sm">{analysis.root_cause}</p>
      </div>

      {/* Impact */}
      <div className="card">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle size={14} className="text-orange-400" aria-hidden="true" />
          <span className="text-white text-sm font-semibold">Current Impact</span>
        </div>
        <p className="text-dt-text/70 text-sm">{analysis.impact_summary}</p>
      </div>

      {/* Post-fix checks */}
      <div className="card">
        <div className="flex items-center gap-2 mb-3">
          <Shield size={14} className="text-green-400" aria-hidden="true" />
          <span className="text-white text-sm font-semibold">Post-Fix Validation Checklist</span>
        </div>
        <ul className="space-y-2">
          {analysis.post_fix_checks.map((c, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-dt-text/70">
              <CheckCircle2 size={13} className="text-green-400/50 mt-0.5 shrink-0" aria-hidden="true" />
              {c}
            </li>
          ))}
        </ul>
      </div>

      <button onClick={onViewScripts} className="btn-primary w-full flex items-center justify-center gap-2">
        <Zap size={14} /> View Remediation Scripts
      </button>
    </div>
  )
}
