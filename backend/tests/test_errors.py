"""Tests for the shared error format and request logging."""

import json
import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import BusinessRuleError, NotFoundError, register_error_handlers
from app.core.logging import REQUEST_ID_HEADER, JsonFormatter


class _Signup(BaseModel):
    email: str
    password: str


def _build_app() -> FastAPI:
    """A tiny app with routes that fail in each of the ways we handle."""
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/missing")
    def missing() -> None:
        raise NotFoundError("That listing does not exist.")

    @app.get("/rule")
    def rule() -> None:
        raise BusinessRuleError("Not allowed yet.", details=["Reason one"])

    @app.get("/crash")
    def crash() -> None:
        raise RuntimeError("database password is hunter2")

    @app.post("/signup")
    def signup(body: _Signup) -> _Signup:
        return body

    return app


test_client = TestClient(_build_app(), raise_server_exceptions=False)


def test_a_service_error_becomes_a_tidy_response() -> None:
    response = test_client.get("/missing")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "That listing does not exist.",
            "details": None,
        }
    }


def test_a_rule_violation_carries_its_details() -> None:
    response = test_client.get("/rule")

    assert response.status_code == 422
    assert response.json()["error"] == {
        "code": "rule_violation",
        "message": "Not allowed yet.",
        "details": ["Reason one"],
    }


def test_an_unknown_address_uses_the_same_format() -> None:
    response = test_client.get("/nowhere")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_an_unexpected_crash_reveals_nothing_internal() -> None:
    response = test_client.get("/crash")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "hunter2" not in response.text
    assert "RuntimeError" not in response.text


def test_validation_errors_name_the_field_but_not_the_value() -> None:
    response = test_client.post("/signup", json={"email": "a@example.com", "password": 12345})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert error["details"][0]["field"] == "password"
    # What was typed is never echoed back.
    assert "12345" not in response.text


def test_real_api_responses_carry_a_request_id(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert len(response.headers[REQUEST_ID_HEADER]) == 32


def test_the_real_api_uses_the_error_format_for_unknown_routes(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_json_log_lines_include_extra_fields() -> None:
    record = logging.LogRecord("app.request", logging.INFO, __file__, 1, "GET %s", ("/x",), None)
    record.request_id = "abc123"
    record.status = 200

    entry = json.loads(JsonFormatter().format(record))

    assert entry["message"] == "GET /x"
    assert entry["level"] == "INFO"
    assert entry["request_id"] == "abc123"
    assert entry["status"] == 200
