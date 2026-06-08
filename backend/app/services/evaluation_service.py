from datetime import datetime

from sqlalchemy.orm import Session

from backend.app.auth.rbac import ensure_workspace_role
from backend.app.models.evaluation import EvaluationResult, EvaluationRun, GoldenQAPair
from backend.app.models.user import User
from backend.app.schemas.evaluation import GoldenQACreate
from backend.app.schemas.query import QueryRequest
from backend.app.services.query_service import QueryService


class EvaluationService:
    def __init__(self, db: Session):
        self.db = db

    def create_golden_qa(self, payload: GoldenQACreate, actor: User) -> GoldenQAPair:
        ensure_workspace_role(self.db, actor.id, payload.workspace_id, "admin")
        qa = GoldenQAPair(
            workspace_id=payload.workspace_id,
            question=payload.question,
            expected_answer=payload.expected_answer,
            required_facts=payload.required_facts,
            required_document_ids=payload.required_document_ids,
        )
        self.db.add(qa)
        self.db.commit()
        self.db.refresh(qa)
        return qa

    def run_evaluation(self, workspace_id: str, actor: User) -> EvaluationRun:
        ensure_workspace_role(self.db, actor.id, workspace_id, "admin")
        qas = (
            self.db.query(GoldenQAPair)
            .filter(GoldenQAPair.workspace_id == workspace_id)
            .order_by(GoldenQAPair.created_at.asc())
            .all()
        )
        run = EvaluationRun(
            workspace_id=workspace_id,
            triggered_by_id=actor.id,
            status="running",
            total_questions=len(qas),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        metric_rows: list[dict[str, float]] = []
        query_service = QueryService(self.db)
        try:
            for qa in qas:
                response = query_service.answer_question(
                    QueryRequest(workspace_id=workspace_id, question=qa.question),
                    actor,
                )
                metrics = _score_response(qa, response.answer, response.citations)
                metric_rows.append(metrics)
                self.db.add(
                    EvaluationResult(
                        run_id=run.id,
                        golden_qa_id=qa.id,
                        question=qa.question,
                        answer=response.answer,
                        citations=[citation.model_dump() for citation in response.citations],
                        metrics=metrics,
                    )
                )

            averages = _average_metrics(metric_rows)
            run.status = "completed"
            run.completed_at = datetime.utcnow()
            run.citation_hit_rate = averages["citation_hit_rate"]
            run.answer_contains_required_facts = averages["answer_contains_required_facts"]
            run.retrieval_recall_at_k = averages["retrieval_recall_at_k"]
            run.refusal_rate_when_context_missing = averages["refusal_rate_when_context_missing"]
            self.db.commit()
            self.db.refresh(run)
            return run
        except Exception:
            self.db.rollback()
            run = self.db.get(EvaluationRun, run.id)
            if run:
                run.status = "failed"
                run.completed_at = datetime.utcnow()
                self.db.commit()
                self.db.refresh(run)
            raise

    def list_runs(self, workspace_id: str, actor: User) -> list[EvaluationRun]:
        ensure_workspace_role(self.db, actor.id, workspace_id, "admin")
        return (
            self.db.query(EvaluationRun)
            .filter(EvaluationRun.workspace_id == workspace_id)
            .order_by(EvaluationRun.created_at.desc())
            .limit(25)
            .all()
        )

    def list_results(self, run_id: str, actor: User) -> list[EvaluationResult]:
        run = self.db.get(EvaluationRun, run_id)
        if not run:
            return []
        ensure_workspace_role(self.db, actor.id, run.workspace_id, "admin")
        return (
            self.db.query(EvaluationResult)
            .filter(EvaluationResult.run_id == run_id)
            .order_by(EvaluationResult.created_at.asc())
            .all()
        )


def _score_response(qa: GoldenQAPair, answer: str, citations: list) -> dict[str, float]:
    required_doc_ids = set(qa.required_document_ids or [])
    cited_doc_ids = {citation.document_id for citation in citations}
    required_facts = [fact.lower() for fact in (qa.required_facts or [])]
    answer_lower = answer.lower()

    citation_hit = 1.0 if not required_doc_ids or bool(required_doc_ids & cited_doc_ids) else 0.0
    fact_hit = (
        1.0
        if not required_facts
        else sum(1 for fact in required_facts if fact in answer_lower) / len(required_facts)
    )
    recall = (
        1.0
        if not required_doc_ids
        else len(required_doc_ids & cited_doc_ids) / len(required_doc_ids)
    )
    context_missing_expected = not required_doc_ids and not required_facts
    refused = answer_lower.startswith("i do not know")
    refusal_rate = 1.0 if context_missing_expected and refused else 0.0
    return {
        "citation_hit_rate": citation_hit,
        "answer_contains_required_facts": fact_hit,
        "retrieval_recall_at_k": recall,
        "refusal_rate_when_context_missing": refusal_rate,
    }


def _average_metrics(rows: list[dict[str, float]]) -> dict[str, float]:
    keys = [
        "citation_hit_rate",
        "answer_contains_required_facts",
        "retrieval_recall_at_k",
        "refusal_rate_when_context_missing",
    ]
    if not rows:
        return {key: 0.0 for key in keys}
    return {key: round(sum(row[key] for row in rows) / len(rows), 4) for key in keys}

