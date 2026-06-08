# Interview Demo Script

Scenario: HarbourBridge Digital Finance Limited is a fictional Hong Kong fintech company using the Enterprise Knowledge RAG Platform as an internal knowledge base for compliance, support, security, product, vendor risk, and AI governance teams.

## 1. Start The Platform

Docker Compose path:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Local Python path:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL = "sqlite:///./local.db"
$env:VECTOR_STORE = "memory"
$env:AUTO_CREATE_TABLES = "true"
$env:OTEL_ENABLED = "false"
$env:RAG_TOP_K = "8"
$env:RAG_MIN_SCORE = "0"
uvicorn backend.app.main:app --reload
```

In a second PowerShell window for the local frontend:

```powershell
.\.venv\Scripts\Activate.ps1
$env:BACKEND_URL = "http://localhost:8000"
streamlit run frontend/app.py
```

Open:

- API docs: http://localhost:8000/docs
- Streamlit: http://localhost:8501

## 2. Create Admin User

In Streamlit, register:

- Email: `admin@harbourbridge.example`
- Password: `Password123!`
- Full name: `Demo Admin`

Then log in with the same credentials.

## 3. Create Workspace

Create a workspace:

- Name: `HarbourBridge Knowledge Base`
- Description: `Synthetic internal knowledge base for a Hong Kong fintech demo`

Explain that each workspace is a tenant boundary. Documents, vector search, query audit logs, feedback, and evaluation records are scoped to the workspace.

## 4. Upload Demo Documents

Upload the files in `data/demo_documents`:

- `Compliance_Policy_2026.md`
- `KYC_Procedure_Manual.md`
- `Customer_Support_SOP.md`
- `IT_Security_Policy.md`
- `Digital_Banking_Product_FAQ.md`
- `Incident_Response_Playbook.md`
- `Vendor_Risk_Management_Guide.md`
- `Employee_Onboarding_AI_Tools.md`

If using Docker Compose, ingestion runs through the Celery worker. If using the lightweight local SQLite path, run the backend with `CELERY_TASK_ALWAYS_EAGER=true` or start a Redis-backed worker.

Note: with `VECTOR_STORE=memory`, vectors are lost after backend restart. Re-upload or re-ingest demo documents after restarting, or use Qdrant through Docker Compose.

## 5. Wait For Ingestion

Open the Documents page and wait until each document status is `completed`.

Explain the ingestion flow:

1. Raw file is saved under `data/uploads`.
2. PostgreSQL stores document metadata.
3. Celery extracts text and chunks content.
4. Embeddings are generated.
5. Qdrant stores vectors with workspace and document metadata.

## 6. Ask Demo Questions

Use the Ask page. For each answer, open citations and show that snippets come from the expected document.

1. What documents are required for customer onboarding under the KYC policy?
2. What should support agents do when a customer reports a failed transfer?
3. What is the incident response process for suspected data leakage?
4. What are the rules for using GenAI tools internally?
5. Which vendor risks require escalation?
6. How are payment approvals configured for the business wallet?
7. How often must privileged production access be reviewed?
8. What training must new employees complete before using internal AI tools with confidential information?

## 7. Show Citations

For each response, highlight:

- Source document names.
- Chunk snippets.
- Page number where available.
- Confidence score heuristic.
- Refusal behavior when context is missing.

Suggested missing-context prompt:

```text
What is the private API key for the production payment gateway?
```

The system should answer that it does not know based on available workspace documents.

## 8. Show Audit Logs

Open Query History and explain that every query records:

- User ID.
- Workspace ID.
- Question.
- Retrieved document IDs.
- Model name.
- Latency.
- Timestamp.

Explain that audit access requires workspace admin.

## 9. Load And Run Evaluation

Load the golden QA dataset:

```powershell
.\.venv\Scripts\Activate.ps1
python -m backend.app.rag.evaluate load-dataset --workspace-id <workspace-id> --user-email admin@harbourbridge.example --dataset-path data/eval_sets/fintech_knowledge_eval.json
```

Run evaluation:

```powershell
python -m backend.app.rag.evaluate run --workspace-id <workspace-id> --user-email admin@harbourbridge.example
```

In Streamlit, open Evaluation Results and discuss:

- `citation_hit_rate`
- `answer_contains_required_facts`
- `retrieval_recall_at_k`
- `refusal_rate_when_context_missing`

## 10. Explain RBAC Behavior

Create a second user:

- Email: `viewer@harbourbridge.example`
- Role: `viewer`

Show:

- Viewer can list documents and ask questions in the workspace.
- Viewer cannot upload documents.
- Viewer cannot add members.
- Viewer cannot view audit logs or run evaluation.

Then update the user to `manager`:

- Manager can upload documents.
- Manager still cannot manage members or view admin-only audit/evaluation pages.

Explain that `admin`, `manager`, and `viewer` are enforced in backend services, not only in the UI.

## 11. Closing Talking Points

This is positioned as an enterprise RAG platform, not a chatbot demo:

- Multi-tenant workspace model.
- Real JWT auth and RBAC.
- Async ingestion with Celery.
- Qdrant vector search scoped by workspace.
- Citation-grounded responses.
- Audit logs and feedback.
- Evaluation dataset and batch metrics.
- Docker Compose deployment path.
