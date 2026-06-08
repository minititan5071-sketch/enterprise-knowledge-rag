# Enterprise Knowledge RAG Platform

Enterprise Knowledge RAG Platform is a portfolio-quality internal knowledge-base system for companies that need workspace-scoped document search, citation-grounded answers, auditability, and role-based governance.

This is intentionally positioned as an enterprise AI application, not a chatbot demo. It includes authentication, workspace RBAC, async ingestion, vector retrieval, audit logs, feedback, evaluation, Docker Compose, and a Streamlit admin dashboard.

## Enterprise Use Case

A company can use this platform to centralize internal policies, support procedures, product FAQs, security playbooks, onboarding guides, and compliance manuals. Employees ask questions inside a workspace and receive answers grounded in approved documents with citations.

The included demo scenario uses a fictional Hong Kong fintech company, HarbourBridge Digital Finance Limited. Demo documents live in `data/demo_documents`, and the golden QA set lives in `data/eval_sets/fintech_knowledge_eval.json`.

## Architecture

```mermaid
flowchart LR
  User["Employee or Admin"] --> UI["Streamlit Dashboard"]
  UI --> API["FastAPI Backend"]
  API --> Auth["JWT Auth and RBAC"]
  API --> PG["PostgreSQL Metadata"]
  API --> Redis["Redis Broker"]
  API --> Qdrant["Qdrant Vector DB"]
  API --> LLM["OpenAI-Compatible LLM"]
  Redis --> Worker["Celery Worker"]
  Worker --> Files["data/uploads"]
  Worker --> Extract["Text Extraction and Chunking"]
  Extract --> Embed["Embedding Client"]
  Embed --> Qdrant
  Worker --> PG
  API --> Audit["Audit Logs and Feedback"]
  API --> OTel["Structured Logs and OpenTelemetry"]
```

## Module Breakdown

| Path | Responsibility |
| --- | --- |
| `backend/app/api` | FastAPI routers, route dependencies, OpenAPI tags. |
| `backend/app/auth` | Password hashing, JWT creation/validation, workspace RBAC checks. |
| `backend/app/core` | Runtime settings, Celery app, structured logging. |
| `backend/app/db` | SQLAlchemy base, engine, and session management. |
| `backend/app/models` | SQLAlchemy tables for users, workspaces, documents, audit logs, feedback, and evaluation. |
| `backend/app/rag` | Chunking, loaders, embeddings, vector store, LLM client, evaluation CLI. |
| `backend/app/services` | Business logic for auth, workspaces, documents, ingestion, query, feedback, audit, and evaluation. |
| `backend/app/workers` | Celery task definitions. |
| `frontend` | Streamlit dashboard for operators and demo users. |
| `data/demo_documents` | Synthetic fintech knowledge base for demos. |
| `data/eval_sets` | Golden QA dataset for evaluation. |
| `docs` | Architecture, demo, security, and screenshot guidance. |

## API Endpoints

| Method | Endpoint | Purpose | Access |
| --- | --- | --- | --- |
| `GET` | `/health` | Service and database health check. | Public |
| `POST` | `/auth/register` | Register user. | Public |
| `POST` | `/auth/login` | Login and receive JWT. | Public |
| `POST` | `/workspaces` | Create workspace. | Authenticated |
| `GET` | `/workspaces` | List workspaces for current user. | Authenticated |
| `POST` | `/workspaces/{workspace_id}/members` | Add or update workspace member. | Admin |
| `POST` | `/documents/upload` | Upload document for ingestion. | Manager or Admin |
| `GET` | `/documents` | List workspace documents. | Viewer or higher |
| `POST` | `/query` | Ask a workspace-scoped RAG question. | Viewer or higher |
| `POST` | `/feedback` | Mark answer as helpful, wrong, or unsafe. | Viewer or higher |
| `GET` | `/feedback` | View workspace feedback. | Admin |
| `GET` | `/audit-logs` | View query audit logs. | Admin |
| `POST` | `/eval/golden` | Create golden QA pair. | Admin |
| `POST` | `/eval/run` | Run evaluation. | Admin |
| `GET` | `/eval/results` | List evaluation runs or run details. | Admin |

## Document Ingestion Flow

```mermaid
sequenceDiagram
  participant U as User
  participant API as FastAPI
  participant DB as PostgreSQL
  participant R as Redis
  participant W as Celery Worker
  participant Q as Qdrant

  U->>API: Upload PDF/TXT/MD/DOCX
  API->>API: Check JWT and workspace role
  API->>DB: Store document metadata as pending
  API->>R: Enqueue ingestion task
  W->>DB: Mark document processing
  W->>W: Extract text and chunk with metadata
  W->>W: Generate embeddings
  W->>Q: Upsert vectors with workspace_id filter metadata
  W->>DB: Mark completed with chunk count
```

## RAG Query Flow

```mermaid
sequenceDiagram
  participant U as User
  participant API as FastAPI
  participant Q as Qdrant
  participant L as LLM
  participant DB as PostgreSQL

  U->>API: POST /query
  API->>API: Validate JWT and workspace membership
  API->>API: Embed question
  API->>Q: Search top-k chunks filtered by workspace_id
  API->>API: Apply minimum score threshold
  alt reliable context found
    API->>L: Generate answer from retrieved context
  else no reliable context
    API->>API: Refuse with "I do not know"
  end
  API->>DB: Write audit log
  API->>U: Return answer, citations, snippets, confidence, audit_log_id
```

## Windows Local Setup

