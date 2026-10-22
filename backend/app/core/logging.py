"""Structured JSON logging.

Every log line is one JSON object, built with ``json.dumps`` so that a
message containing quotes, backslashes or newlines can never break the
output. The previous formatter pasted ``%(message)s`` into a JSON-looking
template, which produced invalid JSON for any such message.

Each request carries an id so the lines belonging to one request can be
found again. The id is kept in a context variable, so any log call made
while handling a request picks it up without having to thread it through
every call site (R-08: the id is opaque and carries no personal data).
"""
import json
import logging
import uuid
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any

REQUEST_ID_HEADER = "x-request-id"
MAX_REQUEST_ID_LENGTH = 64
# Only these characters may come from a client-supplied id, so a caller
# cannot inject control characters or newlines into the log stream.
_ALLOWED_ID_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.:")

REQUEST_ID: ContextVar[str] = ContextVar("sangad_request_id", default="")

# The attributes every LogRecord carries. Anything else in a record was
# added by the caller through `extra=`.
_STANDARD_RECORD_FIELDS = frozenset(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__.keys()
) | {"message", "asctime", "taskName", "color_message"}


def new_request_id() -> str:
    """Generate a fresh opaque request id."""
    return uuid.uuid4().hex


def sanitize_request_id(value: str) -> str:
    """Return the id if it is safe to log, otherwise a fresh one."""
    trimmed = value.strip()
    if not trimmed or len(trimmed) > MAX_REQUEST_ID_LENGTH:
        return new_request_id()
    if not set(trimmed) <= _ALLOWED_ID_CHARS:
        return new_request_id()
    return trimmed


def get_request_id() -> str:
    """The id of the request being handled, or an empty string."""
    return REQUEST_ID.get()


def set_request_id(value: str) -> Token[str]:
    """Bind the request id to the current context."""
    return REQUEST_ID.set(value)


def reset_request_id(token: Token[str]) -> None:
    """Restore the previous request id."""
    REQUEST_ID.reset(token)


class JsonFormatter(logging.Formatter):
    """Render a log record as a single JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }

        request_id = getattr(record, "request_id", None) or get_request_id()
        if request_id:
            payload["request_id"] = request_id

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Anything the caller passed through `extra=` becomes a field.
        for key, value in record.__dict__.items():
            if key in _STANDARD_RECORD_FIELDS or key.startswith("_"):
                continue
            payload[key] = value

        return json.dumps(payload, default=str)


def setup_uvicorn_logging() -> None:
    """Point uvicorn's own loggers at the JSON formatter.

    uvicorn configures its logging before it imports the application, and
    it writes its start-up lines before the application lifespan runs, so
    this has to be called at import time to catch them.
    """
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        for existing in uvicorn_logger.handlers:
            existing.setFormatter(JsonFormatter())

    # "uvicorn.error" carries no handler of its own and reaches the
    # "uvicorn" handler by propagation. "uvicorn" must then not also reach
    # the root logger, or every line would be written twice.
    logging.getLogger("uvicorn").propagate = False


def setup_logging() -> None:
    """Install the JSON formatter on the root logger and on uvicorn's loggers."""
    root = logging.getLogger()
    for handler in root.handlers:
        if isinstance(handler.formatter, JsonFormatter):
            break
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root.handlers = [handler]
    root.setLevel(logging.INFO)

    setup_uvicorn_logging()
