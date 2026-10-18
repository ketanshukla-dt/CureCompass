import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Brain, Zap, RefreshCw, Target } from 'lucide-react'
import ScriptViewer from '../components/ScriptViewer.jsx'
import StepGuide from '../components/StepGuide.jsx'
import IncidentHeader from './incident/IncidentHeader.jsx'
import AnalysisSummary from './incident/AnalysisSummary.jsx'
import ResolutionPanel from './incident/ResolutionPanel.jsx'
import OutcomeModal from './incident/OutcomeModal.jsx'
import { fetchIncident, analyzeIncident, resolveIncident, validateResolution } from '../api/client.js'
import { getErrorMessage } from '../utils/errors.js'

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

  useEffect(() => {
    let ignore = false
    setLoading(true)
    setError(null)
    fetchIncident(id).then(data => {
      if (ignore) return
      setIncident(data)
      if (data.analysis?.scripts?.length) {
        setSelectedScript(data.analysis.scripts[0].id)
      }
    }).catch(err => {
      if (ignore) return
      setError(getErrorMessage(err, 'Failed to load incident details.'))
    }).finally(() => {
      if (!ignore) setLoading(false)
    })
    return () => { ignore = true }
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
      setError(getErrorMessage(err, 'Failed to run SRE AI analysis. Verify your Claude API configuration or server state.'))
    } finally {
      setAnalyzing(false)
    }
  }

  // Records the outcome; returns true on success.
  const recordOutcome = async (outcome, notes = null) => {
    if (!selectedScript || resolving || resolveOutcome) return false
    setResolving(true)
    setError(null)
    try {
      const script = incident.analysis.scripts.find(s => s.id === selectedScript)
      await resolveIncident(id, { script_id: script?.title || selectedScript, outcome, notes })
      setResolveOutcome(outcome)
      return true
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to record remediation outcome.'))
      return false
    } finally {
      setResolving(false)
    }
  }

  const handleOutcomeClick = async (outcome) => {
    if (outcome === 'partial') {
      setPartialFeedback('')
      setModalType('partial')
      return
    }
    if (!window.confirm(`Record this remediation as "${outcome}"? This cannot be undone.`)) return
    if (await recordOutcome(outcome)) setModalType(outcome)
  }

  const handlePartialSubmit = async () => {
    const ok = await recordOutcome('partial', partialFeedback)
    setModalType(ok ? 'partial-confirmed' : null)
  }

  const handleValidate = async () => {
    setValidating(true)
    setError(null)
    try {
      setValidation(await validateResolution(id))
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to run AI resolution validation.'))
    } finally {
      setValidating(false)
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-full text-dt-text/40" role="status" aria-live="polite">
      <RefreshCw size={20} className="spin-slow mr-3" aria-hidden="true" /> Loading incident...
    </div>
  )

  if (!incident) return (
    <div className="p-6 text-dt-text/50" role={error ? 'alert' : undefined}>
      {error || 'Incident not found.'}
    </div>
  )

  const analysis = incident.analysis
  const hasAnalysis = !!analysis
  const tabs = hasAnalysis ? [
    { key: 'analysis', label: 'AI Analysis', icon: Brain },
    { key: 'scripts',  label: `Scripts (${analysis.scripts.length})`, icon: Zap },
    { key: 'guide',    label: 'Execution Guide', icon: Target },
  ] : []

  return (
    <div className="p-6 max-w-5xl">
      <button onClick={() => navigate('/')} className="flex items-center gap-1.5 text-dt-text/50 hover:text-white text-sm mb-5 transition-colors">
        <ArrowLeft size={14} aria-hidden="true" /> Back to Incidents
      </button>

      {error && (
        <div role="alert" className="card border-red-800/50 bg-red-900/10 text-red-400 text-sm mb-5 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} aria-label="Dismiss error" className="text-red-400 hover:text-white font-bold px-2 text-lg">×</button>
        </div>
      )}

      <IncidentHeader
        incident={incident}
        hasAnalysis={hasAnalysis}
        analyzing={analyzing}
        onAnalyze={runAnalysis}
      />

      {analyzing && (
        <div className="card mb-5 flex items-center gap-4 border-dt-blue/30 bg-dt-blue/5" role="status" aria-live="polite">
          <RefreshCw size={20} className="spin-slow text-dt-blue shrink-0" aria-hidden="true" />
          <div>
            <div className="text-white font-semibold text-sm">Claude is analyzing this incident...</div>
            <div className="text-dt-text/50 text-xs mt-0.5">
              Reading Davis AI data → Identifying fix → Generating scripts → Writing execution guide
            </div>
          </div>
        </div>
      )}

      {hasAnalysis && (
        <>
          <div role="tablist" aria-label="Incident analysis" className="flex gap-1 mb-4 border-b border-dt-border">
            {tabs.map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                role="tab"
                aria-selected={activeTab === key}
                onClick={() => setActiveTab(key)}
                className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
                  activeTab === key
                    ? 'border-dt-blue text-dt-blue'
                    : 'border-transparent text-dt-text/50 hover:text-white'
                }`}
              >
                <Icon size={13} aria-hidden="true" /> {label}
              </button>
            ))}
          </div>

          <div role="tabpanel">
            {activeTab === 'analysis' && (
              <AnalysisSummary analysis={analysis} onViewScripts={() => setActiveTab('scripts')} />
            )}

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
                        <Target size={15} className="text-dt-blue" aria-hidden="true" />
                        <span className="text-white font-semibold">Step-by-Step Execution Guide</span>
                      </div>
                      <StepGuide steps={analysis.execution_steps} />
                    </div>
                    <ResolutionPanel
                      outcome={resolveOutcome}
                      validation={validation}
                      busy={resolving || !!resolveOutcome}
                      validating={validating}
                      onOutcome={handleOutcomeClick}
                      onValidate={handleValidate}
                    />
                  </>
                )}
              </div>
            )}
          </div>
        </>
      )}

      {modalType && (
        <OutcomeModal
          type={modalType}
          feedback={partialFeedback}
          submitting={resolving}
          onFeedbackChange={setPartialFeedback}
          onSubmit={handlePartialSubmit}
          onClose={() => setModalType(null)}
        />
      )}
    </div>
  )
}
