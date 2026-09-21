FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src

FROM base AS test
RUN pip install --no-cache-dir ".[dev]"
COPY migrations ./migrations
COPY tests ./tests
COPY dashboard ./dashboard
COPY alembic.ini compose.yaml ./
CMD ["pytest"]

FROM base AS production
RUN pip install --no-cache-dir .
COPY alembic.ini ./
COPY migrations ./migrations
EXPOSE 8000
# Cloud Run injecte PORT (8080 par défaut). En local, on conserve le port 8000.
CMD ["sh", "-c", "exec uvicorn energy_weather.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
