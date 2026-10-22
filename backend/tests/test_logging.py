"""Logs must be valid JSON, and every request must carry an id.

The old formatter pasted the message into a JSON-looking template, so a
message containing a quote or a newline produced a line that
``json.loads`` could not read. These tests pin the JSON contract and the
per-request id.
"""
import io
import json
import logging
from http import HTTPStatus

from fastapi.testclient import TestClient

from app.core.logging import (
    REQUEST_ID_HEADER,
    JsonFormatter,
    get_request_id,
    reset_request_id,
    sanitize_request_id,
    set_request_id,
    setup_logging,
)

HOSTILE_MESSAGE = 'he said "hello"\nsecond line\tand a tab\\and a backslash'


def _format_record(message: str) -> str:
    record = logging.LogRecord(
        name="sangad.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=None,
        exc_info=None,
    )
    return JsonFormatter().format(record)


def test_a_log_line_is_valid_json() -> None:
    line = _format_record("plain message")
    assert json.loads(line)["message"] == "plain message"


def test_a_message_with_quotes_and_newlines_is_still_valid_json() -> None:
    line = _format_record(HOSTILE_MESSAGE)
    parsed = json.loads(line)
    assert parsed["message"] == HOSTILE_MESSAGE
    # The raw line must stay on one line so a log shipper sees one record.
    assert "\n" not in line


def test_a_log_line_carries_level_name_and_time() -> None:
    parsed = json.loads(_format_record("hello"))
    assert parsed["level"] == "INFO"
    assert parsed["name"] == "sangad.test"
    assert parsed["time"].endswith("+00:00")


def test_extra_fields_are_included() -> None:
    record = logging.LogRecord(
        name="sangad.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=None,
        exc_info=None,
    )
    record.request_id = "abc-123"
    record.status_code = 200
    parsed = json.loads(JsonFormatter().format(record))
    assert parsed["request_id"] == "abc-123"
    assert parsed["status_code"] == HTTPStatus.OK


def test_the_context_request_id_is_used_when_no_extra_is_given() -> None:
    token = set_request_id("ctx-abc")
    try:
        parsed = json.loads(_format_record("hello"))
        assert parsed["request_id"] == "ctx-abc"
        assert get_request_id() == "ctx-abc"
    finally:
        reset_request_id(token)


def test_setup_logging_installs_the_json_formatter() -> None:
    root = logging.getLogger()
    original_handlers = root.handlers
    original_level = root.level
    try:
        root.handlers = []
        setup_logging()
        assert any(isinstance(h.formatter, JsonFormatter) for h in root.handlers)
        # Calling it twice must not stack duplicate handlers.
        setup_logging()
        assert len(root.handlers) == 1
    finally:
        root.handlers = original_handlers
        root.setLevel(original_level)


def test_setup_logging_makes_the_uvicorn_loggers_json_too() -> None:
    """The whole stream must be JSON, not only the application's own lines."""
    root = logging.getLogger()
    original_handlers = root.handlers
    original_level = root.level
    uvicorn_access = logging.getLogger("uvicorn.access")
    original_access_handlers = uvicorn_access.handlers
    try:
        root.handlers = []
        setup_logging()
        uvicorn_access.addHandler(logging.StreamHandler())
        setup_logging()
        assert uvicorn_access.handlers
        assert all(
            isinstance(h.formatter, JsonFormatter) for h in uvicorn_access.handlers
        )
    finally:
        root.handlers = original_handlers
        root.setLevel(original_level)
        uvicorn_access.handlers = original_access_handlers


def test_a_unsafe_request_id_is_replaced() -> None:
    """A caller must not be able to inject control characters into the log."""
    assert sanitize_request_id("abc-123") == "abc-123"
    hostile = sanitize_request_id("bad id\nwith newline")
    assert hostile != "bad id\nwith newline"
    assert "\n" not in hostile


def test_every_response_carries_a_request_id(api_client: TestClient) -> None:
    response = api_client.get("/healthz")
    assert response.status_code == HTTPStatus.OK
    assert response.headers.get(REQUEST_ID_HEADER)


def test_a_supplied_request_id_is_echoed(api_client: TestClient) -> None:
    response = api_client.get("/healthz", headers={REQUEST_ID_HEADER: "req-abc-123"})
    assert response.headers[REQUEST_ID_HEADER] == "req-abc-123"


def test_an_unsafe_supplied_request_id_is_not_echoed(api_client: TestClient) -> None:
    response = api_client.get("/healthz", headers={REQUEST_ID_HEADER: "bad id with spaces"})
    echoed = response.headers[REQUEST_ID_HEADER]
    assert echoed != "bad id with spaces"
    assert " " not in echoed


def test_the_access_log_is_valid_json_and_carries_the_request_id(
    api_client: TestClient,
) -> None:
    """The full path: middleware -> context -> formatter -> one JSON line."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    access_logger = logging.getLogger("sangad.access")
    previous_level = access_logger.level
    access_logger.addHandler(handler)
    access_logger.setLevel(logging.INFO)
    try:
        api_client.get("/healthz", headers={REQUEST_ID_HEADER: "req-log-1"})
    finally:
        access_logger.removeHandler(handler)
        access_logger.setLevel(previous_level)

    lines = [line for line in stream.getvalue().splitlines() if line.strip()]
    assert lines, "the access log produced no output"
    records = [json.loads(line) for line in lines]
    entry = next(r for r in records if r.get("request_id") == "req-log-1")
    assert entry["method"] == "GET"
    assert entry["path"] == "/healthz"
    assert entry["status_code"] == HTTPStatus.OK
    assert isinstance(entry["duration_ms"], float)
