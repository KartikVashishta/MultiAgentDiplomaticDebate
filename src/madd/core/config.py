from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    
    # Role-based models (override via env vars)
    research_model: str = Field(default="gpt-5-mini", alias="MADD_RESEARCH_MODEL")
    turn_model: str = Field(default="gpt-5-mini", alias="MADD_TURN_MODEL")
    judge_model: str = Field(default="gpt-5-mini", alias="MADD_JUDGE_MODEL")
    verify_model: str = Field(default="gpt-5-mini", alias="MADD_VERIFY_MODEL")
    search_model: str = Field(default="gpt-5-mini", alias="MADD_SEARCH_MODEL")
    
    # Temperature per role
    research_temperature: float = Field(default=0.3, alias="MADD_RESEARCH_TEMP")
    turn_temperature: float = Field(default=0.7, alias="MADD_TURN_TEMP")
    judge_temperature: float = Field(default=0.0, alias="MADD_JUDGE_TEMP")
    
    # Paths
    profiles_dir: str = Field(default="data/country_profiles", alias="MADD_PROFILES_DIR")
    scenarios_dir: str = Field(default="data/scenarios", alias="MADD_SCENARIOS_DIR")
    output_dir: str = Field(default="output", alias="MADD_OUTPUT_DIR")
    
    # Search settings
    search_cache_dir: str = Field(default=".cache/search", alias="MADD_SEARCH_CACHE_DIR")
    search_cache_enabled: bool = Field(default=True, alias="MADD_SEARCH_CACHE")
    
    # Behavior
    max_retries: int = Field(default=3, alias="MADD_MAX_RETRIES")
    debug: bool = Field(default=False, alias="MADD_DEBUG")
    strict_votes: bool = Field(default=False, alias="MADD_STRICT_VOTES")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()


def current_year() -> int:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).year
