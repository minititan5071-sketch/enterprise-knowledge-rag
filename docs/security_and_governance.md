# Security And Governance Notes

## Authentication Model

The backend uses JWT bearer authentication. Users register with email and password. Passwords are hashed before storage. Login returns a signed access token, and protected API routes require the token through the `Authorization: Bearer <token>` header.

Current limitations:

- No refresh token flow.
- No SSO, SAML, OIDC, or SCIM provisioning yet.
- Password policy is basic and should be strengthened before production.

## RBAC Model

Authorization is enforced at the workspace level with three roles:

- `admin`: manage workspace membership, upload and list documents, query, view audit logs, manage feedback views, and run evaluations.
- `manager`: upload and list documents, query, and provide feedback.
- `viewer`: list documents, query, and provide feedback.

Role checks happen in backend service functions so access control does not depend on Streamlit UI state.

## Workspace-Level Data Isolation

Workspace ID is the tenant boundary. The application stores `workspace_id` on documents, memberships, audit logs, feedback, golden QA pairs, and evaluation runs. Vector payloads in Qdrant also include `workspace_id`, and retrieval applies a workspace filter before returning chunks.

This model prevents a user in one workspace from querying another workspace unless they have an explicit membership in that workspace.

## Audit Logging

Every RAG query creates an audit log containing:

- User ID.
- Workspace ID.
- Question.
- Retrieved document IDs.
- Model name.
- Latency in milliseconds.
- Creation timestamp.

Audit logs are useful for compliance review, troubleshooting retrieval quality, and monitoring potentially risky use patterns. Audit log reads require workspace admin role.

## Prompt And Response Logging Limitations

The MVP logs the user question and retrieved document IDs. It does not currently store the full assembled prompt or full context payload. This reduces sensitive context retention, but it also limits forensic detail during model incident review.

Future production deployments should define a clear retention policy for prompts, responses, citations, user feedback, and traces. High-risk environments should support redaction, sampling, legal hold, and tenant-specific retention.

## Known Risks

Prompt injection:
Documents may contain instructions that attempt to override system behavior. The current prompt tells the model to answer from context, but there is no dedicated prompt-injection classifier or document sanitization pipeline.

Data leakage:
Workspace filtering protects normal retrieval, but production deployments also need object-storage permissions, encryption, secret management, strict logging controls, and careful model provider configuration.

Hallucination:
The service refuses when no reliable context is retrieved, but retrieved context may still be incomplete or ambiguous. Users must verify citations for high-impact decisions.

Stale documents:
The platform stores uploaded documents, but it does not yet enforce review dates, ownership workflows, document expiry, or automatic stale-content warnings.

Over-permissioned users:
Workspace admins can add members and grant roles. Production deployments should add approval workflows, just-in-time access, and periodic access reviews.

Model provider risk:
OpenAI-compatible endpoints may be external or local. Production use must confirm contractual, privacy, retention, and regional data-processing requirements.

## Future Mitigations

- Add SSO/OIDC and enterprise identity lifecycle management.
- Add refresh tokens, token revocation, and stronger password policy.
- Add per-document ACLs and document sensitivity labels.
- Add object storage with encryption, signed URLs, and malware scanning.
- Add prompt-injection detection and context sanitization.
- Add citation reranking and answer verification.
- Add document review dates, owners, and stale-content alerts.
- Add redaction for logs, traces, prompts, and feedback.
- Add security dashboards for unusual query patterns.
- Add OpenTelemetry Collector with trace sampling and secure export.

