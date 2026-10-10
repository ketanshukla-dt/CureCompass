import { useState } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Copy, Check, Download, RotateCcw, AlertTriangle, Clock } from 'lucide-react'

const RISK_CONFIG = {
  low:    { cls: 'risk-low',    icon: '🟢', label: 'Low Risk' },
  medium: { cls: 'risk-medium', icon: '🟡', label: 'Medium Risk' },
  high:   { cls: 'risk-high',   icon: '🔴', label: 'High Risk' },
}

export default function ScriptViewer({ script, onSelect, isSelected }) {
  const [copied, setCopied] = useState(false)
  const [showRollback, setShowRollback] = useState(false)
  const risk = RISK_CONFIG[script.risk_level] || RISK_CONFIG.medium

  const copyToClipboard = async (text) => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const downloadScript = () => {
    const ext = { bash: 'sh', powershell: 'ps1', kubectl: 'sh', python: 'py' }[script.language] || 'sh'
    const blob = new Blob([script.script], { type: 'text/plain' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${script.title.replace(/\s+/g, '-').toLowerCase()}.${ext}`
    a.click()
  }

  return (
    <div className={`border rounded-xl overflow-hidden transition-all ${
      isSelected ? 'border-dt-blue bg-dt-blue/5' : 'border-dt-border bg-dt-card'
    }`}>
      {/* Header */}
      <div className="p-4 flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <h3 className="text-white font-semibold text-sm">{script.title}</h3>
            <span className={risk.cls}>{risk.icon} {risk.label}</span>
            <span className="text-xs bg-dt-dark border border-dt-border px-2 py-0.5 rounded text-dt-text/60 font-mono">
              {script.language}
            </span>
          </div>
          <p className="text-dt-text/60 text-xs">{script.description}</p>

          {/* Risk reason + downtime */}
          <div className="flex items-center gap-4 mt-2">
            <span className="flex items-center gap-1 text-xs text-dt-text/50">
              <AlertTriangle size={10} />
              {script.risk_reason}
            </span>
            <span className="flex items-center gap-1 text-xs text-dt-text/50">
              <Clock size={10} />
              Downtime: {script.estimated_downtime}
            </span>
          </div>
        </div>

        <button
          onClick={() => onSelect(script.id)}
          className={`shrink-0 text-xs font-semibold px-3 py-1.5 rounded-lg border transition-all ${
            isSelected
              ? 'bg-dt-blue border-dt-blue text-white'
              : 'border-dt-border text-dt-text/60 hover:border-dt-blue hover:text-dt-blue'
          }`}
        >
          {isSelected ? '✓ Selected' : 'Select'}
        </button>
      </div>

      {/* Script */}
      <div className="relative">
        <div className="flex items-center justify-between px-4 py-2 bg-black/30 border-y border-dt-border/50">
          <span className="text-xs text-dt-text/40 font-mono">{script.title.toLowerCase().replace(/\s+/g, '_')}.{
            { bash: 'sh', powershell: 'ps1', kubectl: 'sh', python: 'py' }[script.language]
          }</span>
          <div className="flex items-center gap-2">
            {script.rollback_script && (
              <button
                onClick={() => setShowRollback(!showRollback)}
                className="flex items-center gap-1 text-xs text-dt-text/50 hover:text-yellow-400 transition-colors"
              >
                <RotateCcw size={11} />
                {showRollback ? 'Show Script' : 'Rollback'}
              </button>
            )}
            <button onClick={downloadScript} className="flex items-center gap-1 text-xs text-dt-text/50 hover:text-white transition-colors">
              <Download size={11} />
              Download
            </button>
            <button
              onClick={() => copyToClipboard(showRollback ? script.rollback_script : script.script)}
              className="flex items-center gap-1 text-xs text-dt-text/50 hover:text-white transition-colors"
            >
              {copied ? <Check size={11} className="text-green-400" /> : <Copy size={11} />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
        </div>

        <SyntaxHighlighter
          language={script.language === 'kubectl' ? 'bash' : script.language}
          style={vscDarkPlus}
          customStyle={{
            margin: 0,
            background: '#020810',
            fontSize: '12px',
            maxHeight: '280px',
            overflow: 'auto',
          }}
        >
          {showRollback ? (script.rollback_script || '') : script.script}
        </SyntaxHighlighter>
      </div>
    </div>
  )
}
