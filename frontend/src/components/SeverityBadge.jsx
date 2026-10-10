export default function SeverityBadge({ severity }) {
  const cls = {
    CRITICAL: 'badge-critical',
    HIGH:     'badge-high',
    MEDIUM:   'badge-medium',
    LOW:      'badge-low',
  }[severity] || 'badge-low'

  return <span className={cls}>{severity}</span>
}
