# Architecture

## System Design

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Orchestrator                    │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐           │
│  │  Writer   │   │ Reviewer  │   │  Tester  │           │
│  │  Agent    │   │  Agent    │   │  Agent   │           │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘           │
│       │               │               │                 │
│  ┌────▼───────────────▼───────────────▼────┐           │
│  │          Message Queue (async)          │           │
│  └─────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌────────────────┐
│  MCP Server  │    │  RAG System  │    │  Fine-tuning   │
│  (tools &    │    │  (vector     │    │  Pipeline      │
│   resources) │    │   retrieval) │    │  (PEFT/LoRA)   │
└──────────────┘    └──────────────┘    └────────────────┘
                           │
                           ▼
                  ┌────────────────┐
                  │  Evaluation &  │
                  │  Monitoring    │
                  └────────────────┘
```

## Components

### 1. Multi-Agent System
- **WriterAgent**: Generates code based on prompts + RAG context
- **ReviewerAgent**: Reviews code quality, finds issues
- **TesterAgent**: Creates pytest unit tests
- **AgentOrchestrator**: Coordinates the workflow (write → review → test)

### 2. Agent-to-Agent Communication
- `MessageQueue`: Async pub/sub queue for task distribution
- `delegate()`: Agents can delegate subtasks to other agents
- `DelegationManager`: Routes tasks to the right agent based on keywords

### 3. MCP Server (Model Context Protocol)
- Standard protocol for LLM tool/resource access
- Implements: `initialize`, `tools/list`, `tools/call`, `resources/list`, `resources/read`
- Tools: `generate_code`, `explain_code`, `search_docs`, `format_code`, `analyze_complexity`

### 4. RAG (Retrieval-Augmented Generation)
- `EmbeddingGenerator`: Creates vectors (sentence-transformers or fallback)
- `VectorStore`: In-memory similarity search via cosine similarity
- `RAGRetriever`: Indexes docs/codebase, retrieves context for agents

### 5. Fine-tuning
- `FineTuner`: PEFT/LoRA fine-tuning pipeline for code LLMs
- `ModelRegistry`: Catalog of available models by capability
- Supports real (torch+transformers) and simulated training

### 6. Evaluation & Monitoring
- `MetricsCollector`: Counters, gauges, histograms
- `CodingBenchmark`: 5 standard coding tasks with pass/fail scoring
- `Monitor`: Tracks requests, latency, LLM calls, exports reports
