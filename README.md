# Multi-Agent Coding Assistant

A coding assistant with a React web interface and a Python backend. It supports conversational coding help, agent-orchestrated code generation, MCP tools and resources, retrieval-augmented generation (RAG), fine-tuning workflows, and monitoring.

## Features

- Chat with the assistant and request code generation, review, and tests.
- Orchestrate specialized agents and coordinate work through an asynchronous message queue.
- Expose tools and resources through a Model Context Protocol (MCP) API.
- Index and retrieve context from documents with the RAG components.
- Prepare fine-tuning datasets and run PEFT/LoRA workflows.
- Inspect evaluation and monitoring components.

## Requirements

- Python 3.11 or newer
- Node.js and npm

## Run the Web App

From the repository root, create and activate a virtual environment, then install the Python package and Django dependencies:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install -r backend/requirements.txt
```

Copy `.env.example` to `.env` and set the LLM provider and API key you intend to use. Keep `.env` private; it is excluded from Git.

Run the Django migrations and start the API server:

```powershell
python backend/manage.py migrate
python backend/manage.py runserver 8000
```

In a second terminal, install and start the frontend:

```powershell
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. Vite proxies `/api` requests to the Django server at `http://localhost:8000`.

## Run the Python CLI

With the Python environment activated:

```powershell
python -m src.main
```

## Configuration

The application reads settings from a root `.env` file. See [.env.example](.env.example) for the available variables.

| Variable | Purpose |
| --- | --- |
| `LLM_PROVIDER` | Provider: `openai`, `anthropic`, or `ollama` |
| `LLM_API_KEY` | Provider API key, when required |
| `LLM_MODEL` | Model name |
| `HF_TOKEN` | Optional Hugging Face token for model workflows |
| `BASE_MODEL` | Base model used by fine-tuning workflows |
| `EMBEDDING_MODEL` | Sentence-transformer model used for embeddings |
| `CHROMA_PERSIST_DIR` | Local persistence path for vector data |
| `LOG_LEVEL` | Python log level |

## Tests

Install the test dependencies and run the suite:

```powershell
python -m pip install pytest pytest-asyncio
python -m pytest tests -v
```

To run Django's configuration check:

```powershell
python backend/manage.py check
```

## Project Layout

- `backend/` - Django REST API used by the web interface
- `frontend/` - React and TypeScript application built with Vite
- `src/agents/` - Agent roles and orchestration
- `src/communication/` - Agent messaging and task delegation
- `src/mcp/` - MCP server, tools, and resources
- `src/rag/` - Embedding, retrieval, and vector-store components
- `src/models/` - Model registry and fine-tuning utilities
- `src/evaluation/` - Benchmarks, metrics, and monitoring
- `tests/` - Python test suite
- `docs/` - [Architecture](docs/architecture.md) and [usage examples](docs/usage.md)

## Optional Python Features

The `pyproject.toml` defines optional dependency groups for RAG, fine-tuning, and monitoring. Install them as needed:

```powershell
python -m pip install -e ".[rag]"
python -m pip install -e ".[fine-tune]"
python -m pip install -e ".[monitoring]"
```

Fine-tuning dependencies, especially PyTorch, can require significant disk space and may need platform-specific installation options.

## Development Notes

The Django settings use development defaults. Configure a secure `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, and appropriate `DJANGO_ALLOWED_HOSTS` before deploying. Do not use the development server for production.
