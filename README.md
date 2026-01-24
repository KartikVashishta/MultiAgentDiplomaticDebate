# Multi-Agent Diplomatic Debate (MADD)

A LangGraph-based simulation for orchestrating multi-agent diplomatic debates. Countries negotiate treaties while a judge evaluates and a verifier checks claims.

---

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Run simulation
madd data/scenarios/demo.yaml

# Run tests
pytest tests/
```

---

## Features

- **LangGraph pipeline**: Modular graph with profiles → debate rounds → treaty compilation → verification → judging
- **Role-based models**: Separate model configs for research, turns, judging, verification
- **Web search with citations**: GA OpenAI web_search tool with caching and per-field citations
- **Structured outputs**: Pydantic schemas for all data (profiles, messages, treaties, scorecards, audits)
- **Transcript with references**: Citation IDs resolved to sources in output

---

## Project Structure

```
├── src/madd/              # Main package (canonical)
│   ├── agents/            # Country, Judge, Verifier, Researcher agents
│   ├── core/              # Schemas, config, state, graph, scenario
│   ├── stores/            # Profile and run output persistence
│   └── tools/             # Web search with caching
├── src/legacy/            # Deprecated AgentScope implementation
├── data/
│   ├── scenarios/         # YAML scenario definitions
│   └── country_profiles/  # Cached profile JSON
├── output/                # Run outputs (timestamped dirs)
└── tests/                 # Pytest tests
```

---

## CLI Usage

```bash
# Run with default settings
madd data/scenarios/demo.yaml

# Override max rounds
madd data/scenarios/demo.yaml --rounds 5

# Custom output directory
madd data/scenarios/demo.yaml --output-dir my_output
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | (required) | OpenAI API key |
| `MADD_RESEARCH_MODEL` | `gpt-4o-search-preview` | Model for profile research |
| `MADD_TURN_MODEL` | `gpt-4o` | Model for country turns |
| `MADD_JUDGE_MODEL` | `gpt-4o` | Model for scoring |
| `MADD_VERIFY_MODEL` | `gpt-4o-mini` | Model for verification |
| `MADD_SEARCH_CACHE` | `true` | Enable web search caching |

---

## Output Files

Each run produces `output/run_YYYYMMDD_HHMMSS/`:

| File | Description |
|------|-------------|
| `state.json` | Full state snapshot |
| `sources.json` | All citations used |
| `transcript.md` | Debate with citation references |
| `treaty.md` | Final treaty draft |
| `scorecards.json` | Round-by-round scores |
| `audit.json` | Verifier findings |
| `summary.md` | Executive summary |

---

## Development

```bash
# Install with dev deps
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/
```

---

## Legacy Files

The following files are from the deprecated AgentScope implementation:

- `run.py` - Use `madd` CLI instead
- `requirements.txt` - Use `pip install -e .` instead
- `src/legacy/` - Old agents, memory, prompts, etc.

---

## License

MIT
