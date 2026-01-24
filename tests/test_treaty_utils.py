from madd.core.schemas import Clause, ClauseStatus, TreatyDraft
from madd.core.treaty_utils import get_votable_clauses


def test_get_votable_clauses_filters_by_round():
    treaty = TreatyDraft()
    treaty.clauses = [
        Clause(id="C1", text="Clause 1", proposed_by="A", proposed_round=1),
        Clause(id="C2", text="Clause 2", proposed_by="B", proposed_round=2),
    ]
    treaty.clauses[0].status = ClauseStatus.PROPOSED
    treaty.clauses[1].status = ClauseStatus.PROPOSED

    votable = get_votable_clauses(treaty, current_round=2)

    assert [c.id for c in votable] == ["C1"]
