import hashlib
import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING

from madd.core.config import get_settings
from madd.core.schemas import CountryProfile

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from madd.core.scenario_router import RouterPlan


def _normalize_name(name: str) -> str:
    return name.lower().replace(" ", "_").replace("-", "_")


def _normalize_scenario_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "scenario"


def make_scenario_key(name: str, description: str) -> str:
    slug = _normalize_scenario_name(name)
    digest = hashlib.sha256(description.encode("utf-8")).hexdigest()[:8]
    return f"{slug}_{digest}"


def get_profile_path(country_name: str, scenario_key: str | None = None) -> Path:
    settings = get_settings()
    base_dir = Path(settings.profiles_dir)
    if scenario_key:
        base_dir = base_dir / scenario_key
    return base_dir / f"{_normalize_name(country_name)}.json"


def load_profile(country_name: str, scenario_key: str | None = None) -> CountryProfile | None:
    path = get_profile_path(country_name, scenario_key)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return CountryProfile.model_validate(data)
    except Exception:
        return None


def save_profile(profile: CountryProfile, scenario_key: str | None = None) -> Path:
    path = get_profile_path(profile.facts.name, scenario_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(profile.model_dump_json(indent=2))
    return path


def ensure_profile(
    country_name: str,
    scenario_description: str,
    scenario_name: str | None = None,
    scenario_key: str | None = None,
    router_plan: "RouterPlan | None" = None,
) -> CountryProfile:
    from madd.agents.researcher import generate_profile
    
    cached = load_profile(country_name, scenario_key)
    if cached and cached.all_citations():
        return cached
    if cached and not cached.all_citations():
        logger.warning(f"Cached profile for {country_name} has no citations; regenerating.")
    
    profile = None
    for _attempt in range(2):
        profile = generate_profile(
            country_name,
            scenario_description,
            scenario_name=scenario_name,
            router_plan=router_plan,
        )
        if profile.all_citations():
            break
    if not profile or not profile.all_citations():
        raise ValueError(f"Profile for {country_name} has no citations; cannot proceed.")
    save_profile(profile, scenario_key)
    return profile
