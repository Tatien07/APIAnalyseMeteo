import json
import logging

from energy_weather.core.logging import JsonFormatter, reset_request_id, set_request_id


def test_json_formatter_includes_context_and_structured_fields() -> None:
    record = logging.LogRecord(
        name="energy_weather.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=10,
        msg="Collection completed",
        args=(),
        exc_info=None,
    )
    record.event = "test_completed"
    record.inserted = 12
    token = set_request_id("request-abc")

    try:
        payload = json.loads(JsonFormatter().format(record))
    finally:
        reset_request_id(token)

    assert payload["severity"] == "INFO"
    assert payload["message"] == "Collection completed"
    assert payload["request_id"] == "request-abc"
    assert payload["event"] == "test_completed"
    assert payload["inserted"] == 12
