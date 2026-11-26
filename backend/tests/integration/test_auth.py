import pytest

from sqlalchemy import func, select

from app.core.errors import UnauthorizedError
from app.db.models import Candidate, User, UserRole
from app.db.session import SessionLocal
from app.services import auth as auth_service
from tests.helpers import API, PASSWORD, auth_headers, org_slug, register_candidate, register_recruiter


def test_register_login_me(client):
    register_recruiter(client, "a@acme.com", "Acme")
    r = client.get(f"{API}/auth/me", headers=auth_headers(client, "a@acme.com"))
    assert r.status_code == 200
    assert r.json()["role"] == "recruiter"


def test_duplicate_email_is_conflict(client):
    register_recruiter(client, "a@acme.com", "Acme")
    r = client.post(
        f"{API}/auth/register/recruiter",
        json={
            "email": "a@acme.com",
            "password": PASSWORD,
            "full_name": "Dup",
            "organization_name": "Other",
        },
    )
    assert r.status_code == 409


def test_wrong_password_is_401(client):
    register_recruiter(client, "a@acme.com", "Acme")
    r = client.post(f"{API}/auth/login", json={"email": "a@acme.com", "password": "nope-nope"})
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get(f"{API}/auth/me").status_code == 401


def test_register_candidate_creates_candidate_row(client):
    register_recruiter(client, "r@acme.com", "Acme")
    body = register_candidate(client, "c@acme.com", org_slug("Acme"))

    with SessionLocal() as db:
        user = db.get(User, body["id"])
        candidate = db.scalar(select(Candidate).where(Candidate.user_id == user.id))
        assert candidate is not None
        assert candidate.organization_id == user.organization_id
        assert user.role == UserRole.candidate


def test_register_recruiter_does_not_create_candidate_row(client):
    register_recruiter(client, "r@acme.com", "Acme")
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Candidate)) == 0


def test_refresh_token_reuse_revokes_all_sessions(client):
    register_recruiter(client, "a@acme.com", "Acme")
    with SessionLocal() as db:
        _, r1 = auth_service.login(db, email="a@acme.com", password=PASSWORD)
        _, r2 = auth_service.refresh(db, raw_token=r1)  # normal rotation works

        with pytest.raises(UnauthorizedError):
            auth_service.refresh(db, raw_token=r1)  # reusing the old token = suspected theft

        with pytest.raises(UnauthorizedError):
            auth_service.refresh(db, raw_token=r2)  # ...so even the newest token is now dead