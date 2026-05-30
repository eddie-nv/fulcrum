import type { BranchNode } from '../types'

const STATUS_COLORS: Record<string, string> = {
  pending: '#6b7280',
  running: '#f59e0b',
  passed: '#10b981',
  failed: '#ef4444',
}

interface Props {
  node: BranchNode
}

export default function NodeCard({ node }: Props) {
  const color = STATUS_COLORS[node.status] ?? '#6b7280'
  return (
    <div
      title={node.error_signature ?? undefined}
      style={{
        border: `2px solid ${color}`,
        borderRadius: 8,
        padding: '10px 14px',
        background: `${color}1a`,
        minWidth: 150,
        maxWidth: 200,
        cursor: node.error_signature ? 'help' : 'default',
        transition: 'opacity 0.2s',
      }}
    >
      <div style={{ fontWeight: 700, fontSize: 11, color, letterSpacing: 0.5 }}>
        {node.status.toUpperCase()}
      </div>
      <div style={{ fontSize: 12, marginTop: 4, color: '#cbd5e1', wordBreak: 'break-word' }}>
        {node.strategy}
      </div>
      {node.error_signature && (
        <div style={{ fontSize: 10, marginTop: 6, color: '#64748b', fontFamily: 'monospace' }}>
          {node.error_signature.length > 50
            ? node.error_signature.slice(0, 50) + '…'
            : node.error_signature}
        </div>
      )}
    </div>
  )
}
