import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status

from backend.app.core.config import settings

try:
    from jose import JWTError, jwt
except Exception:  # pragma: no cover - fallback for minimal local environments
    JWTError = Exception
    jwt = None

try:
    from passlib.context import CryptContext
except Exception:  # pragma: no cover - fallback for minimal local environments
    CryptContext = None


if CryptContext:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
else:
    pwd_context = None


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def get_password_hash(password: str) -> str:
    if pwd_context:
        return pwd_context.hash(password)
    salt = hashlib.sha256(settings.jwt_secret_key.encode()).hexdigest()[:16]
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return f"pbkdf2_sha256${salt}${_b64url(digest)}"


def verify_password(password: str, password_hash: str) -> bool:
    if pwd_context and not password_hash.startswith("pbkdf2_sha256$"):
        return pwd_context.verify(password, password_hash)
    _, salt, expected = password_hash.split("$", 2)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
    return hmac.compare_digest(_b64url(digest), expected)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    expires_delta = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    expires_at = datetime.now(timezone.utc) + expires_delta
    payload: dict[str, Any] = {"sub": subject, "exp": expires_at}
    if jwt:
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    header = {"typ": "JWT", "alg": "HS256"}
    raw_header = _b64url(json.dumps(header, separators=(",", ":")).encode())
    raw_payload = _b64url(
        json.dumps(
            {"sub": subject, "exp": int(expires_at.timestamp())},
            separators=(",", ":"),
        ).encode()
    )
    signing_input = f"{raw_header}.{raw_payload}".encode()
    signature = hmac.new(settings.jwt_secret_key.encode(), signing_input, hashlib.sha256).digest()
    return f"{raw_header}.{raw_payload}.{_b64url(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if jwt:
        try:
            return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        except JWTError as exc:
            raise credentials_error from exc

    try:
        raw_header, raw_payload, raw_signature = token.split(".")
        signing_input = f"{raw_header}.{raw_payload}".encode()
        expected_signature = hmac.new(
            settings.jwt_secret_key.encode(), signing_input, hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_b64url(expected_signature), raw_signature):
            raise ValueError("bad signature")
        payload = json.loads(_b64url_decode(raw_payload))
        if datetime.now(timezone.utc).timestamp() > payload["exp"]:
            raise ValueError("expired")
        return payload
    except Exception as exc:  # pragma: no cover - defensive fallback path
        raise credentials_error from exc

