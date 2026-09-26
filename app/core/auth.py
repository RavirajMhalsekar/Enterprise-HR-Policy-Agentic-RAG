import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
import jwt
from fastapi import Request, HTTPException, status, Depends
from pydantic import BaseModel, Field
from app.core.config import get_settings

settings = get_settings()


class User(BaseModel):
    username: str
    role: Literal["user", "admin"]


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=256)


class UserProfile(BaseModel):
    username: str
    role: Literal["user", "admin"]


def authenticate_user(username: str, password: str) -> Optional[User]:
    """
    Validates user credentials against configured environment variables
    using constant-time comparison to prevent timing attacks.
    """
    settings = get_settings()
    username_clean = username.strip().lower()

    # Check Admin credentials
    admin_user = (settings.demo_admin_username or "").strip().lower()
    admin_pass = settings.demo_admin_password or ""
    if admin_user and admin_pass:
        if secrets.compare_digest(username_clean, admin_user) and secrets.compare_digest(password, admin_pass):
            return User(username=settings.demo_admin_username, role="admin")

    # Check Standard User credentials
    demo_user = (settings.demo_user_username or "").strip().lower()
    demo_pass = settings.demo_user_password or ""
    if demo_user and demo_pass:
        if secrets.compare_digest(username_clean, demo_user) and secrets.compare_digest(password, demo_pass):
            return User(username=settings.demo_user_username, role="user")

    return None


def create_access_token(user: User, expires_delta: Optional[timedelta] = None) -> str:
    """Creates a signed HS256 JWT access token."""
    settings = get_settings()
    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY is not configured in environment variables.")

    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    payload = {
        "sub": user.username,
        "role": user.role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> User:
    """Decodes and validates the JWT access token."""
    settings = get_settings()
    if not settings.jwt_secret_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT secret key is not configured.",
        )

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        username: Optional[str] = payload.get("sub")
        role: Optional[str] = payload.get("role")

        if not username or role not in ("user", "admin"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload.",
            )

        return User(username=username, role=role)  # type: ignore

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please log in again.",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
        )


def get_current_user(request: Request) -> User:
    """
    FastAPI dependency extracting and validating the JWT from the HttpOnly cookie.
    Falls back to Bearer Authorization header if present.
    """
    settings = get_settings()
    token = request.cookies.get(settings.jwt_cookie_name)

    if not token:
        # Check Authorization header as fallback
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1]

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please log in.",
        )

    return decode_access_token(token)


def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency enforcing admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for this operation.",
        )
    return current_user


def get_optional_current_user(request: Request) -> Optional[User]:
    """Non-raising user resolver for optional authentication states."""
    try:
        return get_current_user(request)
    except HTTPException:
        return None
