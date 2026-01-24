import json
from pathlib import Path
from typing import Optional

from madd.core.config import get_settings
from madd.core.schemas import CountryProfile


def _normalize_name(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_")


def get_profile_path(country_name: str) -> Path:
    settings = get_settings()
    return Path(settings.profiles_dir) / f"{_normalize_name(country_name)}.json"


def load_profile(country_name: str) -> Optional[CountryProfile]:
    path = get_profile_path(country_name)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return CountryProfile.model_validate(data)
    except Exception:
        return None


def save_profile(profile: CountryProfile) -> Path:
    path = get_profile_path(profile.facts.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(profile.model_dump_json(indent=2))
    return path


def ensure_profile(country_name: str, scenario_description: str) -> CountryProfile:
    from madd.agents.researcher import generate_profile
    
    cached = load_profile(country_name)
    if cached:
        return cached
    
    profile = generate_profile(country_name, scenario_description)
    save_profile(profile)
    return profile
