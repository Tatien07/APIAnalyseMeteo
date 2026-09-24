from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class WeatherLocation(BaseModel):
    name: str
    latitude: float
    longitude: float


def default_weather_locations() -> list[WeatherLocation]:
    return [
        WeatherLocation(name="paris", latitude=48.8566, longitude=2.3522),
        WeatherLocation(name="lyon", latitude=45.7640, longitude=4.8357),
        WeatherLocation(name="marseille", latitude=43.2965, longitude=5.3698),
        WeatherLocation(name="lille", latitude=50.6292, longitude=3.0573),
        WeatherLocation(name="toulouse", latitude=43.6047, longitude=1.4442),
    ]


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
    weather_locations: list[WeatherLocation] = Field(default_factory=default_weather_locations)
    weather_forecast_hours: int = Field(default=24, ge=1, le=168)
    weather_past_hours: int = Field(default=24, ge=0, le=168)
    energy_api_url: str = (
        "https://odre.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
        "eco2mix-national-tr/records"
    )
    energy_record_limit: int = Field(default=96, ge=1, le=100)
    freshness_threshold_minutes: int = Field(default=180, ge=15, le=1440)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
