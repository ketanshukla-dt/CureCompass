import { Brain, RefreshCw, Clock, Server } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import SeverityBadge from '../../components/SeverityBadge.jsx'
import { formatDuration } from '../../utils/format.js'

export default function IncidentHeader({ incident, hasAnalysis, analyzing, onAnalyze }) {
  return (
    <div className="card mb-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <SeverityBadge severity={incident.severity} />
            <span className="text-xs text-dt-text/50">{incident.id}</span>
          </div>
          <h1 className="text-xl font-bold text-white mb-3">{incident.title}</h1>
          <div className="flex items-center gap-5 text-xs text-dt-text/50">
            <span className="flex items-center gap-1">
              <Clock size={11} aria-hidden="true" />
              {formatDistanceToNow(new Date(incident.start_time), { addSuffix: true })}
            </span>
            <span className="flex items-center gap-1">
              <Clock size={11} aria-hidden="true" />
              {formatDuration(incident.duration_minutes)} open
            </span>
            <span className="flex items-center gap-1">
              <Server size={11} aria-hidden="true" />
              {incident.impact_count} affected
            </span>
          </div>
        </div>

        {!hasAnalysis && (
          <button
            onClick={onAnalyze}
            disabled={analyzing}
            className="btn-primary flex items-center gap-2 shrink-0 pulse-glow"
          >
            {analyzing
              ? <><RefreshCw size={14} className="spin-slow" /> Analyzing...</>
              : <><Brain size={14} /> Analyze with AI</>
            }
          </button>
        )}
      </div>

      {/* Affected entities */}
      <div className="mt-4 pt-4 border-t border-dt-border/50">
        <div className="text-xs text-dt-text/40 mb-2">AFFECTED ENTITIES</div>
        <div className="flex flex-wrap gap-2">
          {incident.affected_entities.map(e => (
            <span key={e.entity_id} className="text-xs bg-dt-dark border border-dt-border px-2.5 py-1 rounded-lg text-dt-text/70">
              {e.entity_name}
              <span className="ml-1.5 text-dt-text/30">{e.entity_type}</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}
