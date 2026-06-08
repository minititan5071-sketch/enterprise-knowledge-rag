# Architecture Notes

The platform keeps tenant isolation at the workspace boundary. Every document, vector payload, audit record, feedback entry, and evaluation row carries `workspace_id`. API services call RBAC checks before reading or writing workspace data.

Core flows:

1. User uploads a document through FastAPI.
2. The file is written to `data/uploads/<workspace_id>`.
3. PostgreSQL stores document metadata with `pending` status.
4. Celery extracts text, chunks by page where available, embeds chunks, and upserts vectors into Qdrant.
5. Queries embed the question, search Qdrant with a `workspace_id` filter, and pass reliable context to the LLM client.
6. The answer response includes citations and an audit log ID.
7. Feedback and evaluation use audit/query outputs to track quality.

The LLM and embedding clients call OpenAI-compatible endpoints when configured. Local deterministic providers exist for development and CI.

