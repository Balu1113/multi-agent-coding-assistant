import { useState } from 'react'
import Layout from './components/Layout'
import AgentPanel from './components/AgentPanel'

import MCPServerPanel from './components/MCPServerPanel'
import RAGPanel from './components/RAGPanel'
import FineTuningPanel from './components/FineTuningPanel'
import MonitorDashboard from './components/MonitorDashboard'
import WorkspacePanel from './components/WorkspacePanel'

type Tab = 'agents' | 'workspace' | 'mcp' | 'rag' | 'fine-tune' | 'monitor'

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: 'agents', label: 'Agents', icon: '🤖' },
  { id: 'workspace', label: 'Workspace', icon: '📂' },
  { id: 'mcp', label: 'MCP Server', icon: '🔌' },
  { id: 'rag', label: 'RAG', icon: '📚' },
  { id: 'fine-tune', label: 'Fine-Tuning', icon: '🎯' },
  { id: 'monitor', label: 'Monitor', icon: '📊' },
]

export default function App() {
  const [activeTab, setActiveTab] = useState<Tab>('agents')

  const renderTab = () => {
    switch (activeTab) {
      case 'agents':
        return <AgentPanel />
      case 'workspace':
        return null
      case 'mcp':
        return <MCPServerPanel />
      case 'rag':
        return <RAGPanel />
      case 'fine-tune':
        return <FineTuningPanel />
      case 'monitor':
        return <MonitorDashboard />
    }
  }

  return (
    <Layout
      tabs={TABS}
      activeTab={activeTab}
      onTabChange={(id) => setActiveTab(id as Tab)}
    >
      <div style={{ height: '100%', display: activeTab === 'workspace' ? 'block' : 'none' }}>
        <WorkspacePanel />
      </div>
      {activeTab !== 'workspace' && renderTab()}
    </Layout>
  )
}
