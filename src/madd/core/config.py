from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")

    model_name: str = Field(default="gpt-4o", alias="MADD_MODEL")
    temperature: float = Field(default=0.7, alias="MADD_TEMPERATURE")
    
    profiles_dir: str = Field(default="data/country_profiles", alias="MADD_PROFILES_DIR")
    scenarios_dir: str = Field(default="data/scenarios", alias="MADD_SCENARIOS_DIR")
    output_dir: str = Field(default="output", alias="MADD_OUTPUT_DIR")
    
    max_retries: int = Field(default=3, alias="MADD_MAX_RETRIES")
    debug: bool = Field(default=False, alias="MADD_DEBUG")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()
