# Usage

## Quick Start

```bash
# Install dependencies
pip install -e .

# Run the interactive CLI
python -m src.main
```

## Running Tests

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

## API Overview

### Agents

```python
from src.agents.orchestrator import AgentOrchestrator
from src.communication.message_queue import MessageQueue

async def example():
    mq = MessageQueue()
    async with AgentOrchestrator(mq) as orch:
        result = await orch.process_request("Write a sorting algorithm")
        print(result["code"])
```

### MCP Server

```python
from src.mcp.server import MCPServer, MCPRequest

server = MCPServer()
resp = await server.handle_request(MCPRequest(
    method="tools/call",
    params={"name": "generate_code", "arguments": {"prompt": "hello"}},
))
```

### RAG

```python
from src.rag.retriever import RAGRetriever

retriever = RAGRetriever()
await retriever.index_document("doc1", "Python is a programming language")
results = await retriever.retrieve("programming")
```

### Fine-tuning

```python
from src.models.fine_tuner import FineTuner, TrainingExample

tuner = FineTuner()
examples = [TrainingExample(instruction="Write a function", output="def f(): pass")]
path = await tuner.prepare_dataset(examples)
output_dir = await tuner.train(path)
```

### Evaluation

```python
from src.evaluation.benchmarks import CodingBenchmark

bm = CodingBenchmark()
results = await bm.run_all(lambda p: f"# {p}")
print(bm.summarize(results))
```

## Configuration

Copy `.env.example` to `.env` and set:

| Variable | Description |
|----------|-------------|
| `LLM_PROVIDER` | openai, anthropic, or ollama |
| `LLM_API_KEY` | API key for the LLM provider |
| `LLM_MODEL` | Model name (e.g. gpt-4o) |
| `EMBEDDING_MODEL` | Sentence transformer model |
| `CHROMA_PERSIST_DIR` | Vector store storage path |
