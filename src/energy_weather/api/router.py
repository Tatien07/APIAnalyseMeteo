from fastapi import APIRouter

from energy_weather.api.routes import analytics, health, measurements

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(measurements.router, prefix="/measurements", tags=["measurements"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
