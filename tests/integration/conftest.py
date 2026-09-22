from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import text

from energy_weather.db.session import engine
from energy_weather.main import app


@pytest.fixture(autouse=True)
async def clean_measurements() -> AsyncIterator[None]:
    async with engine.begin() as connection:
        await connection.execute(text("TRUNCATE TABLE measurements RESTART IDENTITY"))
    yield
    await engine.dispose()


@pytest.fixture
async def api_client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
