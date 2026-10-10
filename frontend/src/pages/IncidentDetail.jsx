import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Brain, Zap, CheckCircle2, RefreshCw,
  Target, Shield, AlertTriangle, Clock, Server
} from 'lucide-react'
import SeverityBadge from '../components/SeverityBadge.jsx'
import ScriptViewer from '../components/ScriptViewer.jsx'
import StepGuide from '../components/StepGuide.jsx'
import { fetchIncident, analyzeIncident, resolveIncident, validateResolution } from '../api/client.js'
import { formatDistanceToNow } from 'date-fns'

export default function IncidentDetail() {
  const { id } = useParams()
  const navigate = useNavigate()

  const [incident, setIncident] = useState(null)
  const [loading, setLoading] = useState(true)
  const [analyzing, setAnalyzing] = useState(false)
  const [selectedScript, setSelectedScript] = useState(null)
  const [activeTab, setActiveTab] = useState('analysis') // analysis | scripts | guide
  const [resolving, setResolving] = useState(false)
  const [resolveOutcome, setResolveOutcome] = useState(null)
  const [validation, setValidation] = useState(null)
  const [validating, setValidating] = useState(false)
  const [error, setError] = useState(null)
  const [modalType, setModalType] = useState(null) // 'success' | 'failed' | 'partial' | 'partial-confirmed'
  const [partialFeedback, setPartialFeedback] = useState('')
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false)

  useEffect(() => {
    fetchIncident(id).then(data => {
      setIncident(data)
      if (data.analysis?.scripts?.length) {
        setSelectedScript(data.analysis.scripts[0].id)
      }
    }).catch(err => {
      console.error(err)
      setError('Failed to load incident details.')
    }).finally(() => setLoading(false))
  }, [id])

  const runAnalysis = async () => {
    setAnalyzing(true)
    setError(null)
    try {
      const data = await analyzeIncident(id)
      setIncident(data)
      if (data.analysis?.scripts?.length) {
        setSelectedScript(data.analysis.scripts[0].id)
      }
      setActiveTab('scripts')
    } catch (err) {
      console.error(err)
      setError(err.response?.data?.detail || 'Failed to run SRE AI analysis. Verify your Claude API configuration or server state.')
    } finally {
      setAnalyzing(false)
    }
  }

  const handleResolve = async (outcome, notes = null) => {
    if (!selectedScript) return
    setResolving(true)
    setError(null)
    try {
      const script = incident.analysis.scripts.find(s => s.id === selectedScript)
      await resolveIncident(id, { script_id: script?.title || selectedScript, outcome, notes })
      setResolveOutcome(outcome)
      if (outcome === 'success' || outcome === 'failed') {
        setModalType(outcome)
      }
    } catch (err) {
      console.error(err)
      setError('Failed to record remediation outcome.')
    } finally {
      setResolving(false)
    }
  }

  const handleButtonClick = (outcome) => {
    if (outcome === 'success') {
      handleResolve('success')
    } else if (outcome === 'failed') {
      handleResolve('failed')
    } else if (outcome === 'partial') {
      setModalType('partial')
      setPartialFeedback('')
    }
  }

  const handlePartialSubmit = async () => {
    if (!selectedScript) return
    setIsSubmittingFeedback(true)
    setError(null)
    try {
      const script = incident.analysis.scripts.find(s => s.id === selectedScript)
      await resolveIncident(id, { 
        script_id: script?.title || selectedScript, 
        outcome: 'partial', 
        notes: partialFeedback 
      })
      setResolveOutcome('partial')
      setModalType('partial-confirmed')
    } catch (err) {
      console.error(err)
      setError('Failed to record remediation outcome.')
      setModalType(null)
    } finally {
      setIsSubmittingFeedback(false)
    }
  }

  const handleValidate = async () => {
    setValidating(true)
    setError(null)
    try {
      const result = await validateResolution(id)
      setValidation(result)
    } catch (err) {
      console.error(err)
      setError('Failed to run AI resolution validation.')
    } finally {
      setValidating(false)
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-full text-dt-text/40">
      <RefreshCw size={20} className="spin-slow mr-3" /> Loading incident...
    </div>
  )

  if (!incident) return (
    <div className="p-6 text-dt-text/50">Incident not found.</div>
  )

  const analysis = incident.analysis
  const hasAnalysis = !!analysis

  return (
    <div className="p-6 max-w-5xl">
      {/* Back */}
      <button onClick={() => navigate('/')} className="flex items-center gap-1.5 text-dt-text/50 hover:text-white text-sm mb-5 transition-colors">
        <ArrowLeft size={14} /> Back to Incidents
      </button>

      {error && (
        <div className="card border-red-800/50 bg-red-900/10 text-red-400 text-sm mb-5 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-400 hover:text-white font-bold px-2 text-lg">×</button>
        </div>
      )}

      {/* Incident header */}
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
                <Clock size={11} />
                {formatDistanceToNow(new Date(incident.start_time), { addSuffix: true })}
              </span>
              <span className="flex items-center gap-1">
                <Clock size={11} />
                {incident.duration_minutes}m open
              </span>
              <span className="flex items-center gap-1">
                <Server size={11} />
                {incident.impact_count} affected
              </span>
            </div>
          </div>

          {!hasAnalysis && (
            <button
              onClick={runAnalysis}
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

      {/* Analyzing spinner */}
      {analyzing && (
        <div className="card mb-5 flex items-center gap-4 border-dt-blue/30 bg-dt-blue/5">
          <RefreshCw size={20} className="spin-slow text-dt-blue shrink-0" />
          <div>
            <div className="text-white font-semibold text-sm">Claude is analyzing this incident...</div>
            <div className="text-dt-text/50 text-xs mt-0.5">
              Reading Davis AI data → Identifying fix → Generating scripts → Writing execution guide
            </div>
          </div>
        </div>
      )}

      {/* Analysis results */}
      {hasAnalysis && (
        <>
          {/* Tabs */}
          <div className="flex gap-1 mb-4 border-b border-dt-border">
            {[
              { key: 'analysis', label: 'AI Analysis', icon: Brain },
              { key: 'scripts',  label: `Scripts (${analysis.scripts.length})`, icon: Zap },
              { key: 'guide',    label: 'Execution Guide', icon: Target },
            ].map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
                  activeTab === key
                    ? 'border-dt-blue text-dt-blue'
                    : 'border-transparent text-dt-text/50 hover:text-white'
                }`}
              >
                <Icon size={13} /> {label}
              </button>
            ))}
          </div>

          {/* ── Tab: Analysis ── */}
          {activeTab === 'analysis' && (
            <div className="space-y-4">
              {/* Confidence + recommended action */}
              <div className="card border-dt-blue/30 bg-dt-blue/5">
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div className="flex items-center gap-2">
                    <Brain size={16} className="text-dt-blue" />
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
                  <AlertTriangle size={14} className="text-orange-400" />
                  <span className="text-white text-sm font-semibold">Current Impact</span>
                </div>
                <p className="text-dt-text/70 text-sm">{analysis.impact_summary}</p>
              </div>

              {/* Post-fix checks */}
              <div className="card">
                <div className="flex items-center gap-2 mb-3">
                  <Shield size={14} className="text-green-400" />
                  <span className="text-white text-sm font-semibold">Post-Fix Validation Checklist</span>
                </div>
                <ul className="space-y-2">
                  {analysis.post_fix_checks.map((c, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-dt-text/70">
                      <CheckCircle2 size={13} className="text-green-400/50 mt-0.5 shrink-0" />
                      {c}
                    </li>
                  ))}
                </ul>
              </div>

              <button onClick={() => setActiveTab('scripts')} className="btn-primary w-full flex items-center justify-center gap-2">
                <Zap size={14} /> View Remediation Scripts
              </button>
            </div>
          )}

          {/* ── Tab: Scripts ── */}
          {activeTab === 'scripts' && (
            <div className="space-y-4">
              <p className="text-dt-text/50 text-sm">
                Select a script, review it carefully, then use the Execution Guide tab to run it safely.
              </p>
              {analysis.scripts.map(script => (
                <ScriptViewer
                  key={script.id}
                  script={script}
                  isSelected={selectedScript === script.id}
                  onSelect={setSelectedScript}
                />
              ))}
              {selectedScript && (
                <button onClick={() => setActiveTab('guide')} className="btn-primary w-full flex items-center justify-center gap-2">
                  <Target size={14} /> Open Execution Guide
                </button>
              )}
            </div>
          )}

          {/* ── Tab: Guide ── */}
          {activeTab === 'guide' && (
            <div className="space-y-5">
              {!selectedScript ? (
                <div className="card text-center py-8 text-dt-text/50 text-sm">
                  Please select a script first from the Scripts tab.
                </div>
              ) : (
                <>
                  <div className="card">
                    <div className="flex items-center gap-2 mb-4">
                      <Target size={15} className="text-dt-blue" />
                      <span className="text-white font-semibold">Step-by-Step Execution Guide</span>
                    </div>
                    <StepGuide steps={analysis.execution_steps} />
                  </div>

                  {/* Mark outcome */}
                  {!resolveOutcome && !validation && (
                    <div className="card border-green-800/40 bg-green-900/5">
                      <div className="text-white font-semibold text-sm mb-3">How did it go?</div>
                      <div className="flex gap-3">
                        {['success', 'partial', 'failed'].map(o => (
                          <button
                            key={o}
                            disabled={resolving}
                            onClick={() => handleButtonClick(o)}
                            className={`flex-1 py-2 rounded-lg text-sm font-semibold border transition-colors ${
                              o === 'success' ? 'border-green-700 text-green-400 hover:bg-green-900/30' :
                              o === 'partial' ? 'border-yellow-700 text-yellow-400 hover:bg-yellow-900/30' :
                              'border-red-700 text-red-400 hover:bg-red-900/30'
                            }`}
                          >
                            {o === 'success' ? '✅ Worked' : o === 'partial' ? '⚠️ Partial' : '❌ Failed'}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {resolveOutcome && !validation && (
                    <div className="card">
                      <div className="text-white font-semibold text-sm mb-2">Outcome recorded: <span className="text-dt-blue">{resolveOutcome}</span></div>
                      <button
                        onClick={handleValidate}
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

                  {validation && (
                    <div className={`card border ${
                      validation.recovery_confirmed ? 'border-green-700/50 bg-green-900/10' : 'border-yellow-700/50 bg-yellow-900/10'
                    }`}>
                      <div className="flex items-center gap-2 mb-2">
                        {validation.recovery_confirmed
                          ? <CheckCircle2 size={16} className="text-green-400" />
                          : <AlertTriangle size={16} className="text-yellow-400" />
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
                              <span className="text-dt-blue/60">→</span> {c}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </>
      )}

      {/* Outcome Feedback Modal */}
      {modalType && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="card max-w-md w-full border border-dt-border bg-dt-dark p-6 rounded-2xl shadow-2xl animate-fade-in text-white">
            
            {modalType === 'success' && (
              <div className="text-center space-y-4">
                <div className="w-12 h-12 bg-green-500/20 text-green-400 rounded-full flex items-center justify-center mx-auto text-2xl font-bold">
                  ✓
                </div>
                <h3 className="text-lg font-bold">Remediation Logged</h3>
                <p className="text-dt-text/70 text-sm">Thanks!</p>
                <button
                  onClick={() => setModalType(null)}
                  className="btn-primary w-full py-2 font-semibold"
                >
                  OK
                </button>
              </div>
            )}

            {modalType === 'failed' && (
              <div className="text-center space-y-4">
                <div className="w-12 h-12 bg-red-500/20 text-red-400 rounded-full flex items-center justify-center mx-auto text-2xl font-bold">
                  ✗
                </div>
                <h3 className="text-lg font-bold">Remediation Logged</h3>
                <p className="text-dt-text/70 text-sm">
                  Ok, we will feed this to train our model.
                </p>
                <div className="flex flex-col gap-2 pt-2">
                  <a
                    href="https://support.dynatrace.com"
                    target="_blank"
                    rel="noreferrer"
                    className="btn-primary w-full py-2 font-semibold block text-center"
                  >
                    Raise Support Ticket
                  </a>
                  <button
                    onClick={() => setModalType(null)}
                    className="btn-ghost w-full py-2 font-semibold text-dt-text/60 hover:text-white"
                  >
                    Close
                  </button>
                </div>
              </div>
            )}

            {modalType === 'partial' && (
              <div className="space-y-4">
                <h3 className="text-lg font-bold flex items-center gap-2">
                  <span className="text-yellow-400">⚠️</span> Describe Partial Success
                </h3>
                <p className="text-dt-text/70 text-sm">
                  We have logged the partial recovery. To help train our remediation advisor, please describe what worked:
                </p>
                <textarea
                  className="w-full bg-dt-dark border border-dt-border rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-dt-blue"
                  rows="4"
                  placeholder="e.g. The service restarted and database connectivity was restored, but memory footprint remains elevated..."
                  value={partialFeedback}
                  onChange={(e) => setPartialFeedback(e.target.value)}
                />
                <div className="flex gap-3 pt-2">
                  <button
                    onClick={() => setModalType(null)}
                    className="btn-ghost flex-1 py-2 font-semibold text-dt-text/60 hover:text-white"
                    disabled={isSubmittingFeedback}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handlePartialSubmit}
                    className="btn-primary flex-1 py-2 font-semibold"
                    disabled={isSubmittingFeedback || !partialFeedback.trim()}
                  >
                    {isSubmittingFeedback ? 'Saving...' : 'Submit'}
                  </button>
                </div>
              </div>
            )}

            {modalType === 'partial-confirmed' && (
              <div className="text-center space-y-4">
                <div className="w-12 h-12 bg-yellow-500/20 text-yellow-400 rounded-full flex items-center justify-center mx-auto text-2xl font-bold">
                  ✓
                </div>
                <h3 className="text-lg font-bold">Feedback Saved</h3>
                <p className="text-dt-text/70 text-sm">
                  Thanks for your feedback! This data has been recorded to train our platform.
                </p>
                <button
                  onClick={() => setModalType(null)}
                  className="btn-primary w-full py-2 font-semibold"
                >
                  OK
                </button>
              </div>
            )}

          </div>
        </div>
      )}
    </div>
  )
}
