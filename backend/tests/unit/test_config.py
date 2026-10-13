import pytest
from pydantic import ValidationError

from tests.conftest import make_settings


def test_valid_settings_load() -> None:
    settings = make_settings()
    assert settings.jwt_secret
    assert settings.cors_origin_list == ["http://localhost:5173"]


def test_short_jwt_secret_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(jwt_secret="too-short")


def test_wildcard_cors_origin_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make_settings(cors_origins="*")
    with pytest.raises(ValidationError):
        make_settings(cors_origins="http://localhost:5173, *")


def test_cors_origins_are_split_and_trimmed() -> None:
    settings = make_settings(cors_origins="http://a.test, http://b.test")
    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]


def test_database_url_is_required() -> None:
    with pytest.raises(ValidationError):
        make_settings(database_url=None)
