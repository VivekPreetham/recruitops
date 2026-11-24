import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.orchestration.graphs.job_analysis import build_job_analysis_graph
from app.schemas.job_requirements import JobRequirements
from app.services import job_analysis as analysis_service
from tests.helpers import (
    API,
    auth_headers,
    create_job,
    org_slug,
    register_candidate,
    register_recruiter,
)

DRAFT = JobRequirements(
    required_skills=["Python", "LangChain"], preferred_skills=["Docker"], seniority="junior"
)


class FakeRateLimit(Exception):
    status_code = 429  # our retry policy treats this as retryable


class FakeLLM:
    """Stands in for the real model. Returns scripted results in order; the last one repeats."""

    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def with_structured_output(self, schema, **kwargs):
        return self

    def invoke(self, messages):
        self.calls += 1
        item = self.results.pop(0) if len(self.results) > 1 else self.results[0]
        if isinstance(item, Exception):
            raise item
        return item


@pytest.fixture
def install_llm(monkeypatch):
    def _install(*results):
        llm = FakeLLM(results)
        saver = InMemorySaver()  # in-memory checkpoints: no Postgres needed for graph state
        monkeypatch.setattr(
            analysis_service, "_graph", lambda: build_job_analysis_graph(saver, llm=llm)
        )
        return llm

    return _install


def _setup(client):
    register_recruiter(client, "r@acme.com", "Acme")
    headers = auth_headers(client, "r@acme.com")
    return headers, create_job(client, headers)


def _confirm_body(extra_skill="Git"):
    data = DRAFT.model_dump()
    data["required_skills"] = [*data["required_skills"], extra_skill]
    return {"requirements": data}


def test_analyze_pauses_for_review(client, install_llm):
    llm = install_llm(DRAFT)
    headers, job = _setup(client)

    r = client.post(f"{API}/jobs/{job['id']}/analyze", headers=headers)

    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "awaiting_review"
    assert body["version"] == 1
    assert body["draft"]["required_skills"] == ["Python", "LangChain"]
    assert llm.calls == 1


def test_confirm_with_edits_saves_version_1(client, install_llm):
    install_llm(DRAFT)
    headers, job = _setup(client)
    client.post(f"{API}/jobs/{job['id']}/analyze", headers=headers)

    r = client.post(
        f"{API}/jobs/{job['id']}/requirements/confirm", headers=headers, json=_confirm_body()
    )

    assert r.status_code == 201
    assert r.json()["version"] == 1
    assert "Git" in r.json()["data"]["required_skills"]  # the recruiter's edit won
    status = client.get(f"{API}/jobs/{job['id']}/analysis", headers=headers).json()
    assert status["status"] == "confirmed"
    assert "Git" in status["requirements"]["required_skills"]


def test_reanalysis_creates_version_2(client, install_llm):
    install_llm(DRAFT)
    headers, job = _setup(client)
    url = f"{API}/jobs/{job['id']}"
    client.post(f"{url}/analyze", headers=headers)
    client.post(f"{url}/requirements/confirm", headers=headers, json=_confirm_body())

    again = client.post(f"{url}/analyze", headers=headers).json()
    assert again["status"] == "awaiting_review"
    assert again["version"] == 2

    r = client.post(f"{url}/requirements/confirm", headers=headers, json=_confirm_body("AWS"))
    assert r.json()["version"] == 2


def test_second_analyze_while_pending_is_409(client, install_llm):
    install_llm(DRAFT)
    headers, job = _setup(client)
    client.post(f"{API}/jobs/{job['id']}/analyze", headers=headers)
    r = client.post(f"{API}/jobs/{job['id']}/analyze", headers=headers)
    assert r.status_code == 409


def test_confirm_without_analysis_is_409(client, install_llm):
    install_llm(DRAFT)
    headers, job = _setup(client)
    r = client.post(
        f"{API}/jobs/{job['id']}/requirements/confirm", headers=headers, json=_confirm_body()
    )
    assert r.status_code == 409


def test_invalid_confirm_body_is_422(client, install_llm):
    install_llm(DRAFT)
    headers, job = _setup(client)
    client.post(f"{API}/jobs/{job['id']}/analyze", headers=headers)
    bad = {"requirements": {**DRAFT.model_dump(), "seniority": "wizard"}}
    r = client.post(f"{API}/jobs/{job['id']}/requirements/confirm", headers=headers, json=bad)
    assert r.status_code == 422


def test_transient_llm_failure_is_retried(client, install_llm):
    llm = install_llm(FakeRateLimit(), DRAFT)  # first call fails with 429, second succeeds
    headers, job = _setup(client)

    r = client.post(f"{API}/jobs/{job['id']}/analyze", headers=headers)

    assert r.status_code == 200
    assert r.json()["status"] == "awaiting_review"
    assert llm.calls == 2


def test_other_org_cannot_touch_the_analysis(client, install_llm):
    install_llm(DRAFT)
    headers, job = _setup(client)
    client.post(f"{API}/jobs/{job['id']}/analyze", headers=headers)

    register_recruiter(client, "b@globex.com", "Globex")
    other = auth_headers(client, "b@globex.com")
    url = f"{API}/jobs/{job['id']}"

    assert client.post(f"{url}/analyze", headers=other).status_code == 404
    assert client.get(f"{url}/analysis", headers=other).status_code == 404
    assert (
        client.post(
            f"{url}/requirements/confirm", headers=other, json=_confirm_body()
        ).status_code
        == 404
    )


def test_candidate_cannot_analyze(client, install_llm):
    install_llm(DRAFT)
    headers, job = _setup(client)
    register_candidate(client, "c@x.com", org_slug("Acme"))
    r = client.post(f"{API}/jobs/{job['id']}/analyze", headers=auth_headers(client, "c@x.com"))
    assert r.status_code == 403