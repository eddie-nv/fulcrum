export type StrategyStatus = 'pending' | 'running' | 'passed' | 'failed'

export interface BranchNode {
  id: string
  parent_id: string | null
  level: number
  strategy: string
  status: StrategyStatus
  error_signature: string | null
}

export interface BranchTree {
  session_id: string
  nodes: BranchNode[]
}

export interface FeatureCard {
  session_id: string
  container_id: string
  status: string
  levels_tried: number
  winning_strategy: string | null
  error_signatures: string[]
  hypothesis: string | null
  open_blockers: string[]
  room_id: string | null
}
