# Adaptive Multi-Agent DevOps Incident Resolver

An enterprise-style incident investigation app that uses a planner agent, executor agent, tool layer, RAG retrieval, reflector retries, and a final incident report to diagnose production alerts.

The project is designed to work locally even when PostgreSQL, Redis, RabbitMQ, and an external LLM are unavailable. In that mode it uses deterministic demo data, realistic generated logs, a local FAISS index, and safe simulated read-only infrastructure outputs.

## Capabilities

- Manual incident creation, Linux log upload, and 10 built-in demo incidents.
- Live server-sent event stream for planner decisions, tool execution, terminal output, reflection retries, confidence, root cause, and suggested fix.
- Agent workflow: Planner -> Executor -> Tool Layer -> Reflector -> Final Report.
- RAG over runbooks, previous incidents, and infrastructure documentation using FAISS.
- Read-only tool guardrails for shell commands, log reading, PostgreSQL checks, Redis checks, runbook search, previous incident search, and semantic search.
- React enterprise dashboard with active incidents, trace timeline, terminal panel, metrics, and report view.
- Docker Compose with backend, frontend, PostgreSQL, Redis, and RabbitMQ.
- CI pipeline with Ruff, Black, mypy, pytest, and frontend build.

## Repository Layout

```text
backend/devops_resolver/
  domain/          Core models and repository contracts
  application/     Agent orchestration, reflection loop, use cases
  infrastructure/  Demo data, FAISS index, tool adapters, repositories
  presentation/    FastAPI routes and application factory
frontend/
  src/             React, TypeScript, TailwindCSS dashboard
tests/
  unit/            Isolated model, RAG, and tool tests
  agent/           Multi-agent workflow tests
  integration/     FastAPI integration tests
```

## Local Backend

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uvicorn devops_resolver.presentation.api.main:app --reload --host 0.0.0.0 --port 8000
```

API docs are available at `http://localhost:8000/docs`.

## Local Frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard runs at `http://localhost:5173` and proxies `/api` to the backend.

## Docker Compose

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: `http://localhost:8080`
- Backend API: `http://localhost:8000`
- RabbitMQ management: `http://localhost:15672`

## Configuration

Environment variables use the `DIR_` prefix.

| Variable | Purpose |
| --- | --- |
| `DIR_DATABASE_URL` | Optional PostgreSQL URL. Local demo fallback works without it. |
| `DIR_REDIS_URL` | Optional Redis URL. Local demo fallback works without it. |
| `DIR_RABBITMQ_URL` | Optional RabbitMQ URL for future queue workers. |
| `DIR_LLM_PROVIDER` | `local`, `groq`, `openai`, or `openai_compatible`. Defaults to no-credit local mode. |
| `DIR_GROQ_API_KEY` | Optional Groq API key for Llama models. |
| `DIR_GROQ_BASE_URL` | Groq OpenAI-compatible endpoint. Defaults to `https://api.groq.com/openai/v1`. |
| `DIR_OPENAI_API_KEY` | Optional OpenAI or OpenAI-compatible API key. |
| `DIR_OPENAI_BASE_URL` | Optional OpenAI-compatible endpoint. |
| `DIR_LLM_MODEL` | Chat model name. Defaults to `llama-3.1-8b-instant`; `llama-3.3-70b-versatile` is a stronger Groq option. |
| `DIR_USE_MOCK_LLM` | Force deterministic local planner mode. |

### Groq Llama Setup

```env
DIR_LLM_PROVIDER=groq
DIR_GROQ_API_KEY=your_groq_key
DIR_LLM_MODEL=llama-3.1-8b-instant
```

Groq exposes an OpenAI-compatible API, so the backend uses the same LangChain `ChatOpenAI` adapter with Groq's base URL. Use `llama-3.1-8b-instant` for speed or `llama-3.3-70b-versatile` for stronger planning.

## Demo Incidents

The built-in catalog includes High CPU, Disk Full, PostgreSQL Down, Redis Memory Full, Out Of Memory, Service Crash, SSL Expired, High Disk IO, Nginx 502, and Memory Leak. Each demo includes realistic logs, an expected root cause, and an expected mitigation.

## Verification

```bash
ruff check backend tests
black --check backend tests
mypy backend
pytest
cd frontend && npm run build
```

## Safety Model

Autonomous shell execution is restricted to an allowlist of read-only diagnostic commands. Destructive command patterns such as `rm`, `kill`, `drop`, `delete`, `truncate`, `insert`, and `update` are refused and captured as failed tool evidence. Live PostgreSQL and Redis mutation is not enabled by default; local and demo investigations use safe read-only simulated adapters.
