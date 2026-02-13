from pathlib import Path

import yaml
from pydantic import BaseModel, Field


class AgendaItem(BaseModel):
    topic: str
    description: str | None = None
    priority: int = Field(default=1, ge=1, le=5)


class Scenario(BaseModel):
    name: str
    description: str
    countries: list[str] = Field(..., min_length=2)
    max_rounds: int = Field(default=3, ge=1, le=10)
    agenda: list[AgendaItem] = Field(default_factory=list)

    # Optional: TODO
    model_name: str | None = None
    temperature: float | None = None


def load_scenario(path: str | Path) -> Scenario:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Scenario file not found: {path}")
    
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    return Scenario.model_validate(data)


def load_scenario_from_text(raw_yaml: str | bytes) -> Scenario:
    data = yaml.safe_load(raw_yaml if isinstance(raw_yaml, str) else raw_yaml.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Scenario YAML must define a mapping with at least name/description/countries")
    return Scenario.model_validate(data)
