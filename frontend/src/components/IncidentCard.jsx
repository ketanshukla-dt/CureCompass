import { useNavigate } from 'react-router-dom'
import { Clock, Server, ChevronRight, Brain } from 'lucide-react'
import SeverityBadge from './SeverityBadge.jsx'
import { formatDistanceToNow } from 'date-fns'

const TYPE_LABELS = {
  cpu_memory:          '⚡ CPU / Memory',
  service_crash:       '💥 Service Crash',
  db_slowness:         '🗄️ Database',
  deployment_rollback: '🔄 Deployment',
  monitoring_gap:      '📡 Monitoring',
}

export default function IncidentCard({ incident }) {
  const navigate = useNavigate()
  const startTime = new Date(incident.start_time)
  const hasAnalysis = incident.status === 'REMEDIATION_READY'

  return (
    <div
      onClick={() => navigate(`/incidents/${incident.id}`)}
      className="card cursor-pointer hover:border-dt-blue transition-all group"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          {/* Type + Severity */}
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs text-dt-text/50 font-medium">
              {TYPE_LABELS[incident.incident_type] || incident.incident_type}
            </span>
            <SeverityBadge severity={incident.severity} />
            {hasAnalysis && (
              <span className="flex items-center gap-1 bg-dt-blue/20 text-dt-blue border border-dt-blue/30 text-xs px-2 py-0.5 rounded">
                <Brain size={10} />
                Fix Ready
              </span>
            )}
          </div>

          {/* Title */}
          <h3 className="text-white font-semibold text-sm mb-3 group-hover:text-dt-blue transition-colors line-clamp-2">
            {incident.title}
          </h3>

          {/* Meta */}
          <div className="flex items-center gap-4 text-xs text-dt-text/50">
            <span className="flex items-center gap-1">
              <Clock size={11} />
              {formatDistanceToNow(startTime, { addSuffix: true })}
            </span>
            <span className="flex items-center gap-1">
              <Server size={11} />
              {incident.impact_count} {incident.impact_count === 1 ? 'entity' : 'entities'}
            </span>
            <span>{incident.duration_minutes}m open</span>
          </div>
        </div>

        <ChevronRight size={16} className="text-dt-text/30 group-hover:text-dt-blue mt-1 shrink-0 transition-colors" />
      </div>

      {/* Affected entities */}
      {incident.affected_entities?.length > 0 && (
        <div className="mt-3 pt-3 border-t border-dt-border/50 flex gap-2 flex-wrap">
          {incident.affected_entities.slice(0, 3).map(e => (
            <span key={e.entity_id} className="text-xs bg-dt-dark px-2 py-0.5 rounded text-dt-text/60 border border-dt-border/50">
              {e.entity_name}
            </span>
          ))}
          {incident.affected_entities.length > 3 && (
            <span className="text-xs text-dt-text/40">+{incident.affected_entities.length - 3} more</span>
          )}
        </div>
      )}
    </div>
  )
}
