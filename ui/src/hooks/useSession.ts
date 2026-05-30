import { useState, useEffect, useRef } from 'react'
import type { BranchTree, FeatureCard } from '../types'

const TERMINAL = new Set(['resolved', 'blocked', 'failed'])

export function useSession(sessionId: string) {
  const [tree, setTree] = useState<BranchTree | null>(null)
  const [card, setCard] = useState<FeatureCard | null>(null)
  const [error, setError] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!sessionId) return

    let active = true

    const poll = async () => {
      try {
        const [treeRes, cardRes] = await Promise.all([
          fetch(`/tree/${sessionId}`),
          fetch(`/card/${sessionId}`),
        ])
        if (!active) return
        if (!treeRes.ok || !cardRes.ok) {
          setError('Session not found')
          return
        }
        const treeData: BranchTree = await treeRes.json()
        const cardData: FeatureCard = await cardRes.json()
        setTree(treeData)
        setCard(cardData)
        setError(null)

        if (!TERMINAL.has(cardData.status) && active) {
          timerRef.current = setTimeout(poll, 2000)
        }
      } catch {
        if (active) setError('Failed to reach Fulcrum API')
      }
    }

    poll()
    return () => {
      active = false
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [sessionId])

  return { tree, card, error }
}
