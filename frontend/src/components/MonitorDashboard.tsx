import { useState, useEffect } from 'react'
import type { MonitorSummary, BenchmarkResult } from '../types'

const INITIAL_SUMMARY: MonitorSummary = {
  uptimeSeconds: 86400,
  requests: { total: 847, success: 812, failed: 35, successRate: 95.87 },
  latency: { count: 847, min: 0.8, max: 12.4, mean: 2.3, p50: 1.9, p95: 6.2 },
  llmCalls: 2156,
}

const BENCHMARK_RESULTS: BenchmarkResult[] = [
  { name: 'FizzBuzz', success: true, duration: 1.2, score: 1.0, details: {} },
  { name: 'Binary Search', success: true, duration: 2.1, score: 1.0, details: {} },
  { name: 'Quick Sort', success: true, duration: 2.8, score: 1.0, details: {} },
  { name: 'API Endpoint', success: false, duration: 3.5, score: 0.33, details: {} },
  { name: 'Unit Test', success: true, duration: 2.4, score: 0.67, details: {} },
]

export default function MonitorDashboard() {
  const [summary] = useState<MonitorSummary>(INITIAL_SUMMARY)
  const [benchmarks] = useState<BenchmarkResult[]>(BENCHMARK_RESULTS)
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(interval)
  }, [])

  const passRate = benchmarks.filter((b) => b.success).length / benchmarks.length * 100
  const avgScore = benchmarks.reduce((s, b) => s + b.score, 0) / benchmarks.length * 100

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>
        Evaluation & Monitoring
      </h2>
      <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 24 }}>
        Measure whether your agent is actually improving. Track requests, latency, benchmarks, and more.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
        {[
          { label: 'Uptime', value: `${Math.floor(summary.uptimeSeconds / 3600)}h ${Math.floor((summary.uptimeSeconds % 3600) / 60)}m`, color: 'var(--accent-cyan)' },
          { label: 'Total Requests', value: summary.requests.total.toLocaleString(), color: 'var(--accent-blue)' },
          { label: 'Success Rate', value: `${summary.requests.successRate.toFixed(1)}%`, color: summary.requests.successRate > 90 ? 'var(--accent-green)' : 'var(--accent-yellow)' },
          { label: 'LLM Calls', value: summary.llmCalls.toLocaleString(), color: 'var(--accent-purple)' },
        ].map((stat) => (
          <div key={stat.label} style={{
            background: 'var(--bg-secondary)', borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border)', padding: '16px 20px',
          }}>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: 1 }}>
              {stat.label}
            </div>
            <div style={{ fontSize: 28, fontWeight: 700, color: stat.color }}>
              {stat.value}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
        <div style={{
          background: 'var(--bg-secondary)', borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border)', padding: 16,
        }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
            ⏱️ Latency (seconds)
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {[
              { label: 'Mean', value: summary.latency.mean, pct: 30 },
              { label: 'P50', value: summary.latency.p50, pct: 25 },
              { label: 'P95', value: summary.latency.p95, pct: 80 },
              { label: 'Min', value: summary.latency.min, pct: 10 },
              { label: 'Max', value: summary.latency.max, pct: 100 },
            ].map((m) => (
              <div key={m.label}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 2 }}>
                  <span style={{ color: 'var(--text-secondary)' }}>{m.label}</span>
                  <span style={{ fontWeight: 600 }}>{m.value.toFixed(1)}s</span>
                </div>
                <div style={{ width: '100%', height: 4, borderRadius: 2, background: 'var(--bg-tertiary)' }}>
                  <div style={{
                    width: `${m.pct}%`, height: '100%',
                    borderRadius: 2,
                    background: m.label === 'P95' ? 'var(--accent-yellow)' : 'var(--accent-blue)',
                  }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div style={{
          background: 'var(--bg-secondary)', borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border)', padding: 16,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>📊 Benchmark Results</div>
            <div style={{ fontSize: 11 }}>
              <span style={{ color: 'var(--accent-green)' }}>{passRate.toFixed(0)}%</span>
              <span style={{ color: 'var(--text-muted)' }}> pass — </span>
              <span style={{ color: 'var(--accent-cyan)' }}>{avgScore.toFixed(0)}%</span>
              <span style={{ color: 'var(--text-muted)' }}> avg score</span>
            </div>
          </div>
          {benchmarks.map((b) => (
            <div key={b.name} style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '8px 10px', marginBottom: 4,
              borderRadius: 'var(--radius)', fontSize: 12,
              background: 'var(--bg-tertiary)',
            }}>
              <span style={{
                width: 8, height: 8, borderRadius: '50%',
                background: b.success ? 'var(--accent-green)' : 'var(--accent-red)',
                flexShrink: 0,
              }} />
              <span style={{ fontWeight: 600, flex: 1 }}>{b.name}</span>
              <div style={{
                width: 80, height: 6, borderRadius: 3,
                background: 'var(--border)',
              }}>
                <div style={{
                  width: `${b.score * 100}%`, height: '100%',
                  borderRadius: 3,
                  background: b.score > 0.5 ? 'var(--accent-green)' : 'var(--accent-red)',
                  transition: 'width 0.3s',
                }} />
              </div>
              <span style={{
                color: b.success ? 'var(--accent-green)' : 'var(--accent-red)',
                minWidth: 40, textAlign: 'right',
              }}>
                {(b.score * 100).toFixed(0)}%
              </span>
              <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                {b.duration.toFixed(1)}s
              </span>
            </div>
          ))}
        </div>
      </div>

      <div style={{
        background: 'var(--bg-secondary)', borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--border)', padding: 20,
      }}>
        <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 12 }}>
          System Health
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {[
            { title: 'Agents', status: 'All 3 running', ok: true },
            { title: 'MCP Server', status: '5 tools, 4 resources', ok: true },
            { title: 'RAG Store', status: '4 documents indexed', ok: true },
            { title: 'Model Registry', status: '3 models available', ok: true },
            { title: 'Message Queue', status: '0 pending messages', ok: true },
            { title: 'Last Export', status: time.toLocaleTimeString(), ok: true },
          ].map((item) => (
            <div key={item.title} style={{
              padding: 12, borderRadius: 'var(--radius)',
              background: 'var(--bg-tertiary)', border: '1px solid var(--border)',
              display: 'flex', alignItems: 'center', gap: 10,
            }}>
              <span style={{
                width: 8, height: 8, borderRadius: '50%',
                background: item.ok ? 'var(--accent-green)' : 'var(--accent-red)',
                flexShrink: 0,
              }} />
              <div>
                <div style={{ fontSize: 12, fontWeight: 600 }}>{item.title}</div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{item.status}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
