from madd.core.schemas import Clause, ClauseStatus, TreatyDraft


def get_votable_clauses(treaty: TreatyDraft | None, current_round: int) -> list[Clause]:
    if not treaty:
        return []
    return [
        clause for clause in treaty.clauses
        if clause.status == ClauseStatus.PROPOSED and clause.proposed_round < current_round
    ]


def format_clause_lines(clauses: list[Clause]) -> list[str]:
    return [f"- {c.id}: {c.text} (by {c.proposed_by})" for c in clauses]
