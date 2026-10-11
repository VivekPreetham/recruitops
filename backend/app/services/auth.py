import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import UnauthorizedError, ConflictError, NotFoundError
from app.db.models import UserRole, RefreshToken, User, Organization
from app.core.security import (
    create_access_token,
    generate_refresh_token, 
    hash_password,
    hash_refresh_token,
    verify_password
)

def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60] or "org"

def _unique_slug(db: Session, name: str) -> str:
    slug = _slugify(name)
    while db.scalar(select(Organization.id).where(Organization.slug == slug)):
        slug = f"{_slugify(name)}-{secrets.token_hex(2)}"
    return slug


def _ensure_email_free(db: Session, email: str) -> None:
    if db.scalar(select(User.id).where(User.email == email.lower())):
        raise ConflictError("Email already registered")

def register_recruiter(
    db: Session, 
    *, 
    email: str, 
    password: str,
    full_name: str,
    organization_name: str
) -> User:
    _ensure_email_free(db, email)
    org = Organization(name=organization_name, slug=_unique_slug(db, organization_name))
    db.add(org)
    db.flush()
    user = User(
        organization_id=org.id,
        email=email.lower(),
        password_hash=hash_password(password),
        full_name=full_name,
        role=UserRole.recruiter,
    )
    db.add(user)
    db.commit()
    return user

def register_candidate(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    org_slug: str
) -> User:
    _ensure_email_free(db, email)
    org = db.scalar(select(Organization).where(Organization.slug == org_slug))
    if org is None:
        raise NotFoundError("Organization not found")
    user = User(
        organization_id=org.id,
        email=email.lower(),
        password_hash=hash_password(password),
        full_name=full_name,
        role=UserRole.candidate,
    )
    db.add(user)
    db.commit()
    return user

def _issue_token(
    db: Session,
    user: User
) -> tuple[str, str]:
    s = get_settings()
    access = create_access_token(
        user_id=str(user.id),
        role=user.role.value,
        organization_id=str(user.organization_id)
    )
    raw_refresh = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=datetime.now(UTC) + timedelta(days=s.jwt_refresh_ttl_days),
        )
    )
    db.commit()
    return access, raw_refresh

def login(
    db: Session,
    *,
    email: str,
    password: str
) -> tuple[str, str]:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid email or password")
    return _issue_token(db, user)

def _revoke_all(
        db: Session,
        user_id: uuid.UUID
) -> None:
    now = datetime.now(UTC)
    tokens = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None)
        )
    )

    for t in tokens:
        t.revoked_at = now


def refresh(
    db: Session,
    *,
    raw_token: str
) -> tuple[str, str]:
    row = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token))
    )

    if row is None:
        raise UnauthorizedError("Invalid Refresh Token")

    if row.revoked_at is not None:
        _revoke_all(db, row.user_id)
        db.commit()
        raise UnauthorizedError("Refresh Token reuse detected")

    if row.expires_at < datetime.now(UTC):
        raise UnauthorizedError("Refresh Token Expired")

    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User inactive")

    row.revoked_at = datetime.now(UTC)
    return _issue_token(db, user)


def logout(
    db: Session,
    *,
    raw_token: str | None
) -> None:
    if not raw_token:
        return
    row = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token))
    )
    if row and row.revoked_at is None:
        row.revoked_at = datetime.now(UTC)
        db.commit()