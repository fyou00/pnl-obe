from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore", hide_input_in_errors=True)

    database_url: SecretStr

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr) -> SecretStr:
        try:
            url = make_url(value.get_secret_value())
            if url.drivername != "postgresql+psycopg" or not url.database:
                raise ValueError
        except Exception as exc:
            raise ValueError(
                "DATABASE_URL harus URL postgresql+psycopg dengan nama database"
            ) from exc
        return value


class Settings(DatabaseSettings):
    jwt_secret_key: SecretStr
    jwt_issuer: str = "pnl-obe"
    jwt_audience: str = "pnl-obe-api"
    access_token_minutes: int = Field(default=30, ge=1, le=1440)
    cors_origins: list[str] = []

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().encode()) < 32:
            raise ValueError("JWT_SECRET_KEY minimal 32 byte; buat nilai acak melalui secrets")
        return value