Use PowerShell from the repository root: `D:\projects\RAG-project`.

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Run the backend with local SQLite and in-memory vector search:

```powershell
$env:DATABASE_URL = "sqlite:///./local.db"
$env:VECTOR_STORE = "memory"
$env:AUTO_CREATE_TABLES = "true"
$env:OTEL_ENABLED = "false"
$env:CELERY_TASK_ALWAYS_EAGER = "true"
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Run the Streamlit frontend in a second PowerShell window:

```powershell
.\.venv\Scripts\Activate.ps1
$env:BACKEND_URL = "http://localhost:8000"
streamlit run frontend/app.py
```

Open:

- API docs: http://localhost:8000/docs
- Frontend: http://localhost:8501

## Running Celery Locally

For production-like local execution, run Redis separately and do not set `CELERY_TASK_ALWAYS_EAGER=true`.

PowerShell window 1:

```powershell
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL = "postgresql+psycopg://rag:rag@localhost:5432/rag"
$env:CELERY_BROKER_URL = "redis://localhost:6379/0"
$env:CELERY_RESULT_BACKEND = "redis://localhost:6379/1"
uvicorn backend.app.main:app --reload
```

PowerShell window 2:

```powershell
.\.venv\Scripts\Activate.ps1
$env:DATABASE_URL = "postgresql+psycopg://rag:rag@localhost:5432/rag"
$env:CELERY_BROKER_URL = "redis://localhost:6379/0"
$env:CELERY_RESULT_BACKEND = "redis://localhost:6379/1"
celery -A backend.app.core.celery_app.celery_app worker --loglevel=INFO
```

## Docker Compose Setup

Create `.env` from the safe template:

```powershell
Copy-Item .env.example .env
```

Start the full stack:

```powershell
docker compose up --build
```

Services:

- Backend API: http://localhost:8000
- Streamlit frontend: http://localhost:8501
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- Qdrant dashboard: http://localhost:6333/dashboard

The Docker path runs:

- `postgres`
- `redis`
- `qdrant`
- `backend`
- `celery-worker`
- `frontend`

The backend container runs `alembic upgrade head` before starting Uvicorn.

## Running Tests

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
$env:TEMP = "$PWD\.tmp"
$env:TMP = "$PWD\.tmp"
pytest
python -m compileall backend frontend
```

The tests use SQLite and the in-memory vector store, so they do not require Docker, Postgres, Redis, or Qdrant.

Current verified status:

- `pytest`: 10 tests passing.
- `python -m compileall backend frontend`: passing.

## Demo Flow

Use the complete script in `docs/demo_script.md`.

Short version:

1. Start Docker Compose or local Python services.
2. Register `admin@harbourbridge.example`.
3. Create workspace `HarbourBridge Knowledge Base`.
4. Upload all files from `data/demo_documents`.
5. Ask the eight demo questions in `docs/demo_script.md`.
6. Open citations and audit logs.
7. Load the evaluation set:

```powershell
python -m backend.app.rag.evaluate load-dataset --workspace-id <workspace-id> --user-email admin@harbourbridge.example --dataset-path data/eval_sets/fintech_knowledge_eval.json
```

8. Run evaluation:

```powershell
python -m backend.app.rag.evaluate run --workspace-id <workspace-id> --user-email admin@harbourbridge.example
```

## Model Configuration

The default `.env.example` uses deterministic local providers for easy demos. For a real OpenAI-compatible provider, update:

```env
LLM_PROVIDER=openai-compatible
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=replace-with-provider-key
LLM_MODEL=gpt-4o-mini
EMBEDDING_PROVIDER=openai-compatible
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=replace-with-provider-key
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
```

For LM Studio or Ollama, point `LLM_BASE_URL` and `EMBEDDING_BASE_URL` to the local OpenAI-compatible endpoint, often using `host.docker.internal` from Docker containers.

If `EMBEDDING_DIMENSION` changes, use a fresh `QDRANT_COLLECTION` or recreate the existing Qdrant collection.

## Security And Governance

See `docs/security_and_governance.md` for:

- Authentication model.
- RBAC model.
- Workspace isolation.
- Audit logging.
- Prompt and response logging limitations.
- Known risks and future mitigations.

## Repository Hygiene

The repository ignores:

- `.env` and local secret files.
- Python caches and test caches.
- Virtual environments.
- Local SQLite/database files.
- Logs.
- Docker/local volume artifacts.
- Uploaded documents under `data/uploads`.

Safe demo documents under `data/demo_documents` and eval sets under `data/eval_sets` are intended to be committed.

## Limitations

- The default local LLM and embedding providers are deterministic development fallbacks.
- Local file storage under `data/uploads` should be replaced with encrypted object storage for production.
- Scanned PDFs require OCR support.
- Workspace-level RBAC exists, but per-document ACLs are not implemented yet.
- Prompt-injection mitigation is basic and should be expanded.
- Evaluation metrics are heuristic and intended for regression signals, not formal model certification.
- No SSO/OIDC, refresh tokens, token revocation, or SCIM provisioning yet.

## Roadmap

- Add OIDC/SAML SSO and SCIM provisioning.
- Add per-document ACLs and data sensitivity labels.
- Add object storage, malware scanning, and document retention policies.
- Add OCR and richer table extraction.
- Add reranking, query rewriting, and citation verification.
- Add prompt-injection detection and safer context handling.
- Add background evaluation scheduling and quality regression alerts.
- Add OpenTelemetry Collector, dashboards, and secure trace export.
- Add production deployment manifests for cloud environments.

