import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

SECRET = "s" * 40
NOW = datetime(2030, 1, 1, 12, 0, tzinfo=UTC)
LIFETIME = timedelta(minutes=30)
USER_ID = uuid.uuid4()


def _token() -> str:
    return create_access_token(USER_ID, "admin", SECRET, NOW, LIFETIME)


def test_password_hash_verifies_and_is_salted() -> None:
    first, second = hash_password("correct-horse"), hash_password("correct-horse")
    assert first != second
    assert verify_password("correct-horse", first)
    assert not verify_password("wrong", first)


def test_malformed_hash_never_matches() -> None:
    assert not verify_password("anything", "not-a-real-hash")


def test_token_round_trip() -> None:
    payload = decode_access_token(_token(), SECRET, NOW + timedelta(minutes=5))
    assert payload.user_id == USER_ID
    assert payload.role == "admin"
    assert payload.expires_at == NOW + LIFETIME


def test_token_carries_only_the_expected_claims() -> None:
    claims = jwt.decode(_token(), options={"verify_signature": False})
    assert set(claims) == {"sub", "role", "iat", "exp"}


def test_expired_token_is_rejected() -> None:
    with pytest.raises(TokenError):
        decode_access_token(_token(), SECRET, NOW + LIFETIME)


def test_token_signed_with_another_secret_is_rejected() -> None:
    with pytest.raises(TokenError):
        decode_access_token(_token(), "o" * 40, NOW)


def test_tampered_token_is_rejected() -> None:
    header, body, signature = _token().split(".")
    forged_body = jwt.utils.base64url_encode(b'{"sub":"x","role":"admin","iat":1,"exp":9999999999}')
    with pytest.raises(TokenError):
        decode_access_token(f"{header}.{forged_body.decode()}.{signature}", SECRET, NOW)


def test_garbage_token_is_rejected() -> None:
    with pytest.raises(TokenError):
        decode_access_token("not.a.jwt", SECRET, NOW)


def test_unsigned_token_is_rejected() -> None:
    claims = {"sub": str(USER_ID), "role": "admin", "iat": 1, "exp": 9999999999}
    unsigned = jwt.encode(claims, key=None, algorithm="none")
    with pytest.raises(TokenError):
        decode_access_token(unsigned, SECRET, NOW)


def test_token_missing_a_claim_is_rejected() -> None:
    incomplete = jwt.encode({"sub": str(USER_ID), "iat": 1, "exp": 9999999999}, SECRET, "HS256")
    with pytest.raises(TokenError):
        decode_access_token(incomplete, SECRET, NOW)


def test_token_with_a_non_uuid_subject_is_rejected() -> None:
    claims = {"sub": "not-a-uuid", "role": "admin", "iat": 1, "exp": 9999999999}
    with pytest.raises(TokenError):
        decode_access_token(jwt.encode(claims, SECRET, "HS256"), SECRET, NOW)
