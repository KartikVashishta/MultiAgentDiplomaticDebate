from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from madd.core.config import get_settings
from madd.core.state import DebateState
from madd.core.scenario_router import DEFAULT_INSTITUTION_NAME


class TreatyRefinerOutput(BaseModel):
    treaty_text: str = Field(default="")


def refine_treaty(state: DebateState) -> str:
    settings = get_settings()
    llm = ChatOpenAI(
        model=settings.turn_model,
        temperature=0.2,
        api_key=settings.openai_api_key,
        max_retries=settings.max_retries,
    )

    structured_llm = llm.with_structured_output(TreatyRefinerOutput, method="function_calling")
    scenario = state["scenario"]
    treaty = state.get("treaty")
    router_plan = state.get("router_plan")

    institution_name = DEFAULT_INSTITUTION_NAME
    if router_plan and router_plan.institution_name:
        institution_name = router_plan.institution_name

    agenda_items = sorted(scenario.agenda, key=lambda x: x.priority)
    agenda_text = "\n".join(
        f"P{item.priority}: {item.topic} - {item.description or ''}".strip()
        for item in agenda_items
    ) or "None provided."

    clause_lines = []
    if treaty:
        for clause in treaty.clauses:
            clause_lines.append(
                f"{clause.id} [{clause.status.value}] by {clause.proposed_by}: {clause.text}"
                + (f" (supersedes {clause.supersedes})" if clause.supersedes else "")
            )
    clauses_text = "\n".join(clause_lines) if clause_lines else "None."

    legal_hooks = router_plan.legal_hooks if router_plan else []
    treaty_definitions = router_plan.treaty_definitions if router_plan else []
    annex_templates = router_plan.treaty_annex_templates if router_plan else []

    system_prompt = """You are a senior treaty drafter. Turn negotiated clauses into a coherent, publication-ready treaty.

Input:
- Scenario name/description and agenda
- Clause list with IDs, statuses, proposed_by, supersedes/amendments

Goals:
1) Produce a coherent treaty (not a clause list).
2) Integrate ACCEPTED clauses into Articles with consistent terminology and no duplication.
3) Harmonize conflicts by clarifying language without changing substance.
4) Add necessary scaffolding consistent with the scenario:
   - Definitions
   - Oversight body charter (name from scenario, else “Joint Oversight Commission (JOC)”)
   - Dispute resolution with sovereignty carve-outs where applicable
   - Compliance/enforcement
   - Review/sunset
5) Add annexes that fit the scenario:
   - Annex on verification/monitoring and reporting
   - Annex on consultation/grievance procedures (if community/rights issues exist)
   - Annex on implementation timelines
   - Annex on technical standards relevant to the scenario (environmental, arms control, trade controls, etc.)

Rules:
- Only ACCEPTED clauses are binding.
- Keep concise: Preamble + 6–10 articles + annexes.
- Add Clause Mapping: “C12 → Article II(3)”.

Output:
- Title, Preamble, Articles, Annexes, Clause Mapping
"""

    user_prompt = f"""Scenario: {scenario.name}
Description: {scenario.description}
Agenda:
{agenda_text}

Institution name: {institution_name}
Legal hooks mentioned: {", ".join(legal_hooks) or "None"}
Definitions to include (if relevant): {", ".join(treaty_definitions) or "None"}
Annex templates to include (if relevant): {", ".join(annex_templates) or "None"}

Clause list:
{clauses_text}

Draft the treaty now."""

    try:
        result = structured_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
        output = TreatyRefinerOutput.model_validate(result)
    except Exception:
        return ""

    return output.treaty_text.strip()
