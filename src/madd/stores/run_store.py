import json
from datetime import UTC, datetime
from pathlib import Path

from madd.core.schemas import Citation
from madd.core.state import DebateState


def create_run_dir(base_dir: str = "output") -> Path:
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    run_dir = Path(base_dir) / f"run_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _serialize(val):
    if hasattr(val, 'model_dump'):
        return val.model_dump(mode="json")
    elif isinstance(val, list):
        return [_serialize(v) for v in val]
    elif isinstance(val, dict):
        return {k: _serialize(v) for k, v in val.items()}
    return val


def save_state_snapshot(state: DebateState, run_dir: Path, label: str = "state") -> Path:
    path = run_dir / f"{label}.json"
    data = {k: _serialize(v) for k, v in state.items()}
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return path


def collect_all_citations(state: DebateState) -> list[Citation]:
    seen = set()
    citations = []
    for profile in state.get("profiles", {}).values():
        for c in profile.all_citations():
            if c.id and c.id not in seen:
                seen.add(c.id)
                citations.append(c)
    return citations


def collect_used_citations(state: DebateState) -> list[Citation]:
    cite_index = build_citation_index(state)
    used_ids = set()
    for msg in state.get("messages", []):
        for cid in msg.references_used:
            used_ids.add(cid)
    citations = []
    for cid in used_ids:
        if cid in cite_index:
            citations.append(cite_index[cid])
    return citations


def build_citation_index(state: DebateState) -> dict[str, Citation]:
    return {c.id: c for c in collect_all_citations(state)}


def save_sources(state: DebateState, run_dir: Path) -> Path:
    path = run_dir / "sources.json"
    citations = collect_used_citations(state)
    data = [c.model_dump(mode="json") for c in citations]
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return path


def save_transcript(state: DebateState, run_dir: Path) -> Path:
    path = run_dir / "transcript.md"
    cite_index = build_citation_index(state)
    
    lines = [f"# Debate Transcript\n\n**Scenario**: {state['scenario'].name}\n"]
    
    for msg in state.get("messages", []):
        lines.append(f"\n## Round {msg.round_number} - {msg.country}\n")
        statement = msg.public_statement
        if msg.is_truncated:
            note = msg.truncation_note or "Statement truncated"
            statement = f"{statement}\n\n[Truncation: {note}]"
        lines.append(f"\n{statement}\n")
        
        refs = []
        for cid in msg.references_used:
            if cid in cite_index:
                refs.append(f"[{cid}]")
            else:
                refs.append(f"[{cid}?]")
        sources_line = ", ".join(refs) if refs else "(none)"
        lines.append(f"\n*Sources: {sources_line}*\n")
        
        if msg.proposed_clauses:
            lines.append("\n**Proposed Clauses:**\n")
            for clause in msg.proposed_clauses:
                lines.append(f"- {clause.text}\n")
    
    lines.append("\n---\n\n## References\n\n")
    used_ids = []
    for msg in state.get("messages", []):
        for cid in msg.references_used:
            if cid not in used_ids:
                used_ids.append(cid)
    for cid in used_ids:
        c = cite_index.get(cid)
        if c:
            lines.append(f"- [{cid}] {c.title} ({c.url})\n")
        else:
            lines.append(f"- [{cid}] Unknown source\n")
    
    with open(path, "w") as f:
        f.writelines(lines)
    return path


def save_treaty(state: DebateState, run_dir: Path) -> Path:
    path = run_dir / "treaty.md"
    treaty = state.get("treaty")
    treaty_text = state.get("treaty_text")
    
    if treaty_text:
        lines = [treaty_text.rstrip() + "\n"]
    else:
        lines = ["# Final Treaty Draft\n\n"]
        if treaty:
            if treaty.title:
                lines.append(f"## {treaty.title}\n\n")
            if treaty.preamble:
                lines.append(f"{treaty.preamble}\n\n")
            lines.append("## Accepted Clauses\n\n")
            for clause in treaty.accepted_clauses:
                lines.append(f"**{clause.id}** (proposed by {clause.proposed_by})\n")
                lines.append(f"> {clause.text}\n\n")
            if treaty.pending_clauses:
                lines.append("## Pending/Rejected Clauses\n\n")
                for clause in treaty.clauses:
                    if clause.status.value != "accepted":
                        lines.append(f"- [{clause.status.value}] {clause.text}\n")
        else:
            lines.append("*No treaty was finalized.*\n")
    
    with open(path, "w") as f:
        f.writelines(lines)
    return path


def save_scorecards(state: DebateState, run_dir: Path) -> Path:
    path = run_dir / "scorecards.json"
    scorecards = state.get("scorecards", [])
    data = [s.model_dump(mode="json") for s in scorecards]
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return path


def save_audit(state: DebateState, run_dir: Path) -> Path:
    path = run_dir / "audit.json"
    audit = state.get("audit", [])
    data = [a.model_dump(mode="json") for a in audit]
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return path


def save_clause_ledger(state: DebateState, run_dir: Path) -> Path:
    path = run_dir / "clauses.json"
    treaty = state.get("treaty")
    clauses = treaty.clauses if treaty else []
    data = []
    for c in clauses:
        data.append({
            "id": c.id,
            "text": c.text,
            "proposed_by": c.proposed_by,
            "proposed_round": c.proposed_round,
            "resolved_round": c.resolved_round,
            "status": c.status.value,
            "supporters": list(c.supporters),
            "objectors": list(c.objectors),
            "amendments": list(c.amendments),
            "supersedes": c.supersedes,
        })
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    return path


def save_summary(state: DebateState, run_dir: Path) -> Path:
    path = run_dir / "summary.md"
    scenario = state["scenario"]
    scorecards = state.get("scorecards", [])
    audit = state.get("audit", [])
    treaty = state.get("treaty")
    citations = collect_used_citations(state)
    
    lines = ["# Debate Summary\n\n"]
    lines.append(f"**Scenario**: {scenario.name}\n\n")
    lines.append(f"**Countries**: {', '.join(scenario.countries)}\n\n")
    lines.append(f"**Rounds**: {state.get('round', 0)}\n\n")
    lines.append(f"**Total Sources**: {len(citations)}\n\n")
    
    if scorecards:
        lines.append("## Final Scores\n\n")
        final = scorecards[-1]
        for score in final.scores:
            lines.append(f"- **{score.country}**: {score.score}/10 - {score.reasoning}\n")
    
    if treaty:
        lines.append("\n## Treaty Status\n\n")
        lines.append(f"- Accepted: {len(treaty.accepted_clauses)}\n")
        lines.append(f"- Pending: {len(treaty.pending_clauses)}\n")
    
    if audit:
        lines.append(f"\n## Audit Findings ({len(audit)})\n\n")
        for finding in audit[:5]:
            lines.append(f"- [{finding.severity.value}] {finding.description}\n")
            if finding.evidence:
                lines.append(f"  - Evidence: {', '.join(finding.evidence[:2])}\n")
    
    with open(path, "w") as f:
        f.writelines(lines)
    return path


def save_all_outputs(state: DebateState, run_dir: Path) -> dict[str, Path]:
    return {
        "state": save_state_snapshot(state, run_dir),
        "sources": save_sources(state, run_dir),
        "transcript": save_transcript(state, run_dir),
        "treaty": save_treaty(state, run_dir),
        "scorecards": save_scorecards(state, run_dir),
        "audit": save_audit(state, run_dir),
        "clauses": save_clause_ledger(state, run_dir),
        "summary": save_summary(state, run_dir),
    }
