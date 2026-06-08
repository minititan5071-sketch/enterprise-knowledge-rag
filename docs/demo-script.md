# Demo Script

Use this script for a 10 minute walkthrough.

1. Start the stack with `docker compose up --build`.
2. Open `http://localhost:8501`.
3. Register and log in as `admin@example.com`.
4. Create `Security Knowledge Base`.
5. Upload a document containing a clear policy fact, such as `Access reviews occur quarterly`.
6. Open the Documents page and confirm ingestion status.
7. Ask `How often do access reviews occur?`.
8. Show the answer, citations, source document names, snippets, and confidence score.
9. Mark the answer as `helpful`.
10. Open Query History and show the audit row.
11. Add a golden QA pair with required fact `quarterly`.
12. Run evaluation and show the metrics.

