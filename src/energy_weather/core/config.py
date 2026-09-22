from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Energy Weather Monitor"
    app_env: str = "development"
    app_log_level: str = "INFO"
    app_log_format: Literal["plain", "json"] = "plain"
    api_prefix: str = "/api/v1"
    database_url: str = Field(
        default="postgresql+psycopg://energy_weather:energy_weather@localhost:5432/energy_weather"
    )
    weather_api_url: str = "https://api.open-meteo.com/v1/forecast"
    weather_location_name: str = "paris"
    weather_latitude: float = 48.8566
    weather_longitude: float = 2.3522
    weather_forecast_hours: int = Field(default=24, ge=1, le=168)
    weather_past_hours: int = Field(default=24, ge=0, le=168)
    energy_api_url: str = (
        "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
        "eco2mix-national-tr/records"
    )
    energy_record_limit: int = Field(default=96, ge=1, le=100)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
