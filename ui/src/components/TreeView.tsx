import type { BranchTree, BranchNode } from '../types'
import NodeCard from './NodeCard'

interface Props {
  tree: BranchTree
}

export default function TreeView({ tree }: Props) {
  const levels = new Map<number, BranchNode[]>()
  for (const node of tree.nodes) {
    const bucket = levels.get(node.level) ?? []
    bucket.push(node)
    levels.set(node.level, bucket)
  }
  const sortedLevels = [...levels.keys()].sort((a, b) => a - b)

  if (tree.nodes.length === 0) {
    return (
      <div style={{ textAlign: 'center', color: '#475569', fontSize: 14, padding: '60px 0' }}>
        Waiting for remediation probes…
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 40, alignItems: 'center' }}>
      {sortedLevels.map((level, i) => (
        <div key={level} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 }}>
          {i > 0 && (
            <div style={{ width: 2, height: 24, background: '#334155', flexShrink: 0 }} />
          )}
          <div style={{
            fontSize: 10,
            color: '#64748b',
            textTransform: 'uppercase',
            letterSpacing: 1.5,
            marginBottom: 4,
          }}>
            Level {level}
          </div>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', justifyContent: 'center' }}>
            {levels.get(level)!.map(node => (
              <NodeCard key={node.id} node={node} />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
