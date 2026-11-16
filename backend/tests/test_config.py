import secrets

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_config_requires_external_secret_and_postgresql():
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="sqlite:///test.db",
            jwt_secret_key=secrets.token_urlsafe(48),
        )
    with pytest.raises(ValidationError) as exc:
        Settings(
            _env_file=None,
            database_url="postgresql+psycopg://localhost/test",
            jwt_secret_key="short",
        )
    assert "input_value" not in str(exc.value)
    settings = Settings(
        _env_file=None,
        database_url="postgresql+psycopg://localhost/test",
        jwt_secret_key=secrets.token_urlsafe(48),
    )
    assert settings.jwt_secret_key.get_secret_value() not in repr(settings)


@pytest.mark.parametrize("minutes", [0, -1, 1441])
def test_token_expiry_must_be_bounded(minutes):
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            database_url="postgresql+psycopg://localhost/test",
            jwt_secret_key=secrets.token_urlsafe(48),
            access_token_minutes=minutes,
        )
