import { useState } from 'react'
import type { MCPTool, MCPResource } from '../types'

const TOOLS: MCPTool[] = [
  { name: 'generate_code', description: 'Generate code from a natural language prompt', inputSchema: { type: 'object', properties: { prompt: { type: 'string' }, language: { type: 'string' }, style: { type: 'string' } } } },
  { name: 'explain_code', description: 'Explain what a piece of code does', inputSchema: { type: 'object', properties: { code: { type: 'string' }, detail: { type: 'string' } } } },
  { name: 'search_docs', description: 'Search documentation for relevant information', inputSchema: { type: 'object', properties: { query: { type: 'string' }, top_k: { type: 'integer' } } } },
  { name: 'format_code', description: 'Format code to follow style conventions', inputSchema: { type: 'object', properties: { code: { type: 'string' }, style: { type: 'string' } } } },
  { name: 'analyze_complexity', description: 'Analyze code complexity metrics', inputSchema: { type: 'object', properties: { code: { type: 'string' } } } },
]

const RESOURCES: MCPResource[] = [
  { uri: 'docs://architecture', name: 'architecture', description: 'System architecture documentation' },
  { uri: 'docs://agents', name: 'agents', description: 'Agent system documentation' },
  { uri: 'docs://mcp', name: 'mcp', description: 'MCP protocol documentation' },
  { uri: 'config://defaults', name: 'defaults', description: 'Default configuration' },
]

export default function MCPServerPanel() {
  const [selectedTool, setSelectedTool] = useState<MCPTool | null>(null)
  const [selectedResource, setSelectedResource] = useState<MCPResource | null>(null)
  const [toolOutput, setToolOutput] = useState<string | null>(null)
  const [resourceContent, setResourceContent] = useState<string | null>(null)

  const callTool = (tool: MCPTool) => {
    setSelectedTool(tool)
    setToolOutput(`Calling ${tool.name}...\n\nResult: Simulated response from "${tool.name}"\nArguments: ${JSON.stringify(tool.inputSchema, null, 2)}`)
  }

  const readResource = (res: MCPResource) => {
    setSelectedResource(res)
    setResourceContent(`# ${res.name}\n\nThis is the content of ${res.uri}.\n\nThe Model Context Protocol (MCP) is an open standard for connecting AI models to tools and data sources. It is already used by companies like OpenAI, Anthropic, and Google.`)
  }

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>
        MCP Server — Model Context Protocol
      </h2>
      <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 24 }}>
        An open standard for connecting AI models to tools and data sources.
        Used by OpenAI, Anthropic, Google, and more.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
        <div style={{
          background: 'var(--bg-secondary)', borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border)', padding: 16,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>🛠️ Tools</div>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', background: 'var(--bg-tertiary)', padding: '2px 8px', borderRadius: 10 }}>
              {TOOLS.length} registered
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {TOOLS.map((tool) => (
              <div key={tool.name} style={{
                padding: '10px 12px', borderRadius: 'var(--radius)',
                background: selectedTool?.name === tool.name ? 'var(--bg-hover)' : 'var(--bg-tertiary)',
                border: '1px solid var(--border)', cursor: 'pointer',
                transition: 'all 0.1s',
              }}
                onClick={() => callTool(tool)}
              >
                <div style={{ fontWeight: 600, fontSize: 12, fontFamily: 'monospace', color: 'var(--accent-cyan)', marginBottom: 2 }}>
                  {tool.name}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                  {tool.description}
                </div>
              </div>
            ))}
          </div>
          {toolOutput && (
            <div style={{
              marginTop: 12, padding: 12, borderRadius: 'var(--radius)',
              background: '#00000033', fontFamily: 'monospace',
              fontSize: 11, color: 'var(--accent-green)', whiteSpace: 'pre-wrap',
              border: '1px solid var(--border)',
            }}>
              {toolOutput}
            </div>
          )}
        </div>

        <div style={{
          background: 'var(--bg-secondary)', borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border)', padding: 16,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>📄 Resources</div>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', background: 'var(--bg-tertiary)', padding: '2px 8px', borderRadius: 10 }}>
              {RESOURCES.length} available
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {RESOURCES.map((res) => (
              <div key={res.uri} style={{
                padding: '10px 12px', borderRadius: 'var(--radius)',
                background: selectedResource?.uri === res.uri ? 'var(--bg-hover)' : 'var(--bg-tertiary)',
                border: '1px solid var(--border)', cursor: 'pointer',
                transition: 'all 0.1s',
              }}
                onClick={() => readResource(res)}
              >
                <div style={{ fontWeight: 600, fontSize: 12, fontFamily: 'monospace', color: 'var(--accent-purple)', marginBottom: 2 }}>
                  {res.uri}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                  {res.description}
                </div>
              </div>
            ))}
          </div>
          {resourceContent && (
            <div style={{
              marginTop: 12, padding: 12, borderRadius: 'var(--radius)',
              background: '#00000033', fontFamily: 'monospace',
              fontSize: 11, color: 'var(--accent-green)', whiteSpace: 'pre-wrap',
              border: '1px solid var(--border)',
            }}>
              {resourceContent}
            </div>
          )}
        </div>
      </div>

      <div style={{
        background: 'var(--bg-secondary)', borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--border)', padding: 20,
      }}>
        <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 12 }}>
          MCP Request Flow
        </div>
        <div style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--text-secondary)', lineHeight: 2 }}>
          <div><span style={{ color: 'var(--accent-blue)' }}>→</span> POST /mcp  <span style={{ color: 'var(--text-muted)' }}>{'{ "jsonrpc": "2.0", "method": "tools/list", "id": 1 }'}</span></div>
          <div><span style={{ color: 'var(--accent-green)' }}>←</span> 200 OK  <span style={{ color: 'var(--text-muted)' }}>{'{ "jsonrpc": "2.0", "result": { "tools": [...] }, "id": 1 }'}</span></div>
          <div style={{ marginTop: 8 }}><span style={{ color: 'var(--accent-blue)' }}>→</span> POST /mcp  <span style={{ color: 'var(--text-muted)' }}>{'{ "jsonrpc": "2.0", "method": "tools/call", "params": { "name": "generate_code", "arguments": {...} }, "id": 2 }'}</span></div>
          <div><span style={{ color: 'var(--accent-green)' }}>←</span> 200 OK  <span style={{ color: 'var(--text-muted)' }}>{'{ "jsonrpc": "2.0", "result": { "content": [...] }, "id": 2 }'}</span></div>
        </div>
      </div>
    </div>
  )
}
