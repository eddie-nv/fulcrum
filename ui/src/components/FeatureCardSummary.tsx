import type { FeatureCard } from '../types'

const STATUS_COLOR: Record<string, string> = {
  resolved: '#10b981',
  blocked: '#f59e0b',
  failed: '#ef4444',
  investigating: '#3b82f6',
}

interface Props {
  card: FeatureCard
}

export default function FeatureCardSummary({ card }: Props) {
  const color = STATUS_COLOR[card.status] ?? '#6b7280'
  return (
    <div style={{
      border: `2px solid ${color}`,
      borderRadius: 12,
      padding: '20px 24px',
      maxWidth: 520,
      width: '100%',
      background: `${color}0d`,
    }}>
      <div style={{ fontWeight: 800, fontSize: 18, color }}>
        {card.status.toUpperCase()}
        {card.winning_strategy && (
          <span style={{ fontWeight: 400, color: '#94a3b8', fontSize: 14, marginLeft: 10 }}>
            via {card.winning_strategy}
          </span>
        )}
      </div>

      {card.hypothesis && (
        <div style={{ marginTop: 12, fontSize: 13, color: '#cbd5e1', lineHeight: 1.5 }}>
          <span style={{ color: '#64748b', fontWeight: 600 }}>Hypothesis: </span>
          {card.hypothesis}
        </div>
      )}

      {card.error_signatures.length > 0 && (
        <div style={{ marginTop: 10, fontSize: 12, color: '#64748b' }}>
          <span style={{ fontWeight: 600 }}>Error signatures: </span>
          {card.error_signatures.join(', ')}
        </div>
      )}

      {card.open_blockers.length > 0 && (
        <div style={{ marginTop: 10, fontSize: 12, color: '#f87171' }}>
          <span style={{ fontWeight: 600 }}>Blockers: </span>
          {card.open_blockers.join(', ')}
        </div>
      )}

      <div style={{ marginTop: 12, fontSize: 11, color: '#475569' }}>
        Levels tried: {card.levels_tried} &nbsp;·&nbsp; Container: {card.container_id}
      </div>
    </div>
  )
}
