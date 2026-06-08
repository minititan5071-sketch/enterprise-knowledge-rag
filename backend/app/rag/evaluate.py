import json
from pathlib import Path

import typer

from backend.app.auth.rbac import ensure_workspace_role
from backend.app.db.session import SessionLocal
from backend.app.models.evaluation import GoldenQAPair
from backend.app.models.user import User
from backend.app.models.workspace import WorkspaceMember
from backend.app.schemas.evaluation import GoldenQACreate
from backend.app.services.evaluation_service import EvaluationService

app = typer.Typer(help="Run Enterprise Knowledge RAG evaluations.")


@app.command()
def run(
    workspace_id: str = typer.Option(..., help="Workspace ID to evaluate."),
    user_email: str | None = typer.Option(
        None, help="Workspace admin email to attribute the run to."
    ),
) -> None:
    db = SessionLocal()
    try:
        actor = _resolve_actor(db, workspace_id, user_email)
        evaluation_run = EvaluationService(db).run_evaluation(workspace_id, actor)
        typer.echo(
            {
                "run_id": evaluation_run.id,
                "status": evaluation_run.status,
                "total_questions": evaluation_run.total_questions,
                "citation_hit_rate": evaluation_run.citation_hit_rate,
                "answer_contains_required_facts": evaluation_run.answer_contains_required_facts,
                "retrieval_recall_at_k": evaluation_run.retrieval_recall_at_k,
                "refusal_rate_when_context_missing": evaluation_run.refusal_rate_when_context_missing,
            }
        )
    finally:
        db.close()


@app.command("load-dataset")
def load_dataset(
    workspace_id: str = typer.Option(..., help="Workspace ID that should receive the QA set."),
    user_email: str | None = typer.Option(
        None, help="Workspace admin email to authorize the import."
    ),
    dataset_path: Path = typer.Option(
        Path("data/eval_sets/fintech_knowledge_eval.json"),
        exists=True,
        file_okay=True,
        dir_okay=False,
        help="Path to a JSON eval dataset.",
    ),
) -> None:
    db = SessionLocal()
    try:
        actor = _resolve_actor(db, workspace_id, user_email)
        imported = load_eval_dataset(db, workspace_id, actor, dataset_path)
        typer.echo({"workspace_id": workspace_id, "imported_or_updated": imported})
    finally:
        db.close()


def load_eval_dataset(db, workspace_id: str, actor: User, dataset_path: Path) -> int:
    ensure_workspace_role(db, actor.id, workspace_id, "admin")
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    items = payload["items"] if isinstance(payload, dict) and "items" in payload else payload
    if not isinstance(items, list):
        raise typer.BadParameter("Evaluation dataset must be a list or an object with an 'items' list")

    imported = 0
    for item in items:
        question = str(item["question"]).strip()
        required_facts = [str(value).strip() for value in item.get("required_facts", []) if value]
        expected_keywords = [
            str(value).strip() for value in item.get("expected_keywords", []) if value
        ]
        expected_source = str(item.get("expected_source_document", "")).strip()
        category = str(item.get("category", "")).strip()
        expected_answer = (
            f"Expected source document: {expected_source}. "
            f"Category: {category}. "
            f"Expected keywords: {', '.join(expected_keywords)}."
        )

        existing = (
            db.query(GoldenQAPair)
            .filter(GoldenQAPair.workspace_id == workspace_id, GoldenQAPair.question == question)
            .first()
        )
        if existing:
            existing.expected_answer = expected_answer
            existing.required_facts = required_facts + expected_keywords
            existing.required_document_ids = []
        else:
            EvaluationService(db).create_golden_qa(
                payload=GoldenQACreate(
                    workspace_id=workspace_id,
                    question=question,
                    expected_answer=expected_answer,
                    required_facts=required_facts + expected_keywords,
                    required_document_ids=[],
                ),
                actor=actor,
            )
        imported += 1

    db.commit()
    return imported


def _resolve_actor(db, workspace_id: str, user_email: str | None) -> User:
    if user_email:
        user = db.query(User).filter(User.email == user_email.lower()).first()
        if not user:
            raise typer.BadParameter("No user found with that email")
        return user

    row = (
        db.query(User)
        .join(WorkspaceMember, WorkspaceMember.user_id == User.id)
        .filter(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.role == "admin")
        .first()
    )
    if not row:
        raise typer.BadParameter("No admin user found for this workspace")
    return row


if __name__ == "__main__":
    app()
