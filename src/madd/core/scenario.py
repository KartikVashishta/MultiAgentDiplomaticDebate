from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class AgendaItem(BaseModel):
    topic: str
    description: Optional[str] = None
    priority: int = Field(default=1, ge=1, le=5)


class Scenario(BaseModel):
    name: str
    description: str
    countries: list[str] = Field(..., min_length=2)
    max_rounds: int = Field(default=3, ge=1, le=10)
    agenda: list[AgendaItem] = Field(default_factory=list)
    
    # Optional: TODO
    model_name: Optional[str] = None
    temperature: Optional[float] = None


def load_scenario(path: str | Path) -> Scenario:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Scenario file not found: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    return Scenario.model_validate(data)
