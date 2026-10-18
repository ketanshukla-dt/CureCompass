import { useState, useEffect, useCallback } from 'react'
import { History, TrendingUp, CheckCircle2, AlertTriangle, XCircle } from 'lucide-react'
import { fetchHistory, fetchHistoryStats } from '../api/client.js'
import { formatDistanceToNow } from 'date-fns'
import { getErrorMessage } from '../utils/errors.js'

const OUTCOME_CONFIG = {
  success: { icon: CheckCircle2, cls: 'text-green-400', bg: 'bg-green-900/20 border-green-800/40', label: 'Resolved' },
  partial: { icon: AlertTriangle, cls: 'text-yellow-400', bg: 'bg-yellow-900/20 border-yellow-800/40', label: 'Partial' },
  failed:  { icon: XCircle,      cls: 'text-red-400',   bg: 'bg-red-900/20 border-red-800/40',    label: 'Failed' },
}

export default function HistoryPage() {
  const [history, setHistory] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [h, s] = await Promise.all([fetchHistory(), fetchHistoryStats()])
      setHistory(h)
      setStats(s)
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to load remediation history.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  if (loading) return (
    <div className="flex items-center justify-center h-full text-dt-text/40 text-sm" role="status" aria-live="polite">
      Loading history...
    </div>
  )

  if (error) return (
    <div className="p-6 max-w-4xl">
      <div role="alert" className="card border-red-800/50 bg-red-900/10 text-red-400 text-sm text-center py-8">
        <p className="mb-4">{error}</p>
        <button onClick={load} className="btn-ghost">Retry</button>
      </div>
    </div>
  )

  return (
    <div className="p-6 max-w-4xl">
      <div className="flex items-center gap-2 mb-6">
        <History size={20} className="text-dt-blue" />
        <h1 className="text-xl font-bold text-white">Remediation History</h1>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          {[
            { label: 'Total Fixes', value: stats.total, cls: 'text-white' },
            { label: 'Successful', value: stats.success, cls: 'text-green-400' },
            { label: 'Partial', value: stats.partial, cls: 'text-yellow-400' },
            { label: 'Avg Resolution', value: `${stats.avg_resolution_minutes}m`, cls: 'text-dt-blue' },
          ].map(({ label, value, cls }) => (
            <div key={label} className="card text-center">
              <div className={`text-2xl font-bold ${cls}`}>{value}</div>
              <div className="text-xs text-dt-text/50 mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* History list */}
      {history.length === 0 ? (
        <div className="card text-center py-12 text-dt-text/50 text-sm">
          No remediation history yet. Resolve your first incident to see it here.
        </div>
      ) : (
        <div className="space-y-3">
          {history.map(record => {
            const cfg = OUTCOME_CONFIG[record.outcome] || OUTCOME_CONFIG.partial
            const Icon = cfg.icon
            return (
              <div key={record.id} className={`card border ${cfg.bg}`}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Icon size={14} className={cfg.cls} />
                      <span className={`text-xs font-semibold ${cfg.cls}`}>{cfg.label}</span>
                      <span className="text-xs text-dt-text/30">·</span>
                      <span className="text-xs text-dt-text/40">
                        {formatDistanceToNow(new Date(record.resolved_at), { addSuffix: true })}
                      </span>
                    </div>
                    <div className="text-white text-sm font-medium mb-0.5 truncate">{record.incident_title}</div>
                    <div className="text-dt-text/50 text-xs">Script: {record.script_title}</div>
                    {record.notes && (
                      <div className="text-dt-text/40 text-xs mt-1 italic">"{record.notes}"</div>
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-white font-semibold text-sm">{record.duration_minutes}m</div>
                    <div className="text-xs text-dt-text/40">to resolve</div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
