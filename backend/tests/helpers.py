from sqlalchemy import select

from app.db.models import Organization
from app.db.session import SessionLocal

PASSWORD = "password123"
API = "/api/v1"


def register_recruiter(client, email: str, org_name: str):
    r = client.post(
        f"{API}/auth/register/recruiter",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "Test Recruiter",
            "organization_name": org_name,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def org_slug(org_name: str) -> str:
    with SessionLocal() as db:
        return db.scalar(select(Organization.slug).where(Organization.name == org_name))


def register_candidate(client, email: str, slug: str):
    r = client.post(
        f"{API}/auth/register/candidate",
        json={
            "email": email,
            "password": PASSWORD,
            "full_name": "Test Candidate",
            "org_slug": slug,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def auth_headers(client, email: str) -> dict:
    r = client.post(f"{API}/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def create_job(client, headers, title="AI Engineer") -> dict:
    r = client.post(
        f"{API}/jobs",
        headers=headers,
        json={"title": title, "description": "Build RAG and agent systems."},
    )
    assert r.status_code == 201, r.text
    return r.json()