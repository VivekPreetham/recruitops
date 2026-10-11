import pytest

from app.core.errors import UnauthorizedError
from app.db.session import SessionLocal
from app.services import auth as auth_service
from tests.helpers import API, PASSWORD, auth_headers, register_recruiter


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


def test_refresh_token_reuse_revokes_all_sessions(client):
    register_recruiter(client, "a@acme.com", "Acme")
    with SessionLocal() as db:
        _, r1 = auth_service.login(db, email="a@acme.com", password=PASSWORD)
        _, r2 = auth_service.refresh(db, raw_token=r1)  # normal rotation works

        with pytest.raises(UnauthorizedError):
            auth_service.refresh(db, raw_token=r1)  # reusing the old token = suspected theft

        with pytest.raises(UnauthorizedError):
            auth_service.refresh(db, raw_token=r2)  # ...so even the newest token is now dead