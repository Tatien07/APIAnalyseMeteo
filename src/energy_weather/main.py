from fastapi import FastAPI

from energy_weather.api.middleware import register_observability_middleware
from energy_weather.api.router import api_router
from energy_weather.core.config import get_settings
from energy_weather.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.app_log_level, settings.app_log_format)
    application = FastAPI(
        title=settings.app_name,
        version="0.9.0",
        description="API d'agrégation de données météo et énergie.",
    )
    register_observability_middleware(application)
    application.include_router(api_router, prefix=settings.api_prefix)
    return application


app = create_app()
