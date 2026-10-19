import { useState } from 'react'
import type { RAGDocument } from '../types'

const INDEXED_DOCS: RAGDocument[] = [
  { id: 'doc1', content: 'Python is a dynamically-typed, garbage-collected programming language.', metadata: { file: 'python.md', type: 'doc' } },
  { id: 'doc2', content: 'FastAPI is a modern web framework for building APIs with Python.', metadata: { file: 'fastapi.md', type: 'doc' } },
  { id: 'doc3', content: 'Pytest is a testing framework that makes it easy to write simple tests.', metadata: { file: 'pytest.md', type: 'doc' } },
  { id: 'doc4', content: 'React is a JavaScript library for building user interfaces.', metadata: { file: 'react.md', type: 'doc' } },
]

export default function RAGPanel() {
  const [docs] = useState<RAGDocument[]>(INDEXED_DOCS)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<RAGDocument[]>([])

  const search = () => {
    if (!query.trim()) return
    const q = query.toLowerCase()
    const found = docs
      .filter((d) => d.content.toLowerCase().includes(q) || d.id.toLowerCase().includes(q))
      .map((d, i) => ({ ...d, score: Math.max(0, 1 - i * 0.2) }))
    setResults(found)
  }

  return (
    <div>
      <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>
        RAG — Retrieval-Augmented Generation
      </h2>
      <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 24 }}>
        Lets agents pull answers from documentation instead of hallucinating.
        Embeddings are generated via sentence-transformers and stored in a vector store
        with cosine similarity search.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
        <div style={{
          background: 'var(--bg-secondary)', borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border)', padding: 16,
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <div style={{ fontSize: 14, fontWeight: 600 }}>📚 Indexed Documents</div>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', background: 'var(--bg-tertiary)', padding: '2px 8px', borderRadius: 10 }}>
              {docs.length} docs
            </span>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, maxHeight: 300, overflow: 'auto' }}>
            {docs.map((doc) => (
              <div key={doc.id} style={{
                padding: '10px 12px',
                background: 'var(--bg-tertiary)',
                borderRadius: 'var(--radius)',
                border: '1px solid var(--border)',
                fontSize: 12,
              }}>
                <div style={{ fontWeight: 600, fontSize: 11, color: 'var(--accent-cyan)', marginBottom: 4, fontFamily: 'monospace' }}>
                  {doc.id}
                  <span style={{ color: 'var(--text-muted)', marginLeft: 8 }}>{doc.metadata.file}</span>
                </div>
                <div style={{ color: 'var(--text-secondary)' }}>{doc.content}</div>
              </div>
            ))}
          </div>
        </div>

        <div style={{
          background: 'var(--bg-secondary)', borderRadius: 'var(--radius-lg)',
          border: '1px solid var(--border)', padding: 16,
        }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
            🔍 Search Documents
          </div>
          <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && search()}
              placeholder="Search query..."
              style={{
                flex: 1, padding: '10px 14px', borderRadius: 'var(--radius)',
                border: '1px solid var(--border)',
                background: 'var(--bg-tertiary)', color: 'var(--text-primary)',
                fontSize: 13, outline: 'none',
              }}
            />
            <button onClick={search} style={{
              padding: '10px 20px', borderRadius: 'var(--radius)',
              border: 'none', background: 'var(--accent-blue)',
              color: '#fff', fontWeight: 600, fontSize: 13, cursor: 'pointer',
            }}>
              Search
            </button>
          </div>

          {results.length > 0 && (
            <div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 8 }}>
                Top {results.length} results
              </div>
              {results.map((r, i) => (
                <div key={i} style={{
                  padding: '10px 12px',
                  background: 'var(--bg-tertiary)',
                  borderRadius: 'var(--radius)',
                  border: '1px solid var(--border)',
                  marginBottom: 6,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--accent-purple)' }}>
                      {r.id}
                    </span>
                    {r.score !== undefined && (
                      <span style={{
                        fontSize: 10, padding: '1px 6px', borderRadius: 8,
                        background: r.score > 0.8 ? 'var(--accent-green)22' : 'var(--accent-yellow)22',
                        color: r.score > 0.8 ? 'var(--accent-green)' : 'var(--accent-yellow)',
                      }}>
                        {(r.score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    {r.content}
                  </div>
                </div>
              ))}
            </div>
          )}

          {results.length === 0 && query && (
            <div style={{ fontSize: 12, color: 'var(--text-muted)', padding: '12px 0' }}>
              No results found for "{query}"
            </div>
          )}
        </div>
      </div>

      <div style={{
        background: 'var(--bg-secondary)', borderRadius: 'var(--radius-lg)',
        border: '1px solid var(--border)', padding: 20,
      }}>
        <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 12 }}>
          How RAG Works in This System
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
          {[
            { title: '1. Embed', desc: 'Documents and queries are converted to 384-dimensional vector embeddings using sentence-transformers.' },
            { title: '2. Search', desc: 'Query embedding is compared against all document embeddings using cosine similarity.' },
            { title: '3. Retrieve', desc: 'Top-k most similar documents are returned as context for the agent to use.' },
          ].map((step) => (
            <div key={step.title} style={{
              padding: 16, borderRadius: 'var(--radius)',
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border)',
            }}>
              <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--accent-cyan)', marginBottom: 6 }}>
                {step.title}
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                {step.desc}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
