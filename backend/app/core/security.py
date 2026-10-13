"""Password hashing and JWT access tokens."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache

import jwt
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

ALGORITHM = "HS256"
REQUIRED_CLAIMS = ["sub", "role", "iat", "exp"]

_password_hash = PasswordHash.recommended()


class TokenError(Exception):
    """The token is missing claims, malformed, forged or expired."""


@dataclass(frozen=True)
class TokenPayload:
    """The verified contents of an access token."""

    user_id: uuid.UUID
    role: str
    issued_at: datetime
    expires_at: datetime


def hash_password(password: str) -> str:
    """Hash a password with argon2 (salted)."""
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return True if the password matches the hash. A malformed hash never matches."""
    try:
        return _password_hash.verify(password, password_hash)
    except (UnknownHashError, ValueError):
        return False


@lru_cache
def _dummy_hash() -> str:
    return _password_hash.hash("dummy-password-for-timing")


def burn_password_check(password: str) -> None:
    """Spend the time of a real check, so an unknown email can't be spotted by timing."""
    _password_hash.verify(password, _dummy_hash())


def create_access_token(
    user_id: uuid.UUID, role: str, secret: str, now: datetime, lifetime: timedelta
) -> str:
    """Create a signed token carrying only sub, role, iat and exp."""
    claims = {
        "sub": str(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + lifetime).timestamp()),
    }
    return jwt.encode(claims, secret, algorithm=ALGORITHM)


def decode_access_token(token: str, secret: str, now: datetime) -> TokenPayload:
    """Verify signature, required claims and expiry against the injected clock."""
    try:
        claims = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            # Expiry is checked below with the injected clock, so tests need no real waiting.
            options={"require": REQUIRED_CLAIMS, "verify_exp": False, "verify_iat": False},
        )
        user_id = uuid.UUID(str(claims["sub"]))
        expires_at = datetime.fromtimestamp(float(claims["exp"]), tz=now.tzinfo)
        issued_at = datetime.fromtimestamp(float(claims["iat"]), tz=now.tzinfo)
    except (jwt.PyJWTError, ValueError, TypeError) as exc:
        raise TokenError("Invalid token") from exc
    if expires_at <= now:
        raise TokenError("Token expired")
    return TokenPayload(
        user_id=user_id, role=str(claims["role"]), issued_at=issued_at, expires_at=expires_at
    )
