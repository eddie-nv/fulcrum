import { useState } from 'react'
import { useSession } from './hooks/useSession'
import TreeView from './components/TreeView'
import FeatureCardSummary from './components/FeatureCardSummary'

const TERMINAL = new Set(['resolved', 'blocked', 'failed'])

export default function App() {
  const params = new URLSearchParams(window.location.search)
  const [sessionId, setSessionId] = useState(params.get('session') ?? '')
  const [input, setInput] = useState('')
  const { tree, card, error } = useSession(sessionId)

  const isTerminal = card ? TERMINAL.has(card.status) : false

  if (!sessionId) {
    return (
      <div style={S.center}>
        <div style={S.logo}>Fulcrum</div>
        <p style={S.sub}>Enter a session ID to watch the remediation tree</p>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && input.trim() && setSessionId(input.trim())}
            placeholder="session_id"
            style={S.input}
            autoFocus
          />
          <button
            onClick={() => input.trim() && setSessionId(input.trim())}
            style={S.button}
          >
            Watch
          </button>
        </div>
      </div>
    )
  }

  return (
    <div style={S.page}>
      <header style={S.header}>
        <div style={S.logo}>Fulcrum</div>
        <div style={{ fontSize: 12, color: '#64748b', display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontFamily: 'monospace' }}>{sessionId}</span>
          {!isTerminal && card && (
            <span style={{ color: '#3b82f6' }}>● polling</span>
          )}
          {isTerminal && (
            <span style={{ color: '#10b981' }}>✓ resolved</span>
          )}
          <button
            onClick={() => setSessionId('')}
            style={{ ...S.button, background: 'transparent', color: '#475569', border: '1px solid #334155', padding: '4px 10px', fontSize: 11 }}
          >
            ← back
          </button>
        </div>
      </header>

      {error && (
        <div style={{ color: '#ef4444', textAlign: 'center', padding: '40px 0', fontSize: 14 }}>
          {error}
        </div>
      )}

      {tree && <TreeView tree={tree} />}

      {card && isTerminal && (
        <div style={{ marginTop: 48, display: 'flex', justifyContent: 'center' }}>
          <FeatureCardSummary card={card} />
        </div>
      )}

      {!tree && !error && (
        <div style={{ textAlign: 'center', color: '#475569', fontSize: 14, padding: '60px 0' }}>
          Loading…
        </div>
      )}
    </div>
  )
}

const S: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: '#0f172a',
    color: '#f1f5f9',
    padding: '32px 48px',
  },
  center: {
    minHeight: '100vh',
    background: '#0f172a',
    color: '#f1f5f9',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 20,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 48,
    paddingBottom: 16,
    borderBottom: '1px solid #1e293b',
  },
  logo: {
    fontSize: 22,
    fontWeight: 800,
    color: '#f1f5f9',
    letterSpacing: -0.5,
  },
  sub: {
    color: '#64748b',
    fontSize: 14,
  },
  input: {
    background: '#1e293b',
    border: '1px solid #334155',
    borderRadius: 6,
    padding: '9px 14px',
    color: '#f1f5f9',
    fontSize: 14,
    width: 300,
    outline: 'none',
  },
  button: {
    background: '#3b82f6',
    border: 'none',
    borderRadius: 6,
    padding: '9px 18px',
    color: '#fff',
    fontSize: 14,
    cursor: 'pointer',
    fontWeight: 600,
  },
}
