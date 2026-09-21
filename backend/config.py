"""ORBITIQ global configuration. Single source of truth for env-driven settings."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_name: str = "ORBITIQ"
    simulation_seed: int = 42
    database_url: str = "postgresql://orbitiq:orbitiq@postgres:5432/orbitiq"
    redis_url: str = "redis://redis:6379/0"
    opencellid_api_key: str = ""
    celestrak_url: str = "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=tle"
    noaa_sw_url: str = "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json"
    llm_provider: str = "none"  # none | openai | local
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    demo_mode: bool = True
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    api_key: str = ""

    # Demo scale targets
    demo_devices: int = 10284
    demo_cells: int = 1500
    demo_satellites: int = 24

    # ML
    prediction_horizon_min: int = 5
    model_dir: str = "ml/models/demo"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
