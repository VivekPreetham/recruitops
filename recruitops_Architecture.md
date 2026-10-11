# AI Recruitment Operations Platform: Architecture & Implementation Plan

> **Purpose of this file:** the single source of truth for the project. Upload it at the start of a new chat (or when the assistant loses context) so the assistant can continue exactly where we left off.
> **Project name:** working name is `recruitops` (placeholder; the user may rename it, which only affects folder name, FastAPI title, DB name, Docker service names).

---

## 0. Instructions for the AI assistant (read first)

1. **Role:** You are the **instructor** for this project. The user's main goal is to **learn the concepts** (LangGraph, agents, tool calling, HITL, checkpointing, FastAPI, Postgres, etc.), and to finish quickly. There is no fixed deadline.
2. **At the start of every new phase**, explain: what the phase is for, what we will implement, why we implement it, what the need is, and what the user should know.
3. **Whenever a LangGraph concept appears**, explain it very briefly: its role in this project and why we are adding it.
4. **Preferences:**
   - MCQ questions: answer only, no explanation.
   - Pure coding questions: code snippet only, no explanation.
   - When only a subsection of a file changes, give a scoped snippet, not the whole file.
   - Teaching content for phases (intro, concepts, checkpoint questions) is explicitly wanted.
5. **Working style:** give steps in small chunks, ask the user to run them and report output, ask checkpoint questions (answered in the user's own words) before closing a phase. Do not start the next phase until the current one's "Done when" list is satisfied.
6. **Do not regenerate completed phases.** Check the Progress Tracker (section 3).
7. **Core principles (never violate):**
   - The LLM produces *evidence*; **code produces decisions and final scores**.
   - The AI never makes irreversible hiring decisions; every outcome (including "reject recommendation") ends at a human interrupt.
   - Agents never touch the DB directly; they call tools, tools call services, services use repositories.
   - Sensitive attributes are never used in scoring; PII is redacted before LLM calls.
   - Resume text is **untrusted data** (prompt-injection risk).
   - The LLM provider is configurable via env vars; no provider is hard-coded.

---

## 1. Decisions locked

| Item | Decision |
|---|---|
| Frontend | React + Vite + TypeScript (+ Tailwind/shadcn-ui) |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, Pydantic |
| Orchestration | LangGraph (+ LangChain where useful) |
| LLM (dev) | Groq, behind a **provider-agnostic factory** (`LLM_PROVIDER`, `LLM_MODEL` env vars; swap without code changes) |
| Database | PostgreSQL (pgvector image), same DB hosts LangGraph checkpoints in a separate `langgraph` schema |
| Queue / worker | Redis + ARQ |
| File storage | **Local filesystem behind a storage interface** (`save_file`, `get_file`, `get_url`). S3/MinIO implementation can be added later without touching other code. (MinIO was dropped: its Docker image failed to pull.) |
| Multi-tenancy | `organization_id` on users, jobs and derived tables from day one |
| Auth | Argon2id passwords, short-lived JWT access token + rotating refresh token (httpOnly cookie, hash stored server-side) |
| Interview | **Mode A**: candidate types answers asynchronously in the portal (live/voice mode is out of scope; could be added later since evaluation only consumes question + answer text) |
| Timeline | No deadline; finish quickly; learning is the priority |

### Environment notes (current machine)
- OS: Windows, using **Git Bash**. Activate venv with `source .venv/Scripts/activate` (from `backend/`).
- Postgres is exposed on host port **5433** (5432 was already taken). `DATABASE_URL` uses `localhost:5433`.
- `docker-compose.yml` and `.env` live in the **project root**.

---

## 2. Current repo structure

```
recruitops/
├── backend/
│   ├── .venv/
│   ├── alembic/            (env.py reads DB URL from app.core.config.get_settings)
│   ├── alembic.ini
│   ├── app/
│   │   ├── api/routers/
│   │   ├── core/config.py   (pydantic-settings, reads ../.env)
│   │   ├── db/{models,repositories}/
│   │   ├── schemas/  services/  agents/  tools/  infra/  worker/
│   │   ├── orchestration/{graphs,subgraphs}/
│   │   └── main.py          (FastAPI app, GET /health)
│   ├── tests/{unit,integration,workflow,evals}/
│   ├── pyproject.toml (Ruff config)   requirements.txt
├── docker/                 (Dockerfiles later)
├── docs/   evals/
├── docker-compose.yml      (postgres pgvector:pg16 on 5433, redis:7-alpine on 6379)
├── .env   .env.example   .gitignore   README.md
```

Planned additions: `frontend/` (Vite, created in the frontend phase), Dockerfiles, CI workflow.

---

## 3. Progress tracker

| Phase | Status |
|---|---|
| 0. Foundation | **DONE** (Docker up, `/health` works, Alembic connects, Ruff configured). Checkpoint questions pending/optional review. |
| 1. Auth, RBAC, Jobs CRUD, multi-tenancy | NEXT |
| 2. LLM layer + Job Analysis graph (checkpointer + first interrupt) | not started |
| 3. Resume pipeline | not started |
| 4. Candidate Evaluation subgraph + scoring engine | not started |
| 5. Main application graph (routing, HITL, streaming) | not started |
| 6. Rankings, comparison, recruiter frontend | not started |
| 7. Interview subgraph + candidate portal | not started |
| 8. Recruiter AI assistant (tools) | not started |
| 9. Time travel, observability, admin tools | not started |
| 10. Evaluation harness, hardening, docs, deployment | not started |

*(Update this table as phases complete.)*

---

## 4. System architecture

```
┌──────────────┐   REST + SSE   ┌─────────────────────────────────────────┐
│ React + Vite │ ─────────────► │ FastAPI (API layer)                     │
└──────────────┘                │  auth · RBAC · validation · pagination  │
                                └───────┬───────────────────┬─────────────┘
                                        │ enqueue           │ read/write
                                        ▼                   ▼
                                ┌──────────────┐    ┌───────────────────┐
                                │ Redis (ARQ)  │    │ Service layer     │
                                └──────┬───────┘    └─────────┬─────────┘
                                       ▼                      │
                                ┌──────────────────┐          │
                                │ Worker           │          │
                                │ LangGraph runtime│──────────┤
                                │ agents + tools   │          ▼
                                └──────┬───────────┘   ┌──────────────┐
                                       │               │ PostgreSQL   │
                                       ├──────────────►│ app tables + │
                                       │               │ checkpoints  │
                                       ▼               └──────────────┘
                                ┌──────────────┐   ┌──────────────┐
                                │ LLM provider │   │ File storage │
                                └──────────────┘   └──────────────┘
```

**Strict layering (one direction):**
`api → services (business logic) → orchestration (LangGraph) → agents → tools → repositories → DB / external`

The API never calls an LLM directly. It calls a service, which enqueues or resumes a graph run. Normal CRUD stays outside LangGraph.

### Components
- **API:** routers, schemas, auth dependencies, error handlers.
- **Services:** `JobService`, `ApplicationService`, `ResumeService`, `ScoringService` (deterministic), `RankingService`, `InterviewService`, `WorkflowService` (start/resume/inspect graphs), `AuditService`.
- **Orchestration:** graph definitions, state schemas, routing functions (pure, unit-testable), interrupt handlers, retry policies.
- **Agents:** prompt + structured-output schema + thin `run()`. Stateless.
- **Tools:** Pydantic-validated functions; auth context injected from session, never from the LLM.
- **Infra:** LLM factory, storage client, PDF extraction, embeddings, notifications stub, telemetry.

---

## 5. LangGraph architecture

### 5.1 Graph inventory

| Graph | Thread ID | Purpose |
|---|---|---|
| `job_analysis` | `job:{job_id}:v{n}` | JD → structured requirements, recruiter confirmation interrupt |
| `application` (main) | `app:{application_id}` | Whole life of an application |
| ↳ subgraph `candidate_evaluation` | nested in same thread | Parallel analysis → evaluation |
| ↳ subgraph `interview` | nested in same thread | Plan → questions → await answers → evaluate |
| `assistant` | `assistant:{user_id}:{session_id}` | Tool-calling ReAct loop |

One thread per application: the checkpoint history *is* the audit trail, and time travel maps to a real business object.

### 5.2 Main application graph

```
START
  │
  ▼
ingest_resume ─(retry)─► redact_pii ─► [candidate_evaluation subgraph]
                                                │
                                                ▼
                                        apply_business_rules   (deterministic)
                                                │
                                                ▼
                                        route_by_outcome
                   ┌────────────────────────────┼─────────────────────────┐
                   ▼                            ▼                         ▼
          needs_review_flag            recruiter_review_prep      reject_recommendation
          (missing hard req)           (score ≥ threshold)        (score low)
                   └────────────────────────────┼─────────────────────────┘
                                                ▼
                                  ⏸ INTERRUPT: recruiter_decision
                                                │ Command(resume={action, notes, override})
                                    ┌───────────┴───────────┐
                                 reject                   advance
                                    │                        ▼
                                    ▼              [interview subgraph]
                             finalize(rejected)             │
                                                            ▼
                                              route_by_interview_score
                                         ┌──────────┴──────────┐
                                       high                   low
                                         ▼                     ▼
                                   final_review      reject_recommendation
                                         └──────────┬──────────┘
                                                    ▼
                                      ⏸ INTERRUPT: final_decision
                                                    ▼
                                      finalize(hired | rejected)
```

Every path, including "reject recommendation", ends at a human interrupt.

### 5.3 Candidate evaluation subgraph (genuine parallelism)

```
        prepare_context
              │
   ┌──────┬───┴───┬──────────┐      fan-out
   ▼      ▼       ▼          ▼
resume  skills  experience  education
 agent   agent    agent      agent
   └──────┴───┬───┴──────────┘      fan-in: reducer merges into `analyses`
              ▼
        evaluation_agent  → structured evidence + recommendation (NO numeric score)
```

### 5.4 Interview subgraph (Mode A)

```
plan_interview ─► ⏸ approve_plan (recruiter edits rounds/questions)
   ─► generate_questions (per round, parallel via Send)
   ─► ⏸ await_candidate_answers (candidate types answers in portal)
   ─► evaluate_answers (per round, parallel)
   ─► aggregate_interview (deterministic scoring)
   ─► ⏸ interviewer_review (override allowed)
```

### 5.5 Assistant graph

```
START ─► assistant_llm ─(tool_calls?)─► ToolNode ─► assistant_llm ─► END
                          └─ no ─► END
```
Read-only tools, recursion limit, validated inputs.

### 5.6 Why each LangGraph feature is here

| Feature | Business reason |
|---|---|
| Typed state + reducers | Parallel agents write to one state safely |
| Interrupts | Hiring decisions require a human; waits can last days |
| Postgres checkpointer | Survive restarts and multi-day waits |
| Conditional edges | Real routing rules (knockouts, thresholds) |
| Subgraphs | Evaluation and interview are independent, testable units |
| `Send` | Variable number of rounds/questions processed in parallel |
| RetryPolicy | Flaky LLM/PDF/embedding calls |
| Streaming | Live progress UI |
| Time travel | Re-evaluate with new scoring config; debug failures |
| Tool calling | Assistant answers from the DB, not imagination |

---

## 6. State schemas

```python
from typing import Annotated, Literal, TypedDict
from operator import add

def merge_dicts(a: dict, b: dict) -> dict:
    return {**(a or {}), **(b or {})}

class ApplicationState(TypedDict, total=False):
    # identifiers (immutable)
    organization_id: str
    application_id: str
    job_id: str
    candidate_id: str
    scoring_config_version: str

    # data (references/snapshots, not raw resume blobs)
    job_requirements: dict
    candidate_profile: dict                   # PII-redacted
    analyses: Annotated[dict, merge_dicts]    # parallel agent outputs
    evaluation: dict                          # LLM evidence + recommendation
    score_breakdown: dict                     # deterministic result
    outcome: Literal["recruiter_review", "needs_review", "reject_recommended"]

    # human decisions
    recruiter_decision: dict                  # {action, notes, override_reason, decided_by}
    interview: dict
    interview_outcome: str
    final_decision: dict

    # operational
    errors: Annotated[list[dict], add]
    events: Annotated[list[dict], add]        # progress log for streaming
    status: str
```

---

## 7. Agent responsibilities

| Agent | Input | Output (Pydantic) | Must not |
|---|---|---|---|
| JobAnalysis | JD text | `JobRequirements` (required/preferred skills, min/preferred years, education, seniority, domain, location, constraints, responsibilities) | Invent requirements absent from the JD |
| Resume | redacted profile + requirements | completeness, career progression, relevant projects, alignment evidence | Score |
| Skills | requirements + normalized candidate skills | per-skill matched/missing/partial + evidence | Compute match % (code does) |
| Experience | profile + requirements | role/industry relevance ratings, responsibility alignment, evidence | Do years arithmetic |
| Education | profile + requirements | degree/field fit, certifications relevance | Use institution prestige as score input |
| Evaluation | all four outputs | strengths, weaknesses, risks, missing reqs, recommendation (Strong Match / Match / Weak Match / Needs Review), confidence | Output a numeric final score |
| InterviewPlanner | requirements + profile + gaps | rounds, objectives, personalized questions with rationale | Ask generic questions |
| InterviewEvaluator | questions + answers | categorical rubric ratings, evidence, concerns | Output final numeric total |
| Assistant | user query | tool calls + grounded answer | Access DB except through tools |

### LLM vs code separation
LLMs output **categorical rubric ratings** (`strong | adequate | weak | none`). `ScoringService` maps them to numbers using versioned weights:

```python
WEIGHTS_V1 = {"required_skills": .40, "experience": .25,
              "responsibilities": .15, "preferred_skills": .10, "education": .10}
RATING_VALUE = {"strong": 1.0, "adequate": 0.7, "weak": 0.3, "none": 0.0}
```

Deterministic by code: skill-match percentage (via skill alias taxonomy, e.g. `postgres` = `postgresql`), relevant years, weighted final score, routing thresholds. Weights/thresholds are versioned in `scoring_configs`; every evaluation stores the config version and requirements version used.

---

## 8. Tool definitions

All tools: Pydantic input schema, org/user scope injected from session, read-only for the assistant, row-limited, logged.

| Tool | Args | Returns |
|---|---|---|
| `search_candidates` | `job_id?`, `skills[]`, `min_years?`, `min_score?`, `limit≤25` | candidate summaries |
| `get_candidate` | `candidate_id` | redacted profile |
| `get_candidate_evaluation` | `application_id` | score breakdown + evidence |
| `search_jobs` / `get_job` | filters / `job_id` | job + requirements |
| `compare_candidates` | `application_ids[2..5]` | structured comparison |
| `get_application_status` | `application_id` | status + pending human action |
| `get_interview` | `application_id` | plan, status, feedback |
| `generate_interview_questions` | `application_id`, `focus?` | questions (calls planner agent) |
| `explain_ranking` | `app_a`, `app_b` | score deltas by dimension |

State-changing actions (approve/reject/etc.) go through REST with human clicks, never through the assistant.

---

## 9. Database schema (all tenant-scoped tables carry `organization_id`)

```
organizations(id, name, created_at)
users(id, organization_id FK, email UNIQUE, password_hash, role ENUM[recruiter,candidate,admin], is_active, created_at)
refresh_tokens(id, user_id FK, token_hash, expires_at, revoked_at)
candidates(id, organization_id FK, user_id FK UNIQUE, created_at)
resumes(id, candidate_id FK, storage_key, sha256, mime, size, status, uploaded_at)
candidate_profiles(id, candidate_id FK, resume_id FK, parsed JSONB, total_years NUMERIC, parser_version, created_at)
skills(id, canonical_name UNIQUE, category)
skill_aliases(alias UNIQUE, skill_id FK)
candidate_skills(id, profile_id FK, skill_id FK, years NUMERIC, source ENUM[resume,project,cert])

jobs(id, organization_id FK, created_by FK, title, description, status ENUM[draft,open,closed], created_at)
job_requirements(id, job_id FK, version, data JSONB, confirmed_by FK, confirmed_at)
job_requirement_skills(id, job_requirements_id FK, skill_id FK, level ENUM[required,preferred])
scoring_configs(id, organization_id FK, job_id FK NULL, version, weights JSONB, thresholds JSONB)

applications(id, organization_id FK, job_id FK, candidate_id FK, status, current_stage, pending_action,
             thread_id UNIQUE, created_at, UNIQUE(job_id, candidate_id))
evaluations(id, application_id FK, requirements_version, scoring_config_version, llm_output JSONB,
            score_breakdown JSONB, final_score NUMERIC, recommendation, outcome, model, is_replay BOOL, created_at)
evaluation_evidence(id, evaluation_id FK, dimension, claim, evidence_text, source_ref, impact)
recruiter_decisions(id, application_id FK, stage, ai_recommendation, action, notes, override_reason, decided_by FK, decided_at)

interviews(id, application_id FK, status, plan JSONB, created_at)
interview_questions(id, interview_id FK, round_no, text, rationale, targets_skill_id)
interview_answers(id, question_id FK, answer_text, submitted_at)
interview_feedback(id, interview_id FK, ai_evaluation JSONB, final_score, interviewer_override JSONB, decided_by FK)

recruitment_events(id, application_id FK, event_type, actor_type[user|ai|system], actor_id, payload JSONB, created_at)  -- append-only audit
workflow_runs(id, application_id FK, thread_id, graph_name, status, started_at, finished_at, error, trace_id, token_usage JSONB)
```

**Indexes:** `applications(job_id, status)`, `evaluations(application_id, created_at DESC)`, GIN on `candidate_profiles.parsed`, `candidate_skills(skill_id, years)`, `recruitment_events(application_id, created_at)`, `organization_id` on every tenant table.
**Constraints:** CHECK score ranges 0–100, unique `(job_id, candidate_id)`, enums for statuses.

**Multi-tenancy rule:** every query is filtered by the caller's `organization_id` in the repository/service layer (never trusted from the client). Add tests that org A cannot read org B's data.

---

## 10. API specification (prefix `/api/v1`)

| Group | Endpoints |
|---|---|
| Auth | `POST /auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `GET /auth/me` |
| Jobs (recruiter) | `POST/GET /jobs`, `GET/PATCH /jobs/{id}`, `POST /jobs/{id}/analyze`, `POST /jobs/{id}/requirements/confirm` |
| Candidates | `GET /candidates` (filters, pagination), `GET /candidates/{id}`, `GET/PATCH /me/profile` |
| Resumes | `POST /resumes` (multipart), `GET /resumes/{id}`, `GET /resumes/{id}/download` |
| Applications | `POST /jobs/{id}/apply` (candidate), `GET /applications`, `GET /applications/{id}`, `GET /me/applications` |
| Evaluations | `POST /applications/{id}/evaluate`, `GET /applications/{id}/evaluation` |
| Rankings | `GET /jobs/{id}/rankings?sort=&min_score=&skill=` |
| Comparison | `POST /jobs/{id}/compare {application_ids}` |
| Decisions | `POST /applications/{id}/decision {stage, action, notes, override}` → resumes graph |
| Interviews | `GET /applications/{id}/interview`, `POST .../interview/plan/approve`, `POST .../interview/answers` (candidate), `POST .../interview/feedback/decision` |
| Assistant | `POST /assistant/sessions`, `POST /assistant/sessions/{id}/messages` (SSE) |
| Workflow | `GET /workflows/{app_id}/stream` (SSE), `GET /workflows/{app_id}/state`, `GET /workflows/{app_id}/history` (admin), `POST /workflows/{app_id}/replay {checkpoint_id, config_override}` (admin) |

Conventions: pagination, RFC 7807-style errors, `Idempotency-Key` on decision endpoints, `202 Accepted` + `workflow_run_id` for long operations.

---

## 11. Frontend page architecture (React + Vite)

```
/login /register
Recruiter:
  dashboard              pipeline funnel, pending reviews, failed workflows
  jobs                   list + create
  jobs/:id               requirements (edit/confirm), scoring weights, applicants
  jobs/:id/rankings      sortable/filterable table → select for compare
  jobs/:id/compare       side-by-side + AI explanation
  applications/:id       AI evaluation: score breakdown, evidence, concerns,
                         [AI RECOMMENDATION panel] vs [RECRUITER DECISION panel]
  interviews/:id         plan editor, questions, answers, AI evaluation, override
  assistant              chat with visible tool-call traces
  admin/workflows/:id    checkpoint timeline, state diff, replay
Candidate:
  profile, resume, applications, applications/:id (status), interview/:id
```

UI rule: AI output is labeled "AI recommendation (not a decision)" with model/version stamp, visually separate from the recruiter's final decision. Progress uses `EventSource` against the workflow SSE endpoint.

---

## 12. Authentication & authorization

- Argon2id hashing; access JWT (15 min); rotating refresh token (httpOnly, Secure, SameSite cookie) with server-side hash for revocation.
- RBAC: `require_role(...)` dependency + **object-level checks** in services (candidate can only access own rows) + **organization scoping** for recruiters.
- Uploads: PDF only, magic-byte check, size cap, SHA-256 dedupe, random storage keys, access through authorized endpoints/short-lived URLs.
- Resume content is untrusted: defend against prompt injection (and test it).

---

## 13. Planned folder structure (final)

```
recruitops/
├── backend/app/
│   ├── api/ (routers/, deps.py, errors.py)
│   ├── core/ (config.py, security.py, logging.py, telemetry.py)
│   ├── db/ (models/, session.py, repositories/)
│   ├── schemas/   services/   agents/ (prompts/)   tools/   infra/ (llm.py, storage.py, pdf.py, embeddings.py)
│   ├── orchestration/ (state.py, checkpointer.py, retry.py, routing.py, graphs/, subgraphs/)
│   └── worker/arq_worker.py
├── backend/tests/ (unit, integration, workflow, evals)
├── frontend/       (Vite + React + TS)
├── evals/          (datasets, runners, reports)
├── docker/         (backend.Dockerfile, frontend.Dockerfile)
├── docs/   docker-compose.yml   .env.example   README.md
```

---

## 14. Data flow & workflow lifecycle

1. Recruiter creates job → `job_analysis` graph → structured requirements → **interrupt: recruiter confirms/edits** → `job_requirements v1`.
2. Candidate uploads PDF → validated → stored → text extracted by conventional parsers (`pypdf`/`pdfplumber`, regex for email/phone/dates); LLM only parses semantic fields (projects, achievements) → `candidate_profiles`.
3. Candidate applies → `applications` row, `thread_id = app:{id}` → worker starts the graph.
4. Redact PII → parallel agents → evaluation → `ScoringService` → routing → **interrupt**.
5. Recruiter decision via API → `Command(resume=...)` on same thread → continue.
6. Each step writes `recruitment_events`; SSE relays graph updates.

**Application status lifecycle:** `submitted → processing → awaiting_recruiter_review → (rejected | interview_planning → awaiting_candidate → interview_evaluation → awaiting_final_decision → hired | rejected)`, plus `needs_review` and `failed`.

---

## 15. Error / retry strategy

| Failure | Handling |
|---|---|
| LLM timeout / 429 / 5xx | `RetryPolicy` on node: exponential backoff + jitter, 3–4 attempts |
| Invalid structured output | One repair retry (re-prompt with validation error), then fail node |
| PDF extraction failure | Fallback extractor → OCR if image-based → `needs_manual_review` |
| Embedding / external API errors | Same retry policy |
| Non-retryable (validation, auth) | No retry; recorded in `state.errors` |
| Worker crash mid-run | Resume from last checkpoint using the same thread ID |
| Persistent failure | `workflow_runs.status=failed`, admin dashboard entry, manual "retry from checkpoint" |

**Idempotency gotcha:** when a graph resumes from an interrupt, the interrupted node re-executes from its start. Side effects must come *after* `interrupt()` or use idempotency keys.

---

## 16. Human-in-the-loop design

Interrupt points: (1) job requirements confirmation, (2) recruiter review after evaluation, (3) interview plan approval, (4) awaiting candidate answers, (5) interviewer review of AI evaluation, (6) final decision.

```python
def recruiter_decision_node(state):
    decision = interrupt({
        "type": "recruiter_review",
        "ai_recommendation": state["evaluation"]["recommendation"],
        "score": state["score_breakdown"]["final"],
        "allowed_actions": ["advance", "reject", "override_advance", "request_review"],
    })
    validate_decision(decision)   # code validates, not the LLM
    return {"recruiter_decision": decision}
```

Overrides require a reason (auditable; later useful as evaluation data).

---

## 17. Checkpoint & thread strategy

- Thread ID `app:{application_id}` (deterministic). Subgraphs use namespaces under the parent thread.
- Pending interrupts discoverable via `graph.aget_state(config).tasks`; `applications.pending_action` is denormalized for fast dashboards.
- Time travel: `aget_state_history` → admin timeline → `replay` from `checkpoint_id` with optional new scoring config. Replays create a **new evaluation row** (`is_replay=true`); history is never mutated.
- Retention: prune checkpoints of closed applications after N days.

---

## 18. Observability & responsible AI

- `structlog` JSON logs with `organization_id`, `application_id`, `thread_id`, `node`, `run_id`; OpenTelemetry spans per node; callback handler records LLM latency and token usage into `workflow_runs.token_usage`; metrics for retries, failures, time-in-review. Optional: Langfuse.
- Responsible AI: PII (name, gender, photo, DOB, address, etc.) redacted before LLM calls; scoring uses only job-relevant evidence; AI output labeled as recommendation, not truth; bias swap test (same resume, different names/genders → identical deterministic score).

---

## 19. Testing strategy

| Layer | What |
|---|---|
| Unit | scoring engine, skill normalization, routing functions, schema validators |
| Integration | API with httpx + test Postgres, RBAC matrix, **cross-tenant isolation tests** |
| Workflow | Run graphs with a **fake LLM**; assert routing, interrupts, resume, reducers, retries |
| AI evals | Labeled datasets: resume extraction (field F1), skill matching (precision/recall), ranking (Kendall tau/NDCG vs human), tool selection accuracy, interview question quality (LLM-judge + spot checks), interview evaluation, workflow routing |
| Safety | prompt-injection resumes, PII-leak check, bias swap test |

---

## 20. Deployment architecture

`docker-compose`: `frontend`, `api`, `worker`, `postgres` (pgvector), `redis`, optional `otel-collector` / Langfuse. Config via env (`LLM_PROVIDER`, `LLM_MODEL`, `GROQ_API_KEY`, `DATABASE_URL`, `JWT_SECRET`, ...). Commit `.env.example`, never `.env`. CI: ruff + pytest.

---

# IMPLEMENTATION ROADMAP (phases, deliverables, done-when)

Each phase: **Purpose → What we implement → LangGraph concepts → Deliverables → Done when → Checkpoint questions**.

## Phase 0: Foundation (DONE)
- **Purpose:** the "factory floor": reproducible environment, config, migrations, linting.
- **Implemented:** repo layout, docker-compose (Postgres+pgvector on 5433, Redis), typed settings from env, FastAPI `/health`, Alembic wired to settings, Ruff.
- **Checkpoint questions:** (1) Why is the DB URL in `.env` and not hard-coded in `config.py`? (2) Why Alembic instead of `Base.metadata.create_all()`?

## Phase 1: Auth, RBAC, Organizations, Jobs CRUD
- **Purpose:** the secure application layer everything else sits on, with multi-tenancy built in from the start.
- **Implement:** SQLAlchemy base + session dependency; models `organizations`, `users`, `refresh_tokens`, `jobs`; first Alembic migration; Argon2 hashing; JWT access + refresh rotation; `get_current_user`, `require_role`; org-scoped repositories; Jobs CRUD with pagination; error handlers; Pydantic schemas.
- **LangGraph concepts:** none.
- **Deliverables:** register/login/refresh/logout/me; jobs endpoints; tests for auth, RBAC matrix, **cross-org isolation**.
- **Done when:** recruiter in org A cannot see org B's jobs; candidate cannot call recruiter endpoints; refresh rotation works; tests pass; Swagger docs show everything.

## Phase 2: LLM layer + Job Analysis graph (first LangGraph graph)
- **Purpose:** introduce LangGraph with the simplest real use: JD → structured requirements → human confirms.
- **Implement:** provider-agnostic `get_llm()` factory (env-driven, Groq first); structured output with Pydantic `JobRequirements`; skills taxonomy tables + normalization; `JobAnalysis` agent; LangGraph basics (State, nodes, edges, `START/END`); **Postgres checkpointer**; first **`interrupt()`** (recruiter confirms/edits requirements) and `Command(resume=...)`; RetryPolicy on the LLM node; `job_requirements` versioning; endpoints `/jobs/{id}/analyze` and `/requirements/confirm`.
- **LangGraph concepts:** state & nodes, edges, checkpointer, thread_id, interrupt/resume, retry policy.
- **Deliverables:** working analyze→pause→confirm→resume flow; survives API restart while paused; workflow tests with fake LLM.
- **Done when:** you can pause a job analysis, restart the server, and resume it successfully.

## Phase 3: Resume pipeline
- **Purpose:** turn PDFs into trustworthy structured profiles, using conventional parsing where possible.
- **Implement:** storage interface + local implementation; upload validation (magic bytes, size, hash dedupe); text extraction (pypdf/pdfplumber, fallback); regex/NER for deterministic fields; LLM only for semantic fields; PII redaction function; `candidate_profiles`, `candidate_skills`; skill normalization via aliases; ARQ worker for async processing.
- **LangGraph concepts:** none required (optional small ingest graph later); retry used in the ingest step.
- **Deliverables:** `/resumes` upload → parsed profile; redacted view for LLM use; tests on a small set of sample resumes.
- **Done when:** a PDF yields structured profile with skills normalized and PII redacted copy produced.

## Phase 4: Candidate Evaluation subgraph + scoring engine
- **Purpose:** the heart of the project: parallel multi-agent analysis with deterministic scoring.
- **Implement:** four agents + Evaluation agent with structured outputs; subgraph with fan-out/fan-in; reducer-merged state; `ScoringService` with versioned weights/thresholds; evidence persisted to `evaluations` + `evaluation_evidence`; explainable breakdown.
- **LangGraph concepts:** subgraphs, parallel execution, reducers, typed state.
- **Deliverables:** `/applications/{id}/evaluate` produces score + "87 because…" breakdown; scoring unit tests; bias swap test.
- **Done when:** the same input always gives the same score; LLM never outputs the final number; evidence is shown per dimension.

## Phase 5: Main application graph (routing, HITL, streaming)
- **Purpose:** orchestrate the real recruitment lifecycle with human control.
- **Implement:** main graph invoking the evaluation subgraph; conditional edges (needs_review / recruiter_review / reject_recommended); recruiter interrupt + resume via `/decision`; `recruiter_decisions` and `recruitment_events` audit log; `workflow_runs`; SSE streaming of progress; `Idempotency-Key`.
- **LangGraph concepts:** conditional edges, interrupt/resume at scale, streaming modes (`updates`/`custom`), thread-per-application.
- **Deliverables:** full pipeline from application to recruiter decision; pause/resume across days; live progress endpoint.
- **Done when:** every outcome ends at a human decision; resume works after restart; routing tests cover all branches.

## Phase 6: Rankings, comparison, recruiter frontend
- **Purpose:** make it usable; first full UI.
- **Implement:** rankings endpoint (filter/sort/pagination); comparison endpoint + AI comparison explanation; React + Vite app: auth, dashboard, jobs, job details, rankings, compare, application evaluation page (AI recommendation vs recruiter decision panels), SSE progress checklist.
- **Deliverables:** recruiter can run the entire flow in the browser.
- **Done when:** end-to-end demo from job creation to recruiter decision.

## Phase 7: Interview subgraph (Mode A) + candidate portal
- **Purpose:** show deep HITL with multiple pauses and personalized AI planning.
- **Implement:** interview planner (rounds + personalized questions from gaps/projects); plan approval interrupt; parallel question generation (`Send`); candidate portal pages (profile, resume, applications, status, interview answers); await-answers interrupt; per-round parallel evaluation; deterministic aggregation; interviewer override; routing by interview score → final review / reject recommendation; final decision interrupt.
- **LangGraph concepts:** nested subgraph, `Send` (map-reduce), multiple interrupts in one thread.
- **Deliverables:** complete interview flow, candidate and recruiter sides.
- **Done when:** application can travel from "advance" to final outcome with all human checkpoints.

## Phase 8: Recruiter AI assistant
- **Purpose:** tool calling and agent loops: grounded answers, never hallucinated DB facts.
- **Implement:** controlled read-only tools (section 8) with validated inputs and org scoping; ReAct-style assistant graph with `ToolNode`, recursion limit; session memory via thread; SSE chat endpoint; assistant UI with visible tool traces; optional pgvector semantic candidate search.
- **LangGraph concepts:** tool calling, agent loop, ToolNode, conditional "tool or finish" edge, thread-based conversation memory.
- **Deliverables:** answers like "Why was John ranked above Alice?" from real data.
- **Done when:** tool-selection eval set passes; assistant cannot access other orgs' data.

## Phase 9: Time travel, observability, admin tools
- **Purpose:** debugging, auditing and operations.
- **Implement:** checkpoint history API + admin timeline UI; state inspection; replay from checkpoint with config override (creates new evaluation row); structured logging, OTel spans, token/latency tracking into `workflow_runs`; failed-workflow dashboard and retry.
- **LangGraph concepts:** `get_state_history`, `update_state`, replay from `checkpoint_id`.
- **Done when:** you can debug a deliberately failed workflow using only logs + history, and re-score an application with new weights.

## Phase 10: Evaluation harness, hardening, docs, deployment
- **Purpose:** prove quality and make it portfolio-ready.
- **Implement:** eval datasets and runners (resume extraction F1, skill matching P/R, ranking Kendall tau, tool selection accuracy, interview question quality, routing); prompt-injection and PII-leak tests; security review (uploads, authz); Dockerfiles for api/worker/frontend; full docker-compose; CI (ruff + pytest); README with architecture diagrams, ADRs, screenshots, demo video script; checkpoint retention note.
- **Done when:** `docker compose up` runs the whole stack; eval report generated; README explains design decisions (LLM vs code separation, HITL, checkpointing, multi-tenancy).

---

## Appendix A: Concept glossary (quick reference)

- **State / reducer:** shared typed dict; reducer defines how parallel writes merge.
- **Node / edge / conditional edge:** unit of work / transition / transition chosen by a routing function.
- **Checkpointer / thread_id:** persists state after each step; thread_id identifies one workflow's history.
- **Interrupt / Command(resume):** pause for external input; continue with the supplied value.
- **Subgraph:** a graph used as a node inside another graph.
- **Send:** dynamically fan out N parallel tasks (map-reduce).
- **RetryPolicy:** per-node retry with backoff.
- **Streaming:** emit node updates/custom events while running.
- **Time travel:** inspect past checkpoints and re-run from one.

## Appendix B: Known gotchas
- Interrupted nodes re-run from the start on resume → keep side effects idempotent or after `interrupt()`.
- Keep large blobs (resume text) out of graph state; store IDs/references.
- Docker Compose reads `docker-compose.yml` and `.env` from the working directory (project root).
- Postgres host port is 5433; `alembic` and `uvicorn` run from `backend/` with venv activated (`source .venv/Scripts/activate` in Git Bash).
