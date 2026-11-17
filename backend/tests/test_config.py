"""Tests for settings parsing. These never read the real .env file."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def make_settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "postgres_password": "test-password",
        "secret_key": "k" * 32,
        **overrides,
    }
    return Settings(_env_file=None, **values)


def test_cors_origins_accept_a_comma_separated_string() -> None:
    settings = make_settings(cors_allowed_origins="http://localhost:3000, https://roomie.example ,")

    assert settings.cors_allowed_origins == [
        "http://localhost:3000",
        "https://roomie.example",
    ]


def test_database_url_escapes_special_characters_in_password() -> None:
    settings = make_settings(postgres_password="p@ss/word:1")

    rendered = settings.database_url.render_as_string(hide_password=False)

    assert rendered == "postgresql+psycopg://roomie:p%40ss%2Fword%3A1@127.0.0.1:5432/roomie"


def test_password_is_hidden_when_settings_are_printed() -> None:
    settings = make_settings(postgres_password="super-secret")

    assert "super-secret" not in repr(settings)


def test_missing_password_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_production_refuses_the_example_secret_key() -> None:
    with pytest.raises(ValidationError):
        make_settings(
            environment="production",
            secret_key="change-me-to-64-random-hex-characters",
            email_backend="smtp",
            smtp_host="smtp.example.com",
        )


def test_production_refuses_console_email() -> None:
    with pytest.raises(ValidationError):
        make_settings(environment="production", secret_key="x" * 64)
