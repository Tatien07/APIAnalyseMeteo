import logging
from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response

from energy_weather.core.logging import reset_request_id, set_request_id

logger = logging.getLogger(__name__)


def register_observability_middleware(application: FastAPI) -> None:
    @application.middleware("http")
    async def observe_request(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        request_id = (request.headers.get("X-Request-ID") or str(uuid4()))[:128]
        token = set_request_id(request_id)
        started_at = perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            logger.exception(
                "Request failed",
                extra={
                    "event": "http_request_failed",
                    "http_method": request.method,
                    "http_path": request.url.path,
                },
            )
            raise
        finally:
            logger.info(
                "Request completed",
                extra={
                    "event": "http_request_completed",
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "http_status": status_code,
                    "duration_ms": round((perf_counter() - started_at) * 1000, 2),
                },
            )
            reset_request_id(token)
