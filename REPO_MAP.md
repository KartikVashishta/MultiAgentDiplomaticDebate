# Repo Map

## Scope

This repository contains one active app path and one legacy path:

- `src/madd/` is the packaged, tested codebase used by `madd` and `madd-ui`.
- `src/legacy/` is older standalone code kept for reference. It is not the primary execution path.

## Active Entry Points

- `madd = madd.cli:main` from `pyproject.toml`
- `madd-ui = madd.ui.web:main` from `pyproject.toml`
- `src/madd/cli.py` runs a scenario YAML through the LangGraph pipeline and writes outputs.
- `src/madd/ui/web.py` exposes a minimal browser UI that posts pasted YAML into the same pipeline.
- `src/madd/scripts/print_graph_mermaid.py` is a helper script for graph visualization.
- Real runs require `OPENAI_API_KEY`; the active CLI and UI now fail fast with a friendly error if it is missing.

## Core Flow

The main state machine lives in `src/madd/core/graph.py`:

1. `ensure_profiles` builds one profile per country and stores a router plan.
2. `opening_statements` generates round 1 messages.
3. `compile_treaty` converts proposed clauses into treaty state and applies votes.
4. `verify` adds audit findings for unsupported claims and contradictions.
5. `judge` scores the round.
6. The graph loops through `negotiate_round` until `max_rounds` is reached.
7. `refine_treaty` writes the final treaty text.
8. `finalize_report` closes the run.

Key state types are in:

- `src/madd/core/state.py`
- `src/madd/core/schemas.py`
- `src/madd/core/scenario.py`

## Agents

- `src/madd/agents/researcher.py` builds country profiles from search-backed research.
- `src/madd/agents/country.py` generates diplomatic turns, clause proposals, and votes.
- `src/madd/agents/verifier.py` checks claims and contradictions.
- `src/madd/agents/judge.py` scores each round and counts clause outcomes.
- `src/madd/agents/treaty_refiner.py` turns the clause ledger into a treaty draft.

## Tools And Stores

- `src/madd/tools/web_search.py` wraps OpenAI web search and caches results on disk.
- `src/madd/stores/profile_store.py` caches generated country profiles in `data/country_profiles/`.
- `src/madd/stores/run_store.py` writes run artifacts: state, sources, transcript, treaty, scorecards, audit, clause ledger, and summary.
- `src/madd/core/config.py` centralizes settings and environment variables.
- Default output locations follow `MADD_OUTPUT_DIR` when the user does not pass an explicit output path.

## Testing Surface

The `tests/` directory covers the main behavior contracts:

- graph rounds and treaty accounting
- scenario routing
- vote normalization and amendments
- citation handling
- transcript and run-store output
- web search parsing and caching
- CLI parser behavior
- minimal UI scenario execution

## Legacy Path

`src/legacy/` contains older prototypes and prompts, including:

- `src/legacy/run.py`
- `src/legacy/agents/`
- `src/legacy/builder/`
- `src/legacy/parsers/`
- `src/legacy/prompts/`
- `src/legacy/validator/`

Treat this tree as reference material unless the active app is explicitly being migrated.
Start in `src/madd/` for the current packaged codepath.

## Known Weak Spots

- The UI is synchronous and blocking, so it is not a live viewer.
- Real API failure paths are still mostly inferred from tests rather than exercised end-to-end.
- `run_store.create_run_dir()` is collision-safe now, but filesystem output remains the only persistence model.
- `src/legacy/` is easy to confuse with the active code path because it shares domain concepts and naming.
