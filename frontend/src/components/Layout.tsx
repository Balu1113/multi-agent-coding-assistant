import { ReactNode } from 'react'

interface Tab {
  id: string
  label: string
  icon: string
}

interface LayoutProps {
  tabs: Tab[]
  activeTab: string
  onTabChange: (id: string) => void
  children: ReactNode
}

const headerStyle: React.CSSProperties = {
  background: 'linear-gradient(135deg, #1a1d27 0%, #252836 100%)',
  borderBottom: '1px solid var(--border)',
  padding: '16px 24px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
}

const logoStyle: React.CSSProperties = {
  fontSize: 20,
  fontWeight: 700,
  color: 'var(--text-primary)',
  display: 'flex',
  alignItems: 'center',
  gap: 10,
}

const logoAccent: React.CSSProperties = {
  color: 'var(--accent-blue)',
}

const subtitleStyle: React.CSSProperties = {
  fontSize: 12,
  color: 'var(--text-muted)',
  fontWeight: 400,
  marginLeft: 4,
}

const navStyle: React.CSSProperties = {
  display: 'flex',
  gap: 4,
  padding: '0 24px',
  background: 'var(--bg-secondary)',
  borderBottom: '1px solid var(--border)',
  overflowX: 'auto',
}

const tabBtn = (active: boolean): React.CSSProperties => ({
  display: 'flex',
  alignItems: 'center',
  gap: 6,
  padding: '10px 16px',
  border: 'none',
  background: active ? 'var(--bg-tertiary)' : 'transparent',
  color: active ? 'var(--accent-blue)' : 'var(--text-secondary)',
  fontSize: 13,
  fontWeight: active ? 600 : 400,
  cursor: 'pointer',
  borderBottom: active ? '2px solid var(--accent-blue)' : '2px solid transparent',
  transition: 'all 0.15s ease',
  whiteSpace: 'nowrap',
})

const mainStyle: React.CSSProperties = {
  padding: 24,
  overflow: 'auto',
  height: 'calc(100vh - 108px)',
}

export default function Layout({ tabs, activeTab, onTabChange, children }: LayoutProps) {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <header style={headerStyle}>
        <div style={logoStyle}>
          <span>{'{ }'}</span>
          <span>
            Multi-Agent<span style={logoAccent}> Coding Assistant</span>
            <span style={subtitleStyle}>v0.1.0</span>
          </span>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <span style={{
            width: 8, height: 8, borderRadius: '50%',
            background: 'var(--accent-green)', display: 'inline-block',
          }} />
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>System Ready</span>
        </div>
      </header>

      <nav style={navStyle}>
        {tabs.map((tab) => (
          <button
            key={tab.id}
            style={tabBtn(activeTab === tab.id)}
            onClick={() => onTabChange(tab.id)}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </nav>

      <main style={mainStyle}>{children}</main>
    </div>
  )
}
