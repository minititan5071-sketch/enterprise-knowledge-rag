import typer

from backend.app.db.session import SessionLocal
from backend.app.models.user import User
from backend.app.models.workspace import WorkspaceMember
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

