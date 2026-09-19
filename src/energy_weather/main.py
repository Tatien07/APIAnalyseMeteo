from fastapi import FastAPI

from energy_weather.api.router import api_router
from energy_weather.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title=settings.app_name,
        version="0.2.0",
        description="API d'agrégation de données météo et énergie.",
    )
    application.include_router(api_router, prefix=settings.api_prefix)
    return application


app = create_app()
