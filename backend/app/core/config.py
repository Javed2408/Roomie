"""Application settings, loaded from environment variables.

Nothing secret is written in this file. Values come from real environment
variables first, and otherwise from the ".env" file in the repository root
(the same file Docker Compose reads).
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy import URL

# backend/app/core/config.py -> parents[3] is the repository root.
REPO_ROOT = Path(__file__).resolve().parents[3]
# Files the running app creates (uploads, development emails). Git-ignored.
VAR_DIR = REPO_ROOT / "backend" / "var"

# The six compatibility factors (see app/services/compatibility.py).
CompatibilityFactorName = Literal["budget", "societies", "lifestyle", "move_in", "room", "food"]
COMPATIBILITY_FACTOR_NAMES: tuple[CompatibilityFactorName, ...] = (
    "budget",
    "societies",
    "lifestyle",
    "move_in",
    "room",
    "food",
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        # The .env file may hold values meant for other tools; ignore them.
        extra="ignore",
    )

    app_name: str = "Roomie API"
    environment: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"

    # --- Database ---
    postgres_user: str = "roomie"
    # No default on purpose: the app refuses to start without a password
    # rather than quietly falling back to a guessable one.
    postgres_password: SecretStr
    # The IPv4 address, not "localhost": Docker publishes the database on
    # 127.0.0.1 only, and "localhost" is tried over IPv6 first on Windows.
    postgres_host: str = "127.0.0.1"
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = "roomie"
    # A separate database used only by the automated tests, so running
    # them can never touch real data. The tests create it if it is missing.
    postgres_test_db: str = "roomie_test"

    # --- Web ---
    # NoDecode lets us accept a plain comma-separated list in the .env file
    # instead of requiring JSON syntax.
    cors_allowed_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]
    # Where the frontend lives. Used to build the links placed in emails.
    frontend_url: str = "http://localhost:3000"

    # --- Sessions and security ---
    # Signs the anti-forgery (CSRF) tokens. Required, like the password.
    secret_key: SecretStr = Field(min_length=32)
    session_cookie_name: str = "roomie_session"
    # A session ends after this long no matter what...
    session_lifetime_hours: int = Field(default=24 * 14, ge=1)
    # ...or sooner, if it has not been used for this long.
    session_idle_hours: int = Field(default=24 * 3, ge=1)
    # "lax" suits a frontend and API on the same site. If they are deployed
    # on unrelated domains, the cookie must be "none" (and is then Secure).
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    email_verification_hours: int = Field(default=48, ge=1)
    password_reset_minutes: int = Field(default=60, ge=5)
    # Limits on repeated attempts (login, sign-up, ...). Only ever turned
    # off for the automated browser tests.
    rate_limits_enabled: bool = True

    # --- Email ---
    # "console" does not send anything: each email is written to a file in
    # `email_outbox_dir` so a developer can read it and click its link.
    email_backend: Literal["console", "smtp"] = "console"
    email_from: str = "Roomie <no-reply@roomie.example>"
    email_outbox_dir: Path = VAR_DIR / "outbox"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None

    # --- Private document storage ---
    # Verification documents are saved here. This folder is never served
    # by the web server; files leave it only through an authorised API.
    storage_dir: Path = VAR_DIR / "private-storage"
    max_upload_bytes: int = Field(default=5 * 1024 * 1024, ge=1024)

    # --- Compatibility scoring (PRD section 8.6) ---
    # How much each factor counts towards the score, in percent. The six
    # values must add up to 100. To change them without editing code, set
    # COMPATIBILITY_WEIGHTS in .env as JSON, for example
    # {"budget": 30, "societies": 25, "lifestyle": 20, "move_in": 10, "room": 10, "food": 5}
    compatibility_weights: dict[CompatibilityFactorName, int] = {
        "budget": 25,
        "societies": 25,
        "lifestyle": 20,
        "move_in": 15,
        "room": 10,
        "food": 5,
    }

    @field_validator("compatibility_weights")
    @classmethod
    def weights_are_complete(
        cls, value: dict[CompatibilityFactorName, int]
    ) -> dict[CompatibilityFactorName, int]:
        missing = set(COMPATIBILITY_FACTOR_NAMES) - set(value)
        if missing:
            raise ValueError(f"COMPATIBILITY_WEIGHTS is missing: {', '.join(sorted(missing))}.")
        if any(weight < 0 for weight in value.values()):
            raise ValueError("COMPATIBILITY_WEIGHTS cannot contain a negative weight.")
        if sum(value.values()) != 100:
            raise ValueError("COMPATIBILITY_WEIGHTS must add up to 100.")
        return value

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def split_comma_separated_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def check_production_is_safe(self) -> Self:
        if self.environment == "production" and self.secret_key.get_secret_value().startswith(
            "change-me"
        ):
            raise ValueError("SECRET_KEY is still the example value. Generate a real one.")
        if self.environment == "production" and self.email_backend == "console":
            raise ValueError(
                "EMAIL_BACKEND=console writes emails to disk and must not be used "
                "in production. Configure SMTP."
            )
        if self.email_backend == "smtp" and not self.smtp_host:
            raise ValueError("EMAIL_BACKEND=smtp needs SMTP_HOST to be set.")
        return self

    @property
    def cookie_secure(self) -> bool:
        """Send the session cookie over HTTPS only, outside local development."""
        return self.environment == "production" or self.session_cookie_samesite == "none"

    def _url_for(self, database: str) -> URL:
        # URL.create escapes special characters in the password, which a
        # hand-built "postgresql://user:pass@host" string would not.
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=database,
        )

    @property
    def database_url(self) -> URL:
        """Connection URL for the application's database."""
        return self._url_for(self.postgres_db)

    @property
    def test_database_url(self) -> URL:
        """Connection URL for the throwaway database the tests use."""
        return self._url_for(self.postgres_test_db)


@lru_cache
def get_settings() -> Settings:
    """Return the settings, reading the environment only once per process."""
    return Settings()
