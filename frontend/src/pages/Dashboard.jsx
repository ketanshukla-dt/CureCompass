import { useState, useEffect } from 'react'
import { Activity, RefreshCw, AlertTriangle, CheckCircle2, Brain } from 'lucide-react'
import IncidentCard from '../components/IncidentCard.jsx'
import { fetchIncidents } from '../api/client.js'
import { getErrorMessage } from '../utils/errors.js'

const SEVERITY_ORDER = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 }

export default function Dashboard() {
  const [incidents, setIncidents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState('ALL')

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchIncidents()
      data.sort((a, b) =>
        (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9)
      )
      setIncidents(data)
    } catch (e) {
      setError(getErrorMessage(e, 'Failed to load incidents. Check your Dynatrace connection.'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const filtered = filter === 'ALL'
    ? incidents
    : incidents.filter(i => i.severity === filter)

  const stats = {
    critical: incidents.filter(i => i.severity === 'CRITICAL').length,
    high:     incidents.filter(i => i.severity === 'HIGH').length,
    ready:    incidents.filter(i => i.status === 'REMEDIATION_READY').length,
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Activity size={20} className="text-dt-blue" />
            Active Incidents
          </h1>
          <p className="text-dt-text/50 text-sm mt-0.5">
            Davis AI detects · Claude recommends · You decide
          </p>
        </div>
        <button onClick={load} className="btn-ghost flex items-center gap-2">
          <RefreshCw size={14} className={loading ? 'spin-slow' : ''} />
          Refresh
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="card flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-red-900/40 flex items-center justify-center">
            <AlertTriangle size={16} className="text-red-400" />
          </div>
          <div>
            <div className="text-2xl font-bold text-white">{stats.critical}</div>
            <div className="text-xs text-dt-text/50">Critical</div>
          </div>
        </div>
        <div className="card flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-orange-900/40 flex items-center justify-center">
            <AlertTriangle size={16} className="text-orange-400" />
          </div>
          <div>
            <div className="text-2xl font-bold text-white">{stats.high}</div>
            <div className="text-xs text-dt-text/50">High Severity</div>
          </div>
        </div>
        <div className="card flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-dt-blue/20 flex items-center justify-center">
            <Brain size={16} className="text-dt-blue" />
          </div>
          <div>
            <div className="text-2xl font-bold text-white">{stats.ready}</div>
            <div className="text-xs text-dt-text/50">Fix Ready (AI)</div>
          </div>
        </div>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2 mb-4">
        {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            aria-pressed={filter === f}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
              filter === f
                ? 'bg-dt-blue border-dt-blue text-white font-semibold'
                : 'border-dt-border text-dt-text/50 hover:border-dt-blue/50'
            }`}
          >
            {f}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-dt-text/40" role="status" aria-live="polite">
          <RefreshCw size={20} className="spin-slow mr-3" aria-hidden="true" />
          Loading incidents from Dynatrace...
        </div>
      ) : error ? (
        <div role="alert" className="card border-red-800/50 bg-red-900/10 text-red-400 text-sm text-center py-8">
          {error}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card text-center py-12">
          <CheckCircle2 size={32} className="text-green-400 mx-auto mb-3" />
          <div className="text-white font-semibold">All clear</div>
          <div className="text-dt-text/50 text-sm mt-1">No incidents matching this filter</div>
        </div>
      ) : (
        <div className="grid gap-3">
          {filtered.map(i => <IncidentCard key={i.id} incident={i} />)}
        </div>
      )}
    </div>
  )
}
