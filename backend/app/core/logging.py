"""Structured logging.

"Structured" means every log line is a small JSON object with named fields
(time, level, message, request id, ...) instead of free text. Log tools
can then search and filter by field. In development the lines are printed
as plain readable text instead.

Never log passwords, tokens, document contents or message bodies.
"""

import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from fastapi import FastAPI, Request, Response

REQUEST_ID_HEADER = "X-Request-ID"

# Attributes every log record has. Anything else was passed via `extra=`
# and is included in the JSON output.
_STANDARD_ATTRIBUTES = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, object] = {
            "time": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_ATTRIBUTES:
                entry[key] = value
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging(environment: str) -> None:
    """Set up logging once, when the application starts."""
    handler = logging.StreamHandler()
    if environment == "development":
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
    else:
        handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


def add_request_logging(app: FastAPI) -> None:
    """Log one line per request and tag it with a request id.

    The id is returned in the X-Request-ID response header. When someone
    reports a problem, that id finds the matching log lines.
    """
    logger = logging.getLogger("app.request")

    @app.middleware("http")
    async def log_request(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = uuid.uuid4().hex
        started = time.perf_counter()
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "%s %s -> %s",
            request.method,
            request.url.path,
            response.status_code,
            extra={
                "request_id": request_id,
                "method": request.method,
                # The path only. Query strings can carry personal data.
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            },
        )
        return response
