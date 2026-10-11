import uuid

from tests.helpers import (
    API,
    auth_headers,
    create_job,
    org_slug,
    register_candidate,
    register_recruiter,
)


def test_candidate_cannot_create_job(client):
    register_recruiter(client, "r@acme.com", "Acme")
    register_candidate(client, "c@x.com", org_slug("Acme"))
    r = client.post(
        f"{API}/jobs",
        headers=auth_headers(client, "c@x.com"),
        json={"title": "Hack", "description": "Should not be allowed."},
    )
    assert r.status_code == 403


def test_unauthenticated_cannot_list_jobs(client):
    assert client.get(f"{API}/jobs").status_code == 401


def test_candidate_sees_only_open_jobs(client):
    register_recruiter(client, "r@acme.com", "Acme")
    rh = auth_headers(client, "r@acme.com")
    draft = create_job(client, rh, "Draft job")
    opened = create_job(client, rh, "Open job")
    client.patch(f"{API}/jobs/{opened['id']}", headers=rh, json={"status": "open"})

    register_candidate(client, "c@x.com", org_slug("Acme"))
    ch = auth_headers(client, "c@x.com")

    titles = [j["title"] for j in client.get(f"{API}/jobs", headers=ch).json()["items"]]
    assert titles == ["Open job"]
    assert client.get(f"{API}/jobs/{draft['id']}", headers=ch).status_code == 404


def test_org_b_cannot_see_org_a_jobs(client):
    register_recruiter(client, "a@acme.com", "Acme")
    register_recruiter(client, "b@globex.com", "Globex")
    ha = auth_headers(client, "a@acme.com")
    hb = auth_headers(client, "b@globex.com")
    job = create_job(client, ha)

    assert client.get(f"{API}/jobs", headers=hb).json()["total"] == 0
    assert client.get(f"{API}/jobs/{job['id']}", headers=hb).status_code == 404
    assert (
        client.patch(f"{API}/jobs/{job['id']}", headers=hb, json={"title": "Stolen"}).status_code
        == 404
    )
    # and the owner still sees it untouched
    assert client.get(f"{API}/jobs/{job['id']}", headers=ha).json()["title"] == "AI Engineer"


def test_unknown_job_is_404(client):
    register_recruiter(client, "a@acme.com", "Acme")
    r = client.get(f"{API}/jobs/{uuid.uuid4()}", headers=auth_headers(client, "a@acme.com"))
    assert r.status_code == 404