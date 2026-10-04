# HireFlow — Project Specification

This document is the source of truth for the migration of **AutoApply AI**
(`saksham-eng560/autoapply-ai`, commit `8fe0747`, 2 Oct 2026) into **HireFlow**
(`saksham-eng560/HireFlow`). It records every endpoint, table, type, route, component, task, scraper,
submitter, prompt, script and setting in the application. It also serves as the checklist used to
verify the migration (see [Migration verification](#migration-verification) at the end).

The migration is a rebrand. The stack (FastAPI · PostgreSQL 16 + pgvector / SQLite · SQLAlchemy 2.0 ·
JWT · Celery + Redis · Next.js 14 · Playwright · Docker · Caddy · GitHub Actions) and the code are
unchanged. Every file was carried over and only the naming references below were changed, with one
deliberate exception: the Alembic history was squashed (see Section 15).

## Naming map

| AutoApply AI | HireFlow | Where |
|---|---|---|
| `AutoApply AI`, `AutoApply` | `HireFlow` | UI copy, README/PLAN, LICENSE, page titles, PWA + extension manifests, email subjects, Gmail label root, calendar event text |
| `<span>Auto</span>Apply` wordmark | `<span>Hire</span>Flow` | `frontend/src/components/brand.tsx` (`Logo`) |
| `AUTOAPPLY AI` | `HIREFLOW` | prompt / PLAN headings |
| `autoapply_session` | `hireflow_session` | session cookie (`COOKIE_NAME`) |
| `autoapply` (Celery app) · `autoapply.<task>` | `hireflow` · `hireflow.<task>` | `app/worker/*`, `dispatch.send_task` |
| `autoapply` DB name / user / password (dev) | `hireflow` | `.env.example`, `config.py`, compose files, CI, Makefile |
| `autoapply_test` | `hireflow_test` | CI, Makefile |
| `backend/data/autoapply.db` | `backend/data/hireflow.db` | SQLite file for `./start.sh`, `scripts/account.py`, `scripts/internshala_check.py` |
| `autoapply-backend`, `autoapply-frontend` | `hireflow-backend`, `hireflow-frontend` | Docker image tags, ECR repository default |
| `autoapply-api/-worker/-beat` | `hireflow-api/-worker/-beat` | ECS service defaults (`deploy-backend.yml`) |
| compose projects `autoapply`, `autoapply-prod` | `hireflow`, `hireflow-prod` | `docker-compose*.yml` |
| `autoapply-ai-dashboard` | `hireflow-dashboard` | `frontend/package.json`, `package-lock.json` |
| `autoapply-shell-v2` | `hireflow-shell-v2` | service-worker cache (`public/sw.js`) |
| `autoapply-linkedin-sync` | `hireflow-linkedin-sync` | extension alarm name |
| `AutoApply AI — Session Sync` | `HireFlow — Session Sync` | extension `manifest.json` |
| `autoapply:ollama-pull:{model}` | `hireflow:ollama-pull:{model}` | Redis key (`services/ai_setup.py`) |
| `autoapply_interview_id` | `hireflow_interview_id` | Google Calendar event private property |
| `https://manual.autoapply.invalid/` | `https://manual.hireflow.invalid/` | `MANUAL_URL_PREFIX` (applications logged without a link) |
| `autoapply-export-<date>.json` | `hireflow-export-<date>.json` | data export filename |
| `[AutoApply AI]` | `[HireFlow]` | `NOTIFICATION_SUBJECT_PREFIX` (the Gmail monitor ignores these) |
| `autoapply-` / `autoapply-task` / `autoapply-tests-` | `hireflow-` / `hireflow-task` / `hireflow-tests-` | temp-dir and thread-name prefixes |
| `autoapply.example.com` | `hireflow.example.com` | example domain |
| `github.com/saksham-eng560/autoapply-ai`, `~/autoapply-ai` | `github.com/saksham-eng560/HireFlow`, `~/hireflow` | README, `server-setup.sh`, settings page setup command |
| `autoapply-extension.zip` | `hireflow-extension.zip` | CI artifact |

**Intentionally unchanged:**
- The preference key `auto_apply_threshold` (a setting name, not branding).
- The user quote "it doesn't auto apply" in a test docstring.

## Where HireFlow differs from the migration prompt's sketch

The migration prompt was written against an older snapshot of AutoApply AI. Wherever the prompt and the
code disagree, the code wins: nothing is dropped, and later additions are carried over. Specifically:

- **Additional modules present in the source and migrated:**
  - `scrapers/top_companies.py`
  - `services/analytics.py`, `company_catalog.py`, `company_verifier.py`, `cover_letter.py`, `intern_level.py`, `role_focus.py`, `source_mix.py`
  - `hooks/use-popups.ts`
  - the `/dashboard/top-companies` page
  - `scripts/internshala_check.py`
  - Alembic revisions `0005_internshala_user_agent` and `0006_company_check`
  - extra tests (`test_company_check`, `test_intern_level`, `test_internshala_*`, `test_role_focus`, `test_scan_speed`, `test_self_applied` …)
- **Endpoints missing from the prompt's list:**
  - `POST /api/v1/applications/{id}/bot-apply` (Internshala "Apply with the bot")
  - `GET /api/v1/users/me/student`
  - `GET /api/v1/jobs/top-companies`
  - `POST /api/v1/jobs/company-trust`
- **Paths the prompt gives wrongly:** the WebSocket is `/api/v1/ws` and the Gmail webhook is `POST /api/v1/webhooks/gmail`, not `/ws` and `/webhooks/gmail`. Both are declared in `api/files.py`. The frontend, tests and README already use the `/api/v1` paths.
- **Redis channel:** live events use `events:<user_id>`, not `autoapply:events`. There is no product prefix, so the rename does not touch it.
- **The real schema is authoritative.** Section 2 documents the models and migrations as they exist, and they differ from the prompt's table sketch in several places:
  - PostgreSQL enum types and their values
  - `TEXT` vs `VARCHAR` lengths
  - nullability
  - extra columns such as `jobs.company_verdict/company_tier/company_check`, `users.internshala_user_agent`, and `communications.direction/user_id`
- **Paths kept as in the source** (the prompt's tree sketch differs):
  - `backend/alembic.ini` stays at `backend/`, which is where `scripts/migrate.py` runs Alembic from.
  - Extension icons stay at `extension/icons/icon{16,48,128}.png`. There is no `popup.css`; the styles are inline in `popup.html`.
  - `backend/pytest.ini` and `backend/alembic/script.py.mako` are kept.
- **Alembic:** the six source revisions are squashed into one fresh `0001_initial_schema` (Section 15).

---

## Contents

- [Section 1: Complete Backend API Endpoint Registry](#section-1-complete-backend-api-endpoint-registry)
- [Section 2: Complete Database Schema Registry](#section-2-complete-database-schema-registry)
- [Section 3: Custom SQLAlchemy Type Implementations](#section-3-custom-sqlalchemy-type-implementations)
- [Section 4: Security Architecture](#section-4-security-architecture)
- [Section 5: Complete Frontend Route Registry](#section-5-complete-frontend-route-registry)
- [Section 6: Frontend Component Inventory](#section-6-frontend-component-inventory)
- [Section 7: Real-Time Architecture](#section-7-real-time-architecture)
- [Section 8: Background Task Registry (Celery)](#section-8-background-task-registry-celery)
- [Section 9: Scraper Registry](#section-9-scraper-registry)
- [Section 10: Submitter Registry](#section-10-submitter-registry)
- [Section 11: AI/LLM Prompt Files](#section-11-aillm-prompt-files)
- [Section 12: Browser Extension (Manifest V3)](#section-12-browser-extension-manifest-v3)
- [Section 13: Infrastructure & Deployment](#section-13-infrastructure--deployment)
- [Section 14: Complete Environment Variables](#section-14-complete-environment-variables)
- [Section 15: Alembic Migration History](#section-15-alembic-migration-history)
- [Section 16: Test Suite Inventory](#section-16-test-suite-inventory)
- [Migration verification](#migration-verification)

---

## Section 1: Complete Backend API Endpoint Registry

> **Part A**: app shell, health/core, `auth`, `users`, `resumes`, `jobs`, `files`.
> Source of truth: `backend/app/main.py`, `backend/app/api/{deps,auth,users,resumes,jobs,files}.py`, plus the schemas, serializers and services they call.
> The `main.py` mount loop also mounts `applications`, `agent`, `communications`, `interviews`, `analytics` and `review`. Section 1 Part B covers those routers.
> All names below use HireFlow branding. The preference key `auto_apply_threshold` is not branding, so it keeps its name.

**Endpoint count, Part A:** 56 endpoints are defined in application code: 55 HTTP routes and 1 WebSocket. FastAPI also generates 4 documentation routes.

---

### 1.0 Application shell (`backend/app/main.py`)

| Item | Value (HireFlow) |
|---|---|
| FastAPI app | `FastAPI(title="HireFlow", version="1.0.0", description="Autonomous job application agent — human approval required before every submission.", lifespan=lifespan, docs_url="/docs", openapi_url=f"{settings.API_PREFIX}/openapi.json")` (main.py:48-55). `redoc_url` is left at FastAPI's default `/redoc`. |
| API prefix | `settings.API_PREFIX = "/api/v1"` |
| Router mount order (main.py:82-84) | `auth, users, resumes, jobs, applications, agent, communications, interviews, analytics, review, files`. Each one is `app.include_router(router, prefix="/api/v1")`. |
| App-level routes | Only `GET /health` and `GET /health/ready`. **The WebSocket and the Gmail webhook live in the `files.py` router, so their real paths are `/api/v1/ws` and `/api/v1/webhooks/gmail`.** |
| `app.state.limiter` | `limiter` from `app.api.deps` |
| Middleware stack (outermost first) | 1. `security_headers` (`@app.middleware("http")`, main.py:73-79) → 2. `CORSMiddleware` → 3. `SlowAPIMiddleware` → routes. Starlette makes the last-added middleware the outermost one. |
| Security headers (set with `setdefault`, so a handler can override them) | `X-Content-Type-Options: nosniff`; `X-Frame-Options: SAMEORIGIN` (resume PDFs preview in same-origin iframes); `Referrer-Policy: strict-origin-when-cross-origin` |
| CORS | `allow_origins = settings.cors_origins` (CSV `CORS_ORIGINS`, default `http://localhost:3000,http://127.0.0.1:3000`), `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]` |
| Exception handler | `RateLimitExceeded` → `429` `{"detail": f"Rate limit exceeded: {exc.detail}"}`, for example `"Rate limit exceeded: 10 per 1 minute"` (main.py:68-70) |
| Lifespan startup | `wait_for_db` (in a thread) → `create_all` only when `DATABASE_URL` is SQLite (PostgreSQL uses Alembic) → `manager.bind_loop(loop)` → `manager.start_subscriber()` (Redis `psubscribe("events:*")` when Redis is reachable) → `get_llm()` → log `"HireFlow API ready (env=%s, llm=%s, db=%s)"`. `llm` is the provider names or `"heuristics-only"`. In production, each `settings.validate_for_production()` problem is logged as `"CONFIG: %s"`. |
| Lifespan shutdown | `manager.stop_subscriber()` |
| Error body format | `HTTPException` → `{"detail": "<string>"}`. Pydantic request validation → FastAPI default `422` `{"detail": [{"type","loc","msg","input",...}]}`. |
| Transaction semantics | `get_db()` (core/database.py:149) yields one `SessionLocal` per request. It **commits after the handler returns** and rolls back on an exception. Every handler write is therefore atomic per request. `enqueue(..., after_commit=db)` fires only after this commit. |

---

### 1.1 Authentication modes (`api/deps.py`, `core/security.py`)

**JWT mechanics** (`core/security.py`):
- Algorithm `HS256`, signed with `settings.SECRET_KEY`.
- Claims: `sub`, `scope`, `iat`, `exp`, `jti` (`secrets.token_hex(8)`, 16 hex characters), plus any `extra` claims.
- The default lifetime is `ACCESS_TOKEN_EXPIRE_MINUTES = 10080` (7 days).
- `decode_token(token, expected_scopes)` raises `TokenError` with exactly one of these messages:
  - `"Token expired"`
  - `"Invalid token"` (any other PyJWT error)
  - `"Token scope not allowed here"` (the `scope` claim is not in `expected_scopes`)

**Token scopes**

| Scope | Minted by | Lifetime | `sub` | Accepted by |
|---|---|---|---|---|
| `access` | `POST /auth/register`, `POST /auth/login`, `GET /auth/google/callback` (login mode), all via `_set_session` | 7 days (`ACCESS_TOKEN_EXPIRE_MINUTES=10080`) | user UUID | `CurrentUser`, `ExtensionUser`, WebSocket |
| `ws` | `GET /auth/ws-token` | 5 minutes | user UUID | WebSocket `/api/v1/ws` only |
| `extension` | `POST /auth/extension-token` | `EXTENSION_TOKEN_EXPIRE_DAYS = 180` days | user UUID | `ExtensionUser` only (2 endpoints) |
| `oauth_state` | `google_oauth.build_auth_url` (`/auth/google/login`, `/auth/google/connect`) | 15 minutes | user UUID (connect) or `"anonymous"` (login), plus extra claims `mode` (`"login"`/`"connect"`) and `next` | `GET /auth/google/callback` (`state` query param) only |

**Token transport** (`deps._extract_token`):
1. The `Authorization: Bearer <jwt>` header wins. The prefix check is case-insensitive (`"bearer "`), and the value after it is stripped.
2. Otherwise the cookie **`hireflow_session`** (`settings.COOKIE_NAME`) is used.

A Bearer header is used even when a valid cookie is also present. For example, an extension token in the header on a `CurrentUser` route gives `401 "Token scope not allowed here"`.

**Session cookie** (`auth._set_session`, auth.py:27-33):

| Attribute | Value |
|---|---|
| Name | `hireflow_session` |
| Value | the `access` JWT |
| `HttpOnly` | yes |
| `Secure` | `settings.COOKIE_SECURE` (default `False`) |
| `SameSite` | `Lax` |
| `Max-Age` | `ACCESS_TOKEN_EXPIRE_MINUTES*60` = `604800` |
| `Path` | `/` |

The same token is also returned in the JSON body as `access_token`.

**Dependency aliases**
- `CurrentUser = Annotated[User, Depends(get_current_user)]` accepts scope `("access",)` only.
- `ExtensionUser = Annotated[User, Depends(get_current_user_or_extension)]` accepts scopes `("access", "extension")`.
- `DB = Annotated[Session, Depends(get_db)]`.
- `parse_uuid(value)` raises `404 {"detail": "Not found"}` for a malformed UUID path id.

**Auth failures**: every case returns `401`, with no `WWW-Authenticate` header.
- `"Not authenticated"`: no token was found.
- `"Token expired"`, `"Invalid token"` or `"Token scope not allowed here"`: these come from `decode_token`.
- `str(ValueError)`, for example `"badly formed hexadecimal UUID string"`: the `sub` claim is not a valid UUID.
- `"'sub'"` (the `str(KeyError)`): the `sub` claim is missing.
- `"User not found or inactive"`: no user row exists, or `is_active` is `False`.

**Other security facts**
- Password hashing (`hash_password`): `bcrypt.hashpw(base64(sha256(password)), gensalt(rounds=12))`. The SHA-256 pre-hash supports passphrases longer than 72 bytes.
- There is no CSRF token. Protection relies on `SameSite=Lax` plus the CORS allowlist.
- There is no server-side token revocation. Logout only deletes the cookie, and a password change does not invalidate existing JWTs.
- Encrypted columns (AES-256-GCM, `v1:` prefix): `google_access_token`, `google_refresh_token`, `linkedin_session_cookie` (`EncryptedText`); `internshala_session`, `ats_credentials` (`EncryptedJSON`).

**Auth labels used in the tables below**

| Label | Meaning |
|---|---|
| `none` | No authentication |
| `access` | Cookie `hireflow_session` or `Authorization: Bearer`, scope `access` only (`CurrentUser`) |
| `access\|extension` | Same transport, scope `access` or `extension` (`ExtensionUser`) |
| `ws\|access` | WebSocket query `?token=` or cookie, scope `ws` or `access` |
| `oauth_state` | Signed `state` query param |
| `pubsub-token` | Shared secret in `?token=` |

---

### 1.2 Rate limiting (`api/deps.py:14-23`, `main.py:57-70`)

```python
def _rate_key(request):
    token = request.cookies.get(settings.COOKIE_NAME) or request.headers.get("authorization", "")
    return f"{get_remote_address(request)}:{hash(token) if token else ''}"

limiter = Limiter(key_func=_rate_key, default_limits=[settings.RATE_LIMIT_DEFAULT],
                  storage_uri=settings.REDIS_URL if settings.REDIS_URL and not settings.is_sqlite else "memory://",
                  enabled=settings.ENVIRONMENT != "test")
```

**Configuration**
- **Default:** `RATE_LIMIT_DEFAULT = "300/minute"`. `SlowAPIMiddleware` applies it to every HTTP route that has no `@limiter.limit` decorator, including `/health`, `/health/ready`, the docs routes and `/api/v1/webhooks/gmail`. The WebSocket is not rate-limited, because the middleware is HTTP-only.
- **Explicit limits:** a decorator replaces the default for its route. There are four:

  | Route | Decorator |
  |---|---|
  | `POST /api/v1/auth/register` | `@limiter.limit("10/minute")` |
  | `POST /api/v1/auth/login` | `@limiter.limit("20/minute")` |
  | `POST /api/v1/users/me/integrations/llm/test` | `@limiter.limit("10/minute")` |
  | `POST /api/v1/users/me/integrations/ollama/pull` | `@limiter.limit("10/minute")` |

  Each decorated handler takes `request: Request`, which SlowAPI requires.
- **Storage:** Redis (`REDIS_URL`) unless the database is SQLite or `REDIS_URL` is empty. In those cases it is `memory://`, which is per process.
- **Disabled** when `ENVIRONMENT == "test"`.

**Bucket key behavior**
- The key is `"<client IP>:<hash(token)>"`.
- The token for the key is the **cookie first, then the raw `Authorization` header**. This is the reverse of the auth precedence.
- Anonymous callers are keyed as `"<ip>:"`.
- Python's `hash()` of a `str` is salted per process unless `PYTHONHASHSEED` is fixed. With several API processes sharing Redis, one client therefore gets a different bucket in each process. This is existing behavior and should be preserved, not fixed.

**Over the limit:** `429 {"detail": "Rate limit exceeded: <N> per 1 minute"}`. No `X-RateLimit-*` headers are sent, because SlowAPI's `headers_enabled` defaults to `False`.

---

### 1.3 Shared response shapes (`api/serializers.py`)

**File URL helper:** `file_url(key) = f"/api/v1/files/{urllib.parse.quote(key)}"`, or `null`. Storage keys look like `users/<user_uuid>/<folder>/<hex>.<ext>`.

**`UserOut`** (`user_out`, serializers.py:36-52)

| Field | Type / source |
|---|---|
| `id` | `str(UUID)` |
| `email` | str |
| `full_name` | str |
| `phone` | str \| null |
| `location` | str \| null |
| `linkedin_url` | str \| null |
| `has_password` | bool (`hashed_password` set) |
| `google_connected` | bool (refresh token or access token present) |
| `google_email` | str \| null |
| `linkedin_connected` | bool (`linkedin_session_cookie` present) |
| `linkedin_session_valid` | bool |
| `preferences` | object: `user.prefs`, the stored preferences merged over `DEFAULT_PREFERENCES` |
| `last_scan_at` | ISO-8601 \| null |
| `created_at` | ISO-8601 \| null |

**`ResumeOut`** (`resume_out(resume, include_content=True)`, serializers.py:130-147)

| Field | Type |
|---|---|
| `id` | str |
| `label` | str \| null |
| `original_filename` | str \| null |
| `is_master` | bool |
| `version` | int |
| `parent_resume_id` | str \| null |
| `tailored_for_job_id` | str \| null |
| `changes_made` | list[str] (`[]` default) |
| `pdf_url` | `file_url(resume.pdf_url)` |
| `original_file_url` | `file_url(resume.original_file_url)` |
| `created_at`, `updated_at` | ISO \| null |
| `parsed_content` | object. Only present when `include_content=True`. |

`parsed_content` follows the `ResumeContent` schema in `schemas/resume_content.py` (extra keys ignored, strings stripped, lists de-duplicated):
- `personal_info{name,email,phone,location,linkedin,github,portfolio}`
- `summary`
- `education[{institution,degree,field,gpa,start_date,end_date,highlights[]}]`
- `experience[{company,title,start_date,end_date,location,bullets[]}]`
- `projects[{name,description,technologies[],url}]`
- `skills{technical[],languages[],tools[],soft_skills[]}`
- `certifications[{name,issuer,date}]`
- `awards[]`

**`JobOut`** (`job_out(job, application=None, prefs=None)`, serializers.py:58-92)

| Field | Type / notes |
|---|---|
| `id` | str |
| `company_name`, `company_logo_url`, `role_title`, `location` | str \| null |
| `is_remote` | bool \| null |
| `job_type` | enum value: `full-time`, `part-time`, `internship`, `contract`, `freelance` |
| `experience_level` | enum value: `entry`, `mid`, `senior`, `lead`, `executive`, `internship` |
| `salary_min`, `salary_max`, `salary_currency` | number / str \| null |
| `source_url` | str \| null. **`null` when it starts with `MANUAL_URL_PREFIX = "https://manual.hireflow.invalid/"`** (an application logged without a link). |
| `source_platform` | `ATSPlatform` value: `linkedin`, `indeed`, `glassdoor`, `wellfound`, `greenhouse`, `lever`, `workday`, `ashby`, `bamboohr`, `icims`, `taleo`, `smartrecruiters`, `jobvite`, `custom`, `unknown` |
| `application_url` | str \| null |
| `easy_apply` | bool |
| `extracted_skills` | list (`[]` default) |
| `posted_date`, `deadline_date`, `discovered_at` | ISO \| null |
| `is_active` | bool |
| `company` | `CompanySummary` (below) |
| `year_fit` | str \| null, for example "Open to 2nd-year students" |
| `application` | Only when an application is passed: `{id, status, match_score, match_reasoning, similarity_score}`. `status` is an `ApplicationStatus` value: `discovered`, `matched`, `skipped`, `preparing`, `pending_approval`, `approved`, `applied`, `acknowledged`, `screening`, `interview`, `assessment`, `final_round`, `offer`, `accepted`, `rejected`, `withdrawn`, `failed`. |

**`CompanySummary`** (`company_verifier.summary`): `{verdict: "verified"|"unverified"|"suspicious"|null, score, reasons: list[str] (≤6), method, tier: "big_tech"|"product"|"startup_india"|"startup_global"|"ai"|null, tier_label}`.
- If the company is in the user's `trusted_companies` (normalized match), `verdict` is forced to `"verified"` and `"You marked this company legit"` is prepended to `reasons`.

**`JobDetailOut`** (`job_detail_out`): `JobOut` plus `description`, `requirements`, `nice_to_haves`. When `prefs` is not given, it is taken from `application.user.prefs`.

**`ApplicationSummary`** (`application_summary`, serializers.py:107-122)

| Field | Type / notes |
|---|---|
| `self_applied` | bool: any history row with `new_status == applied` and `changed_by == "user"` |
| `id` | str |
| `status` | `ApplicationStatus` value |
| `match_score` | int \| null |
| `match_reasoning` | str \| null |
| `ats_platform` | `ATSPlatform` value |
| `needs_manual_review` | bool |
| `manual_review_reason` | str \| null |
| `created_at`, `updated_at`, `submitted_at` | ISO \| null |
| `job` | `JobOut` without the `application` key, with the owner's prefs, or `null` |

---

### 1.4 Real-time events and background tasks emitted by Part A endpoints

**WebSocket envelope.** Every server-pushed message is `{"type": <str>, "data": {...}}`.
- `publish_event(user_id, type, data)` publishes JSON to the Redis channel `events:<user_id>`. Every API process subscribes to `events:*` and forwards to its local sockets.
- Without Redis, delivery is in-process through `manager.deliver_local`.

| WS `type` | `data` | Emitted by |
|---|---|---|
| `connected` | `{user_id}` | WebSocket accept |
| `pong` | `{}` | Reply to the client text `"ping"` |
| `application_updated` | `{id, status, old_status}` | `application_service.set_status`. Called from `jobs/import`, `jobs/{id}/evaluate`, `jobs/{id}/prepare`, `jobs/company-trust`, `jobs/top-companies` (auto-skip) and `restage_internshala_waiting` (preferences, internshala-session, internshala/check). |
| `notification` | `{id, event_type, title, body, link, data, created_at}` | `notifier.notify`, which also inserts a `notifications` row. Called from `users/me/progress-report` (`progress_digest`) and `jobs/company-trust` via `_mark_ready` (`application_ready`). |

`notify()` also delivers to other channels depending on the event:
- **Email:** sent when the event's channels include it **and** `"email"` is in the user's `notification_channels`. The subject is **`"[HireFlow] <title>"`**. Delivery goes through SMTP if `SMTP_HOST` is set, otherwise through the user's own Gmail when the `gmail.modify` scope is granted.
- **Chat:** Discord/Slack webhooks, from user prefs or the env webhook URLs.

**Background dispatch** (`worker/dispatch.py`)
- `enqueue(name, *args, after_commit=db)` defers sending until the request transaction commits.
- With Redis reachable and `CELERY_TASK_ALWAYS_EAGER=false`, it sends `celery_app.send_task("hireflow.<name>")`.
- Otherwise it runs in a local `ThreadPoolExecutor(max_workers=4, thread_name_prefix="hireflow-task")`.

| Dispatch name | Celery task name | Queued by (Part A) |
|---|---|---|
| `check_user_email` | `hireflow.check_user_email` | `GET /auth/google/callback` (connect mode, after commit) |
| `handle_gmail_push` | `hireflow.handle_gmail_push` | `POST /webhooks/gmail` (immediately, args `(emailAddress, historyId_str)`) |
| `linkedin_sync_user` | `hireflow.linkedin_sync_user` | `POST /users/me/integrations/linkedin/sync` |
| `prepare_application` | `hireflow.prepare_application` | `POST /jobs/import` (when `prepare=true`), `POST /jobs/{job_id}/prepare` |
| `stage_application` | `hireflow.stage_application` | `restage_internshala_waiting`, reached from `PUT /users/me/preferences` (bot switched on), `POST /users/me/integrations/internshala-session` and `POST /users/me/integrations/internshala/check` (when valid) |
| `submit_application` | `hireflow.submit_application` | `POST /jobs/company-trust` (`trusted=true`, through `ready_or_submit`) |

---

### Health & Core

These are the app-level routes in `main.py`, plus the WebSocket and the Gmail webhook. The last two are defined in the `files.py` router and therefore sit under `/api/v1`.

| Method | Path | Auth | Rate limit |
|---|---|---|---|
| GET | `/health` | none | global default (`300/minute`) |
| GET | `/health/ready` | none | global default |
| WS | `/api/v1/ws?token=<jwt>` | `ws\|access` (query `token` or cookie) | not rate-limited (WebSocket) |
| POST | `/api/v1/webhooks/gmail?token=<secret>` | `pubsub-token` (only when configured) | global default |
| GET | `/docs` | none | global default (FastAPI-generated) |
| GET | `/docs/oauth2-redirect` | none | global default (FastAPI-generated) |
| GET | `/redoc` | none | global default (FastAPI-generated) |
| GET | `/api/v1/openapi.json` | none | global default (FastAPI-generated) |

#### `GET /health`
- **Handler:** `health`, `backend/app/main.py:88` (decorator L87, `tags=["health"]`)
- **Request:** none
- **Response:** `200` `{"status": "ok"}`
- **Side effects:** none

#### `GET /health/ready`
- **Handler:** `ready`, `backend/app/main.py:93` (decorator L92, `tags=["health"]`)
- **Request:** none
- **Response:** `{"status": "ok"|"degraded", "checks": {"database", "redis", "llm"}}`, where:
  - `checks.database`: `"ok"`, or `"error: <exception text>"` (from `SELECT 1` on the engine).
  - `checks.redis`: `"ok"` if `get_redis()` returns a client, else `"unavailable (in-process fallback)"`.
  - `checks.llm`: the provider names joined with `", "` (for example `"anthropic, ollama"`), else `"not configured (heuristic mode)"`.
- **Status:** `200` when `checks.database == "ok"`, else **`503`** with `"status": "degraded"`. Redis and LLM never affect health.
- **Side effects:** a DB connection is opened for `SELECT 1`.

#### `WS /api/v1/ws`
- **Handler:** `websocket_endpoint`, `backend/app/api/files.py:62` (decorator L61 `@router.websocket("/ws")`)
- **Query:** `token: str | None = None`
- **Auth:**
  - `raw = token or websocket.cookies["hireflow_session"]`, decoded with `expected_scopes=("ws", "access")`. Extension and `oauth_state` tokens are rejected.
  - The user is then loaded with a fresh `SessionLocal()` (not `get_db`) and must exist with `is_active=True`.
- **Auth failure:** `await websocket.close(code=4401)` **before accept**. Covers a bad or expired token, a wrong scope, a bad `sub`, and a missing or inactive user. Under uvicorn, a close before accept is seen by the client as a rejected handshake (HTTP 403).
- **Protocol:**
  1. `manager.connect(user_id, ws)` accepts the socket and registers it in an in-memory per-user set.
  2. The server immediately sends `{"type": "connected", "data": {"user_id": "<uuid>"}}`.
  3. The server then loops on `receive_text()`. The client text `"ping"` gets `{"type": "pong", "data": {}}`. Any other text is ignored.
  4. On `WebSocketDisconnect`, `manager.disconnect`.
- **Server push:** every `publish_event(user_id, ...)` for this user arrives as `{"type", "data"}` (see 1.4).
- **Frontend:** obtains a token from `GET /api/v1/auth/ws-token`, then connects to `${scheme}://${host}/api/v1/ws?token=...`.

#### `POST /api/v1/webhooks/gmail`
- **Handler:** `gmail_push` (async), `backend/app/api/files.py:47` (decorator L46, `status_code=204`)
- **Query:** `token: str | None = None`
- **Auth:** if `GMAIL_PUBSUB_VERIFICATION_TOKEN` is set, the query `token` must equal it, else `403 {"detail": "Invalid token"}`. If the setting is unset, the endpoint is open.
- **Body (Google Pub/Sub push envelope):** `{"message": {"data": "<base64 of JSON {\"emailAddress\": str, \"historyId\": int|str}>", ...}, ...}`
- **Response:** `204`, empty body.
- **Errors:** `400 {"detail": "Malformed Pub/Sub message"}` on `KeyError`, `ValueError` or `TypeError`. This covers a missing `message.data`, bad base64 (`binascii.Error`), bad UTF-8 and invalid JSON.
- **Side effects:** when `data["emailAddress"]` is truthy, `enqueue("handle_gmail_push", emailAddress, str(historyId or ""))` runs immediately (no `after_commit`). The task resolves the user by `google_email` (case-insensitive), then falls back to `email`, and enqueues `check_user_email`.

#### FastAPI-generated documentation routes
`GET /docs` (Swagger UI), `GET /docs/oauth2-redirect`, `GET /redoc` and `GET /api/v1/openapi.json`. No auth. They are covered by the global default rate limit, because `SlowAPIMiddleware` applies to all HTTP routes. The OpenAPI title is `"HireFlow"`.

---

### Auth (`/api/v1/auth`, `backend/app/api/auth.py`, `APIRouter(prefix="/auth", tags=["auth"])`)

| Method | Path | Auth | Rate limit |
|---|---|---|---|
| GET | `/api/v1/auth/config` | none | global default |
| POST | `/api/v1/auth/register` | none | `@limiter.limit("10/minute")` |
| POST | `/api/v1/auth/login` | none | `@limiter.limit("20/minute")` |
| POST | `/api/v1/auth/logout` | none | global default |
| GET | `/api/v1/auth/me` | access | global default |
| POST | `/api/v1/auth/password` | access | global default |
| GET | `/api/v1/auth/ws-token` | access | global default |
| POST | `/api/v1/auth/extension-token` | access | global default |
| GET | `/api/v1/auth/google/login` | none | global default |
| GET | `/api/v1/auth/google/connect` | access | global default |
| GET | `/api/v1/auth/google/callback` | `oauth_state` (in `state`) | global default |
| POST | `/api/v1/auth/google/disconnect` | access | global default |

#### `GET /api/v1/auth/config`
- **Handler:** `auth_config`, auth.py:37
- **Request:** none
- **Response:** `200 {"google_enabled": bool, "registration_enabled": bool, "llm_providers": list[str], "llm_model": str|null, "environment": str}`
  - `google_enabled`: `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are both set.
  - `registration_enabled`: `ALLOW_REGISTRATION` (default `True`).
  - `llm_providers`: subset of `["anthropic", "openai", "ollama"]`, in priority order.
  - `llm_model`: the primary provider's model, or `null` for heuristics-only.
  - `environment`: `ENVIRONMENT`.
- **Side effects:** none

#### `POST /api/v1/auth/register`
- **Handler:** `register`, auth.py:50 (decorators L48 `status_code=201`, L49 `@limiter.limit("10/minute")`)
- **Body (`RegisterRequest`):**

  | Field | Type / validation |
  |---|---|
  | `email` | `EmailStr` |
  | `password` | `str`, `min_length=8`, `max_length=256` |
  | `full_name` | `str`, `min_length=1`, `max_length=255` |

- **Response:** `201 {"user": UserOut, "access_token": "<access JWT>"}`
- **Side effects:**
  - Inserts a `users` row with:
    - `email` lowercased
    - `full_name` stripped
    - `hashed_password` from bcrypt
    - `preferences = default_preferences()`
  - `db.flush()`.
  - **Sets the `hireflow_session` cookie.**
- **Errors:**
  - `403 "Registration is disabled"` when `ALLOW_REGISTRATION` is false.
  - `409 "An account with this email already exists"`. The check is case-insensitive (`lower(email)`).
  - `422` on validation failure.
  - `429` when rate-limited.

#### `POST /api/v1/auth/login`
- **Handler:** `login`, auth.py:66 (decorators L64, L65 `@limiter.limit("20/minute")`)
- **Body (`LoginRequest`):** `email: EmailStr`, `password: str` (no length limits)
- **Response:** `200 {"user": UserOut, "access_token": "<access JWT>"}`
- **Side effects:** **sets the `hireflow_session` cookie.**
- **Errors:**
  - `401 "Invalid email or password"`: unknown email, wrong password, or an account with no password (Google-only).
  - `403 "Account disabled"`: `is_active` is false. This is checked only after the password verifies.
  - `422` and `429`.

#### `POST /api/v1/auth/logout`
- **Handler:** `logout`, auth.py:77
- **Auth:** none. It works with or without a session.
- **Response:** `200 {"ok": true}`
- **Side effects:** `delete_cookie("hireflow_session", path="/")`. No server-side token revocation.

#### `GET /api/v1/auth/me`
- **Handler:** `me`, auth.py:83
- **Response:** `200 UserOut`. This is the same data as `GET /api/v1/users/me`.
- **Errors:** `401`, see 1.1.

#### `POST /api/v1/auth/password`
- **Handler:** `change_password`, auth.py:88
- **Body (`PasswordChange`):** `current_password: str | None = None`, `new_password: str` (`min_length=8`, `max_length=256`)
- **Response:** `200 {"ok": true}`
- **Behavior:**
  - If the user already has a password, `current_password` must verify, otherwise `400 "Current password is incorrect"`.
  - A user with no password (Google sign-up) can set one without `current_password`.
- **Side effects:** updates `hashed_password` (committed by `get_db`). Existing JWTs stay valid.
- **Errors:** `400` (above), `401`, `422`.

#### `GET /api/v1/auth/ws-token`
- **Handler:** `ws_token`, auth.py:96
- **Response:** `200 {"token": "<JWT scope=ws, exp=+5 min, sub=user id>"}`
- **Side effects:** none

#### `POST /api/v1/auth/extension-token`
- **Handler:** `extension_token`, auth.py:102
- **Auth:** `access` only. An extension token cannot mint another extension token.
- **Response:** `200 {"token": "<JWT scope=extension, exp=+EXTENSION_TOKEN_EXPIRE_DAYS days>", "expires_in_days": 180, "api_url": settings.PUBLIC_API_URL}`. `PUBLIC_API_URL` defaults to `http://localhost:8000`.
- **Side effects:** none (stateless)

#### `GET /api/v1/auth/google/login`
- **Handler:** `google_login`, auth.py:110
- **Query:** `next: str | None = None`. It defaults to `"/dashboard"` and is not validated here; the callback validates it.
- **Response:** `307` redirect to `https://accounts.google.com/o/oauth2/v2/auth?...` with:

  | Param | Value |
  |---|---|
  | `client_id` | `GOOGLE_CLIENT_ID` |
  | `redirect_uri` | `settings.google_redirect_uri`, default `{FRONTEND_URL}/api/v1/auth/google/callback` |
  | `response_type` | `code` |
  | `scope` | `openid email profile` |
  | `access_type` | `offline` |
  | `include_granted_scopes` | `true` |
  | `prompt` | `select_account` |
  | `state` | JWT with `scope=oauth_state`, `sub="anonymous"`, `mode="login"`, `next=<next or "/dashboard">`, 15 min |

- **Errors:** `501 {"detail": "GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are not set"}` when Google is not configured.

#### `GET /api/v1/auth/google/connect`
- **Handler:** `google_connect`, auth.py:118
- **Response:** `200 {"url": "<Google auth URL>"}`. This is **JSON, not a redirect**.
- **URL parameters:** state `mode="connect"`, `sub=<user id>`, `next="/dashboard/settings"`. The scopes are `openid email profile` plus:
  - `https://www.googleapis.com/auth/gmail.readonly`
  - `https://www.googleapis.com/auth/gmail.modify`
  - `https://www.googleapis.com/auth/gmail.labels`
  - `https://www.googleapis.com/auth/calendar.events`
  - `https://www.googleapis.com/auth/calendar.readonly`

  `prompt=consent`, `access_type=offline`, `include_granted_scopes=true`.
- **Errors:** `501 "GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET are not set"`, and `401`.

#### `GET /api/v1/auth/google/callback`
- **Handler:** `google_callback`, auth.py:131
- **Query:** `code: str | None`, `state: str | None`, `error: str | None` (all default `None`)
- **Auth:** no session dependency. Authenticity comes from the `state` JWT, which must have scope `oauth_state` and be unexpired (15 min).
- **Response:** always a `307` redirect to `{FRONTEND_URL}<path>?<query>`. It never returns JSON.
- **Flow:**
  1. If `error`, `code` or `state` is missing, redirect to `/login?error=<error or "google_oauth_failed">`.
  2. Run `parse_state(state)`, then `exchange_code(code)` (POST `https://oauth2.googleapis.com/token`, 20 s timeout), then `fetch_userinfo(access_token)` (GET `https://openidconnect.googleapis.com/v1/userinfo`). On `TokenError`, `GoogleAuthError` or `KeyError`, redirect to `/login?error=google_oauth_failed`. Network exceptions are not caught and give a `500`.
  3. `next_path = payload["next"] or "/dashboard"`. If it does not start with `/`, it becomes `"/dashboard"`.
  4. **`mode == "connect"`:**
     - Load the user by `payload["sub"]`. If the user is missing, redirect to `/login?error=session_expired`.
     - `store_tokens()` sets:
       - `google_access_token`
       - `google_refresh_token` (only if Google returned one)
       - `google_token_expiry` = now + `expires_in` − 60 s
       - `google_scopes` (union with existing)
       - `google_email`
       - `consents["gmail"]` and/or `consents["calendar"]` as ISO timestamps
     - `flush`.
     - Best-effort `gmail_service.start_watch()`. Only when `GMAIL_PUBSUB_TOPIC` is set, it calls Gmail `users.watch` with `labelIds=["INBOX"]` and sets `gmail_history_id` and `gmail_watch_expiration`. Failures are logged at info level.
     - `enqueue("check_user_email", user_id, after_commit=db)`.
     - Redirect to `{next_path}?google=connected`.
     - **No session cookie is set in this mode.**
  5. **Login mode:**
     - Find the user by `lower(email) == google email`. This links to an existing password account by email.
     - If no user exists and `ALLOW_REGISTRATION` is false, redirect to `/login?error=registration_disabled`.
     - If no user exists otherwise, create one with `email=google_email`, `full_name = info["name"]` or the email local-part, default prefs, and no password.
     - Set `google_email` if it is empty. Login mode does **not** store Google API tokens.
     - Redirect to `{next_path}` and **set the `hireflow_session` cookie**.
     - `is_active` is not checked here; the inactive check happens on later authenticated requests.
- **Side effects:** user insert or update as above, external Google HTTP calls, and a Celery task in connect mode.

#### `POST /api/v1/auth/google/disconnect`
- **Handler:** `google_disconnect`, auth.py:182
- **Response:** `200 {"ok": true}`
- **Side effects:**
  - `google_oauth.revoke(user)` POSTs `https://oauth2.googleapis.com/revoke?token=<refresh or access token>` (10 s timeout; `httpx.HTTPError` is logged and ignored).
  - It then clears `google_access_token`, `google_refresh_token`, `google_token_expiry`, `google_scopes`, `gmail_history_id` and `gmail_watch_expiration`.
  - `google_email` is **not** cleared.

---

### Users (`/api/v1/users/me`, `backend/app/api/users.py`, `APIRouter(prefix="/users/me", tags=["users"])`)

| Method | Path | Auth | Rate limit |
|---|---|---|---|
| GET | `/api/v1/users/me` | access | global default |
| PATCH | `/api/v1/users/me` | access | global default |
| GET | `/api/v1/users/me/preferences` | access | global default |
| GET | `/api/v1/users/me/student` | access | global default |
| PUT | `/api/v1/users/me/preferences` | access | global default |
| POST | `/api/v1/users/me/progress-report` | access | global default |
| POST | `/api/v1/users/me/preferences/preset/{name}` | access | global default |
| GET | `/api/v1/users/me/field-mappings` | access | global default |
| PUT | `/api/v1/users/me/field-mappings` | access | global default |
| DELETE | `/api/v1/users/me/field-mappings/{field_name}` | access | global default |
| PUT | `/api/v1/users/me/ats-credentials` | access | global default |
| GET | `/api/v1/users/me/integrations` | access | global default |
| POST | `/api/v1/users/me/integrations/llm/test` | access | `@limiter.limit("10/minute")` |
| POST | `/api/v1/users/me/integrations/ollama/pull` | access | `@limiter.limit("10/minute")` |
| GET | `/api/v1/users/me/integrations/ollama/pull` | access | global default |
| POST | `/api/v1/users/me/integrations/linkedin-cookie` | **access\|extension** | global default |
| DELETE | `/api/v1/users/me/integrations/linkedin` | access | global default |
| POST | `/api/v1/users/me/integrations/linkedin/sync` | access | global default |
| POST | `/api/v1/users/me/integrations/internshala-session` | **access\|extension** | global default |
| DELETE | `/api/v1/users/me/integrations/internshala` | access | global default |
| POST | `/api/v1/users/me/integrations/internshala/check` | access | global default |
| GET | `/api/v1/users/me/export` | access | global default |
| DELETE | `/api/v1/users/me` | access | global default |

**Allowed preference keys** (`ALLOWED_PREF_KEYS`, users.py:41) are the 50 keys of `DEFAULT_PREFERENCES` plus `resume_template` and `auto_draft_replies`, 52 in total:

`target_roles, target_locations, remote_preference, salary_min, salary_max, salary_currency, experience_level, industries, company_size_preference, companies_to_avoid, companies_to_target, max_applications_per_day, auto_apply_threshold, job_types, internships_only, year_of_study, graduation_year, focus_skills, avoid_skills, notification_channels, notification_popups, keywords_exclude, posted_within_days, scan_enabled, scan_interval_hours, platforms, location_focus, internship_season, progress_updates_everywhere, progress_digest, review_mode, resume_strategy, auto_submit_kept, trust_generated_answers, auto_keep_min_score, max_jobs_per_source, exclude_no_sponsorship, internshala_bot_enabled, internshala_auto_submit, internshala_daily_limit, internshala_share, internshala_per_scan, skip_suspicious_companies, trusted_companies, scan_top_companies, sources, discord_webhook_url, slack_webhook_url, timezone, cover_letter_enabled, resume_template, auto_draft_replies`.

`merge_preferences(current, updates)` works like this:
- It starts from a deep copy of the defaults, then overlays `current` and then `updates`.
- Top-level keys are replaced. **`sources`** is the one exception: it is shallow-merged as a dict.

#### `GET /api/v1/users/me`
- **Handler:** `get_me`, users.py:45
- **Response:** `200 UserOut`

#### `PATCH /api/v1/users/me`
- **Handler:** `update_me`, users.py:50
- **Body (`ProfileUpdate`; all fields optional and applied only when present, via `exclude_unset`):**

  | Field | Type / validation |
  |---|---|
  | `full_name` | `str \| None`, `max_length=255` |
  | `phone` | `str \| None`, `max_length=50` |
  | `location` | `str \| None`, `max_length=255` |
  | `linkedin_url` | `str \| None`, not validated |

  Values are not stripped. There is no null guard, so `full_name: null` violates `NOT NULL` at commit and gives a `500`.
- **Response:** `200 UserOut`
- **Side effects:** updates the user columns.

#### `GET /api/v1/users/me/preferences`
- **Handler:** `get_preferences`, users.py:57
- **Response:** `200` with the full merged preferences object (`user.prefs`). Every default key is present.

#### `GET /api/v1/users/me/student`  *(not in the expected list)*
- **Handler:** `get_student`, users.py:62
- **Response:** `200 {"internships_only": bool, "year_of_study": int|null, "graduation_year": int|null, "graduation_year_source": "you"|"resume"|"estimate"|""}`
- **How the values are worked out** (`intern_level.student`):
  - `year_of_study` is in 1-5, or `null` for any year.
  - `graduation_year` comes from the first source that gives a value:
    1. The `graduation_year` preference (`"you"`).
    2. The latest future year found in the master resume's `education[].end_date` (`"resume"`).
    3. An estimate from the year of study (`"estimate"`).
  - If none applies, it is `""`.
- **Side effects:** none (reads the master resume)

#### `PUT /api/v1/users/me/preferences`
- **Handler:** `update_preferences`, users.py:123
- **Body (`PreferencesUpdate`):** `{"preferences": dict[str, Any]}`. This is a partial update, merged over the stored prefs.
- **Validation:** runs in this order on the **merged** result. Each failure is an `HTTPException(422, "<message>")`, so `detail` is a string.

  | # | Check | Exact `detail` |
  |---|---|---|
  | 1 | Every key is in `ALLOWED_PREF_KEYS` | `"Unknown preference keys: ['a', 'b']"` (Python `repr` of the sorted list) |
  | 2 | `auto_apply_threshold` is an int in 0..100 | `"auto_apply_threshold must be 0-100"` |
  | 3 | `max_applications_per_day` is an int in 1..200 | `"max_applications_per_day must be 1-200"` |
  | 4 | `review_mode` ∈ {`swipe`, `auto`} | `"review_mode must be 'swipe' or 'auto'"` |
  | 5 | `resume_strategy` ∈ {`original`, `light`, `full`} | `"resume_strategy must be 'original', 'light' or 'full'"` |
  | 6 | `auto_keep_min_score` is `null` or an int in 0..100 | `"auto_keep_min_score must be empty or 0-100"` |
  | 7 | `max_jobs_per_source` is `null` or an int in 10..1000 | `"max_jobs_per_source must be empty or 10-1000"` |
  | 8 | `notification_popups` is a bool | `"notification_popups must be true or false"` |
  | 9 | `location_focus` (when not null) is an object | `"location_focus must be an object"` |
  | 10 | `location_focus.country_share` (default 90) is an int in 0..100 | `"location_focus.country_share must be 0-100"` |
  | 11 | `location_focus.prime_cities` is a list of str with ≤50 items | `"location_focus.prime_cities must be a list of city names"` |
  | 12 | `location_focus.country` is a str | `"location_focus.country must be text"` |
  | 13 | `internship_season` is empty, or a str matching `(summer\|fall\|autumn\|winter\|spring) [20]YY` or `20YY <season>` | `"internship_season must look like 'Summer 2027' (or be empty)"` |
  | 14 | `progress_digest` ∈ {`daily`, `weekly`, `off`} | `"progress_digest must be 'daily', 'weekly' or 'off'"` |
  | 15 | `internshala_bot_enabled` and `internshala_auto_submit` are bools | `"<key> must be true or false"` |
  | 16 | `internshala_daily_limit` is an int (not bool) in 1..25 | `"internshala_daily_limit must be 1-25"` |
  | 17 | `internshala_share` is an int (not bool) in 0..100 | `"internshala_share must be 0-100"` |
  | 18 | `internshala_per_scan` is an int (not bool) in 0..50 | `"internshala_per_scan must be 0-50"` |
  | 19 | `year_of_study` is `null` or an int (not bool) in 1..5 | `"year_of_study must be 1-5 (or empty for any year)"` |
  | 20 | `graduation_year` is `null` or an int (not bool) in 2000..2100 | `"graduation_year must be a year like 2029 (or empty)"` |
  | 21 | `focus_skills` and `avoid_skills` are each a list of ≤50 non-blank str, each ≤60 characters | `"<key> must be a list of skills (up to 50, each up to 60 characters)"` |
  | 22 | `skip_suspicious_companies`, `scan_top_companies` and `internships_only` are bools | `"<key> must be true or false"` |
  | 23 | `trusted_companies` is a list of ≤500 str, each ≤255 characters | `"trusted_companies must be a list of company names"` |

- **Response:** `200` with the full merged preferences object that was stored.
- **Side effects:**
  - Stores the fully merged dict in `users.preferences`.
  - When `internshala_bot_enabled` changes from false to true:
    - It sets `consents["internshala_bot"] = <now ISO>`.
    - After saving, it calls `restage_internshala_waiting(db, user)`. This only acts when the bot is enabled **and** a valid Internshala session is stored. In that case, each `pending_approval` Internshala application with no `form_fields`:
      - has its `needs_manual_review` and `manual_review_reason` cleared;
      - has `auto_submit` set from `auto_submit_kept` if its `review_decision` is `"keep"`;
      - moves to `preparing` with the note "Filling the Internshala form with the bot" (WS `application_updated`);
      - gets `enqueue("stage_application", id, after_commit=db)`.

#### `POST /api/v1/users/me/progress-report`
- **Handler:** `progress_report`, users.py:160
- **Request:** none
- **Response:** `200 {"sent": bool}`. The value is `false` when the user has no tracked applications (status at or beyond `applied`, excluding `failed`).
- **Side effects:** `progress.send_now(db, user, days=7)` builds the 7-day digest and calls `notify(db, user, "progress_digest", title, body, link="/dashboard/applied")`. That does three things:
  - Inserts a `notifications` row and sends WS `notification`.
  - Sends an email with subject `"[HireFlow] <title>"` if `"email"` is in the user's `notification_channels`.
  - Posts to Discord/Slack when configured.

  The digest title is either `"Progress: N application(s) moved in the last 7 days"` or `"Progress: N applications tracked, no changes in the last 7 days"`.

#### `POST /api/v1/users/me/preferences/preset/{name}`
- **Handler:** `apply_preference_preset`, users.py:166
- **Path:** `name ∈ {"ai-engineer", "internships", "startups", "new-grad", "india-internships"}`
- **Response:** `200` with the full merged preferences after the preset is applied.
- **Side effects:** overwrites `users.preferences` with `apply_preset(...)`. The user's own lists are kept and extended. The `PUT` validations do **not** run, and there is no Internshala restage.
- **Errors:** `422 "Unknown preset '<name>' (choose from ai-engineer, internships, startups, new-grad, india-internships)"`

#### `GET /api/v1/users/me/field-mappings`
- **Handler:** `list_field_mappings`, users.py:183
- **Response:** `200 {"mappings": [FieldMappingOut], "standard_fields": STANDARD_FIELDS}`
  - `FieldMappingOut = {field_name, field_value, field_type, is_secret}`. When `field_name` contains `"password"`, `field_value` is `"********"` and `is_secret` is true.
  - `STANDARD_FIELDS` (`services/question_answerer.py`) is a dict of `field_key → {label, type ("radio"|"number"|"text"|"select"), options?}`. Examples: `work_authorization`, `requires_sponsorship`, `willing_to_relocate`, `years_experience`, `salary_expectation`, `expected_stipend`, `notice_period`, `highest_education`, `how_did_you_hear`, `over_18`, `pronouns`, `gender`, `race_ethnicity`, `hispanic_latino`, and more.
  - This GET does **not** list `ats_credentials` keys. The PUT response does.

#### `PUT /api/v1/users/me/field-mappings`
- **Handler:** `upsert_field_mappings`, users.py:188
- **Body (`FieldMappingsUpdate`):** `{"mappings": [FieldMappingIn]}`, where `FieldMappingIn` is:

  | Field | Type / validation |
  |---|---|
  | `field_name` | `str`, `min_length=1`, `max_length=255` |
  | `field_value` | `str` |
  | `field_type` | `str \| None = "text"` |

- **Behavior:**
  - The name is normalized: `strip().lower().replace(" ", "_")`.
  - If the name contains `"password"`, the value is **never stored as a mapping**. A non-empty value other than `"********"` is written to the encrypted `ats_credentials[name]`.
  - Any other name upserts a `user_field_mappings` row (unique per `user_id`, `field_name`).
- **Response:** `200 {"mappings": [...FieldMappingOut, ...{"field_name": <ats key>, "field_value": "********", "field_type": "password", "is_secret": true}], "standard_fields": STANDARD_FIELDS}`
- **Side effects:** DB inserts and updates, a possible `ats_credentials` update, `flush` and a refresh of the user.

#### `DELETE /api/v1/users/me/field-mappings/{field_name}`
- **Handler:** `delete_field_mapping`, users.py:213
- **Path:** `field_name: str`, exact match with no normalization.
- **Response:** `200 {"ok": true}`. Always returned; there is no 404.
- **Side effects:** deletes the mapping row if it exists, and removes `ats_credentials[field_name]` if present.

#### `PUT /api/v1/users/me/ats-credentials`
- **Handler:** `update_ats_credentials`, users.py:226
- **Body (`ATSCredentialsUpdate`):** `{"credentials": dict[str, str]}`
- **Response:** `200 {"keys": sorted list of stored credential keys}`
- **Side effects:** merges entries with non-empty values into the encrypted `ats_credentials`. Empty values are ignored, so this endpoint cannot delete a credential; the field-mappings DELETE does that.

#### `GET /api/v1/users/me/integrations`
- **Handler:** `integrations`, users.py:235
- **Response:** `200`

  ```json
  {
    "google": {"configured": bool, "connected": bool, "email": str|null, "gmail": bool, "calendar": bool,
               "last_polled_at": iso|null, "push_enabled": bool /* GMAIL_PUBSUB_TOPIC set */},
    "linkedin": {"connected": bool, "session_valid": bool, "updated_at": iso|null,
                 "profile_diff": any|null /* linkedin_profile_snapshot.diff */, "synced_at": str|null},
    "internshala": {"connected": bool, "session_valid": bool, "updated_at": iso|null,
                    "bot_enabled": bool, "auto_submit": bool, "daily_limit": int /* pref or 15 */},
    "llm": {"provider": str|null, "providers": [str], "model": str|null, "embedding_provider": str,
            "ollama": {"configured": bool, "base_url": str /* scheme+host only */, "cloud": bool, "model": str|null,
                       "reachable": bool, "version": str|null, "model_pulled": bool|null, "models": [str],
                       "error": str|null, "pull": PullProgress|null}},
    "automation": {"proxies": int, "captcha": bool, "dry_run": bool /* SUBMISSION_DRY_RUN */,
                   "auto_stage": bool /* AUTO_STAGE_APPLICATIONS */},
    "notifications": {"smtp": bool, "discord": bool, "slack": bool},
    "ats_credentials": [sorted key names]
  }
  ```

  - `google.gmail` and `google.calendar` mean a granted scope contains the substring `"gmail"` or `"calendar"`.
  - The Internshala cookies are never returned.
- **Side effects:** external probe of Ollama: `GET {base}/api/version` (skipped for Ollama Cloud) and `GET {base}/api/tags`. The timeout is 2.0 s when Ollama is configured, else 0.5 s (detect-only). No DB writes.
- **Ollama `error` strings:**
  - `"Ollama Cloud rejected the API key: check OLLAMA_API_KEY in .env"`
  - `"No answer from Ollama at {url} within {t} s"`
  - `"Ollama isn't running at {url}"`
  - `"{url} didn't answer like Ollama (HTTP <code>|<ExcType>)"`

#### `POST /api/v1/users/me/integrations/llm/test`
- **Handler:** `test_llm`, users.py:273 (decorators L271, L272 `@limiter.limit("10/minute")`)
- **Request:** none. No API key is ever accepted or returned.
- **Response:** always `200`, with `{"ok": bool, "provider": str|null, "model": str|null, "latency_ms": int}` plus one of the following:
  - **Success:** `"sample": str (≤300)`. If a fallback provider answered, also `"hint": "<primary> didn't answer, so the fallback (<used>) did: see the API logs for why."`.
  - **Failure:** `"error": str (≤800, credentials scrubbed)` and `"hint": str`.
  - **No LLM configured:** `"error": "No AI model is set up, so the agent uses its built-in heuristics."`, `"hint": "Add ANTHROPIC_API_KEY to .env, or set up a free model with Ollama (How to set it up), then restart."`.
- **Side effects:** one external LLM call: prompt `connection_test`, `effort="low"`, `max_tokens=256`.

#### `POST /api/v1/users/me/integrations/ollama/pull`
- **Handler:** `pull_ollama_model`, users.py:280 (decorators L278 `status_code=202`, L279 `@limiter.limit("10/minute")`)
- **Request:** none. The model is always `OLLAMA_MODEL`.
- **Response:** `202 PullProgress`, where `PullProgress = {"status": "idle"|"pulling"|"success"|"error", "model": str|null, "detail": str|null, "completed": int, "total": int, "percent": int, "error": str|null}`. `percent` is 100 on success, else `min(99, completed*100/total)`. If a download is already running, the current progress is returned and nothing new starts.
- **Side effects:**
  - Writes the progress state to Redis key **`hireflow:ollama-pull:{model}`**, where `model` is normalized with `:latest` added when there is no tag. TTL is 24 h. Without Redis it is kept in process memory.
  - Starts a daemon thread `ollama-pull` that streams `POST {OLLAMA_BASE_URL}/api/pull`, with a 600 s read timeout.
- **Errors:**
  - `400 "Set OLLAMA_MODEL in .env first (for example qwen3.5:4b), then restart the app."`
  - `400 "Ollama Cloud models run on ollama.com, so there is nothing to download."`
  - `429`

#### `GET /api/v1/users/me/integrations/ollama/pull`
- **Handler:** `ollama_pull_progress`, users.py:289
- **Response:** `200 PullProgress` for `OLLAMA_MODEL`. The status is `idle` when nothing is stored. A `pulling` state not updated for more than 660 s is reported as `error` with `"The download stopped responding. Press Download model to try again."`.

#### `POST /api/v1/users/me/integrations/linkedin-cookie`
- **Handler:** `sync_linkedin_cookie`, users.py:295
- **Auth:** `ExtensionUser` (scope `access` or `extension`). The Chrome extension calls this.
- **Body (`LinkedInCookieIn`):** `li_at: str` (`min_length=10`, `max_length=4000`), `profile_url: str | None = None`
- **Response:** `200 {"ok": true, "synced_at": "<ISO>"}`
- **Side effects:**
  - `linkedin_session_cookie = li_at.strip()` (encrypted).
  - `linkedin_cookie_updated_at = now` and `linkedin_session_valid = True`.
  - If `profile_url` contains `"linkedin.com/in/"` and the user has no `linkedin_url`, sets it to `profile_url` with the query string removed.
  - `consents["linkedin"] = now ISO`.
  - No sync is enqueued.

#### `DELETE /api/v1/users/me/integrations/linkedin`
- **Handler:** `disconnect_linkedin`, users.py:308
- **Response:** `200 {"ok": true}`
- **Side effects:** `linkedin_session_cookie = None`, `linkedin_session_valid = False`, `linkedin_profile_snapshot = None`. `linkedin_cookie_updated_at` is kept.

#### `POST /api/v1/users/me/integrations/linkedin/sync`
- **Handler:** `trigger_linkedin_sync`, users.py:316 (decorator `status_code=202`)
- **Response:** `202 {"queued": true}`
- **Side effects:** `enqueue("linkedin_sync_user", user_id, after_commit=db)` → Celery `hireflow.linkedin_sync_user`. The task scrapes the profile, then:
  - updates `linkedin_profile_snapshot` (`hash`, `synced_at`, `text`, `diff`);
  - on a change, may `notify` `linkedin_profile_changed`;
  - on an expired session, may `notify` `session_expired`.
- **Errors:** `400 "LinkedIn session not synced yet"` when no cookie is stored.

#### `POST /api/v1/users/me/integrations/internshala-session`
- **Handler:** `sync_internshala_session`, users.py:330
- **Auth:** `ExtensionUser` (scope `access` or `extension`).
- **Body (`InternshalaSessionIn`):**

  | Field | Type / validation |
  |---|---|
  | `cookies` | `list[InternshalaCookieIn]`, `min_length=1`, `max_length=60` |
  | `reason` | `str = "manual"`, `max_length=20`. The extension sends `manual`, `scheduled` or `cookie-changed`. |
  | `user_agent` | `str \| None = None`, `max_length=512` |

  `InternshalaCookieIn` (`populate_by_name=True`, so both the Chrome alias and the snake_case name are accepted):

  | Field | Type / validation |
  |---|---|
  | `name` | `str`, 1..256 |
  | `value` | `str = ""`, ≤4096 |
  | `domain` | `str`, 1..255 |
  | `path` | `str = "/"`, ≤1024 |
  | `secure` | `bool = False` |
  | `http_only` (alias `httpOnly`) | `bool = False` |
  | `same_site` (alias `sameSite`) | `str \| None`, ≤32 |
  | `expiration_date` (alias `expirationDate`) | `float \| None` |
  | `host_only` (alias `hostOnly`) | `bool \| None` |

- **Validation and errors, in order:**
  1. `409 "Internshala was disconnected in your dashboard — click “Sync Internshala session” in the extension to connect it again."` when `reason != "manual"` and `consents.internshala_disconnected` is set.
  2. The lowercased, stripped domain must full-match `\.?(?:[a-z0-9-]+\.)*internshala\.com`, else `422 "Only internshala.com cookies are accepted, not <domain[:60]>"`.
  3. The name must full-match ``[A-Za-z0-9!#$%&'*+.^_`|~-]+`` and the value must contain no character below 0x20, `;` or `\x7f`, else `422 "Invalid cookie <name[:40]>"`.
  4. Cookies whose `expiration_date` is already in the past are silently dropped. Cookies are de-duplicated by `(name, domain, path)`.
  5. The total of `len(name) + len(value)` over the stored cookies must be ≤ 32000 (`MAX_INTERNSHALA_SESSION_CHARS`), else `413 "Too many Internshala cookies"`.
  6. At least one cookie in `SESSION_COOKIES = {"PHPSESSID", "l", "sessionToken", "persistentSession"}` must have a value, else `422 "No Internshala session cookie found — log into Internshala in Chrome and sync again"`.
  7. `has_login`: `is_logged_in == "1"`, or both `PHPSESSID` and `l` present. Otherwise `422 "You're not logged into Internshala in this browser — log in and sync again"`.
- **Stored cookie shape:** `{name, value, domain, path, secure, httpOnly, sameSite, expirationDate, hostOnly}`. `hostOnly` defaults to `not domain.startswith(".")`.
- **Response:** `200 {"ok": true, "synced_at": "<ISO>", "cookies": <count stored>}`
- **Side effects:**
  - `internshala_session` = the stored cookie list (encrypted JSON).
  - `internshala_user_agent` is only touched when `user_agent` is provided: it is kept if it full-matches `Mozilla/5\.0 [\x20-\x7e]{10,500}`, else set to `None`.
  - `internshala_session_updated_at = now` and `internshala_session_valid = True`.
  - `consents["internshala"] = now`, and `consents.internshala_disconnected` is removed.
  - `restage_internshala_waiting(db, user)` runs (see `PUT /preferences`): WS `application_updated` plus `stage_application` tasks.

#### `DELETE /api/v1/users/me/integrations/internshala`
- **Handler:** `disconnect_internshala`, users.py:373
- **Response:** `200 {"ok": true}`
- **Side effects:**
  - Clears `internshala_session`, `internshala_user_agent` and `internshala_session_updated_at`.
  - Sets `internshala_session_valid = False`.
  - Sets the prefs `internshala_bot_enabled` and `internshala_auto_submit` to `false`.
  - Sets `consents["internshala_disconnected"] = now ISO`. From then on, non-manual extension re-syncs are blocked with `409`.

#### `POST /api/v1/users/me/integrations/internshala/check`
- **Handler:** `check_internshala_session`, users.py:388
- **Response:** `200 {"session_valid": bool, "checked_at": "<ISO>"}`
- **Side effects:**
  - Launches a real Playwright browser with the stored cookies and user agent, and opens `https://internshala.com` plus the dashboard path (`/student/dashboard`). The session is invalid if the page lands on `/login`.
  - Sets `internshala_session_valid`. If valid, runs `restage_internshala_waiting`.
- **Errors:**
  - `400 "Internshala login not synced yet — use the browser extension"`
  - `503 "No browser available to check the session: <exc>"` (`BrowserUnavailable`)
  - `502 "Could not reach Internshala: <exc>"` (any other exception; the stored state is kept)

#### `GET /api/v1/users/me/export`
- **Handler:** `export_data`, users.py:406
- **Response:** `200`, `Content-Type: application/json`, `Content-Disposition: attachment; filename="hireflow-export-<YYYY-MM-DD UTC>.json"`. The body is `json.dumps(..., indent=2, default=str)` of:
  - `exported_at` (ISO).
  - `user`: every column **except** `hashed_password`, `google_access_token`, `google_refresh_token`, `linkedin_session_cookie`, `internshala_session` and `ats_credentials`.
  - `field_mappings`: `[{field_name, field_value (masked "********" if the name contains "password"), field_type}]`.
  - `resumes`: all columns except `skills_embedding`.
  - `applications`: each application's columns plus `job` (all columns except `description_embedding`) and `history`.
  - `communications`, `interviews` (only for the user's applications), `agent_runs`, `notifications`: all columns.
- **Side effects:** none (read-only)

#### `DELETE /api/v1/users/me`
- **Handler:** `delete_account`, users.py:416
- **Body (`DeleteAccountRequest`):** `{"confirm": str}`. The value must be exactly `"DELETE"`. A JSON body is required on this DELETE.
- **Response:** `200 {"deleted": true}`
- **Side effects:** `privacy.delete_user_data` runs these steps:
  1. Revoke the Google token, with errors ignored.
  2. Delete the storage prefix `users/<user_id>` (local directory or S3 objects), with errors logged.
  3. Delete the user's interviews.
  4. Delete the user's communications.
  5. Delete the user's applications.
  6. Delete tailored resumes (`parent_resume_id` not null).
  7. Delete the user. ORM cascades remove the remaining resumes and field mappings. Notifications and agent runs are removed by FK `ON DELETE CASCADE`.

  Finally, it **clears the `hireflow_session` cookie**.
- **Errors:** `400 "Type DELETE to confirm"`, and `422` if the body is missing.

---

### Resumes (`/api/v1/resumes`, `backend/app/api/resumes.py`, `APIRouter(prefix="/resumes", tags=["resumes"])`)

| Method | Path | Auth | Rate limit |
|---|---|---|---|
| POST | `/api/v1/resumes/upload` | access | global default |
| POST | `/api/v1/resumes/from-text` | access | global default |
| GET | `/api/v1/resumes` | access | global default |
| GET | `/api/v1/resumes/master` | access | global default |
| GET | `/api/v1/resumes/{resume_id}` | access | global default |
| PUT | `/api/v1/resumes/{resume_id}` | access | global default |
| POST | `/api/v1/resumes/{resume_id}/set-master` | access | global default |
| GET | `/api/v1/resumes/{resume_id}/pdf` | access | global default |
| DELETE | `/api/v1/resumes/{resume_id}` | access | global default |

**Ownership helper** `_get_owned` (resumes.py:34):
- A malformed UUID gives `404 "Not found"`.
- A missing resume, or one belonging to another user, gives `404 "Resume not found"`.
- It does **not** filter `is_active`, so soft-deleted resumes stay readable and editable by id.

**Embedding helper** `_embed`: sets `skills_embedding = embed_text(skills_text + "\n" + full_text)`, using the configured embedding provider: local, OpenAI or Ollama.

**Master helper** `_make_master`: `UPDATE resumes SET is_master=false WHERE user_id=:uid AND id != :id`, then sets this resume's `is_master = True`.

**Profile sync helper** `_sync_profile`: copies `personal_info.phone`, `location` and `linkedin` into the user's `phone`, `location` and `linkedin_url`, but **only when those user fields are empty**.

#### `POST /api/v1/resumes/upload`
- **Handler:** `upload_resume` (async), resumes.py:52 (decorator L51 `status_code=201`)
- **Request:** `multipart/form-data` with these fields:

  | Field | Type / default |
  |---|---|
  | `file` | `UploadFile`, required |
  | `is_master` | `bool` form field, default `true` |
  | `label` | `str \| None` form field, default `null` |

- **Limits and accepted types:**
  - **`MAX_UPLOAD_BYTES = 10 * 1024 * 1024`.** The file is fully read first, then the size is checked.
  - The type is detected by filename or content:
    - `.pdf`, or content starting with `%PDF`: pypdf. For one-word-per-line exports, lines are rebuilt from word positions, and link URIs are inserted after the first line.
    - `.docx`: python-docx paragraphs plus table rows joined with `" | "`.
    - `.txt`, `.md` or no filename: UTF-8 decode with `errors="replace"`.
  - The extracted text must be at least 50 characters after cleanup.
- **Processing:**
  1. `parse_resume_text(text)` runs in a worker thread. It tries the LLM first (prompt `resume_parser`, `effort="low"`) and the result counts as `"llm"` when it yields experience, education or technical skills. Otherwise the heuristic parser is used (`"heuristic"`).
  2. `personal_info.email` and `.name` default to the user's email and full name.
  3. The file is saved to storage key **`users/<user_id>/uploads/<uuid4 hex>.<ext>`**, where `ext` is the last filename extension, lowercased and capped at 5 characters (default `pdf`). The upload's `content_type` is passed.
  4. A `resumes` row is inserted with:
     - `label` = the given label or `"Master resume (<filename>)"`
     - `original_file_url` = the storage key
     - `original_filename`
     - `raw_text`
     - `parsed_content`
     - `is_master=False` initially
  5. Embed. If `is_master`, run `_make_master`. Then `_sync_profile`.
- **Response:** `201 {...ResumeOut (with parsed_content), "parse_method": "llm"|"heuristic"}`
- **Errors:**
  - `413 "File too large (max 10 MB)"`
  - `422 "Could not read PDF: <exc>"`
  - `422 "Could not read DOCX: <exc>"`
  - `422 "Unsupported file type. Upload one of: .pdf, .docx, .txt, .md"`
  - `422 "Could not extract text from the resume (is it a scanned image?)"`
  - `422` when the `file` field is missing.

#### `POST /api/v1/resumes/from-text`
- **Handler:** `create_from_text`, resumes.py:86 (decorator `status_code=201`)
- **Body (`ResumeCreateFromText`):**

  | Field | Type / validation |
  |---|---|
  | `text` | `str`, `min_length=50`, no maximum |
  | `label` | `str \| None = None` |
  | `is_master` | `bool = True` |

- **Response:** `201 {...ResumeOut (with parsed_content), "parse_method": "llm"|"heuristic"}`
- **Side effects:** same as upload, except that **no file is stored** and the label defaults to `"Master resume"`. Parsing runs synchronously in the request thread.

#### `GET /api/v1/resumes`
- **Handler:** `list_resumes`, resumes.py:103
- **Query:** `tailored: bool | None = None`
  - `true`: only resumes with `parent_resume_id` set.
  - `false`: only resumes without it.
  - omitted: all.
- **Filter and order:** `is_active = true`, ordered by `is_master DESC, created_at DESC`, limited to **200**.
- **Response:** `200 {"items": [ResumeOut without parsed_content]}`

#### `GET /api/v1/resumes/master`
- **Handler:** `get_master`, resumes.py:114
- **Response:** `200 ResumeOut` (with `parsed_content`). It does not filter `is_active`.
- **Errors:** `404 "No master resume yet"`

#### `GET /api/v1/resumes/{resume_id}`
- **Handler:** `get_resume`, resumes.py:122
- **Response:** `200 ResumeOut` (with `parsed_content`)
- **Errors:** `404 "Not found"` (bad UUID), `404 "Resume not found"`

#### `PUT /api/v1/resumes/{resume_id}`
- **Handler:** `update_resume`, resumes.py:127
- **Body (`ResumeUpdate`):** `parsed_content: dict | None = None`, `label: str | None = None` (`max_length=255`)
- **Behavior:**
  - When `parsed_content` is given, it is normalized through `ResumeContent`. Then `version += 1` (starting from 1 if null), `pdf_url = None` (forces re-render), and the resume is re-embedded.
  - When `label` is given, it is replaced.
- **Response:** `200 ResumeOut` (with `parsed_content`)
- **Errors:** the same 404s.

#### `POST /api/v1/resumes/{resume_id}/set-master`
- **Handler:** `set_master`, resumes.py:140
- **Response:** `200 ResumeOut`
- **Side effects:** `_make_master`. It does not check `is_active`.
- **Errors:** the same 404s.

#### `GET /api/v1/resumes/{resume_id}/pdf`
- **Handler:** `resume_pdf`, resumes.py:147
- **Query:**
  - `template: str = "classic"`. Allowed values are `TEMPLATES = ("classic", "modern")`; any other value silently falls back to `"classic"`.
  - `download: bool = False`
- **Response:** `200`, `Content-Type: application/pdf`, `Content-Disposition: <"attachment" if download else "inline">; filename="<personal_info.name with spaces→_ or 'resume'>_Resume.pdf"`. The body is rendered on the fly by ReportLab and not stored.
- **Errors:** the same 404s.

#### `DELETE /api/v1/resumes/{resume_id}`
- **Handler:** `delete_resume`, resumes.py:159
- **Response:** `200 {"ok": true}`
- **Side effects:** **soft delete** by setting `is_active = False`. The stored file is not removed.
- **Errors:** `400 "Set another resume as master before deleting this one"` when the resume is the master, plus the same 404s.

---

### Jobs (`/api/v1/jobs`, `backend/app/api/jobs.py`, `APIRouter(prefix="/jobs", tags=["jobs"])`)

| Method | Path | Auth | Rate limit |
|---|---|---|---|
| GET | `/api/v1/jobs` | access | global default |
| GET | `/api/v1/jobs/top-companies` | access | global default |
| POST | `/api/v1/jobs/company-trust` | access | global default |
| GET | `/api/v1/jobs/{job_id}` | access | global default |
| POST | `/api/v1/jobs/import` | access | global default |
| POST | `/api/v1/jobs/{job_id}/evaluate` | access | global default |
| POST | `/api/v1/jobs/{job_id}/prepare` | access | global default |

Jobs are global (shared across users). A user only sees a job if they have an `applications` row for it, because every list query is an inner join on `Application.user_id == user.id`.

#### `GET /api/v1/jobs`
- **Handler:** `list_jobs`, jobs.py:30
- **Query:**

  | Param | Type / default / validation |
  |---|---|
  | `q` | `str \| None`: case-insensitive `LIKE %q%` on `role_title`, `company_name` or `location` |
  | `platform` | `str \| None`: an `ATSPlatform` value, matched against `Job.source_platform`. Otherwise `422 "Unknown platform"`. |
  | `remote` | `bool \| None`: matched against `Job.is_remote` |
  | `status` | `str \| None` (Python name `status_filter`, `alias="status"`): an `ApplicationStatus` value. Otherwise `422 "Unknown status"`. |
  | `min_score` | `int \| None`: `Application.match_score >= min_score` |
  | `sort` | `str = "match"`. See the sort orders below. |
  | `page` | `int = 1`, `ge=1` |
  | `page_size` | `int = 25`, `ge=1`, `le=100` |

  Sort orders:
  - `match`: `match_score DESC NULLS LAST`, then `discovered_at DESC`
  - `recent`: `discovered_at DESC`
  - `posted`: `posted_date DESC NULLS LAST`
  - `company`: `company_name ASC`
  - any other value: `discovered_at DESC`

  Always filtered to `Job.is_active = true`.
- **Response:** `200 {"items": [JobOut with "application"], "total": int, "page": int, "page_size": int}`
- **Side effects:** none

#### `GET /api/v1/jobs/top-companies`  *(not in the expected list)*
- **Handler:** `top_companies`, jobs.py:78
- **Query:**

  | Param | Type / default / validation |
  |---|---|
  | `tier` | `str \| None`, one of `TIERS` keys: `big_tech`, `product`, `startup_india`, `startup_global`, `ai` |
  | `q` | `str \| None`: case-insensitive substring of role, company or location |
  | `limit` | `int = 200`, `ge=1`, `le=500` |

- **Response:** `200`

  ```json
  {
    "tiers": [{"key": str, "label": str, "count": int}],
    "total": int,
    "items": [JobOut with "application"],
    "catalog": {"<tier>": [company names]},
    "scan_top_companies": bool
  }
  ```

  - `tiers` covers all 5 tiers. Labels: `"Big Tech"`, `"Product companies"`, `"Indian startups"`, `"Global startups"`, `"AI companies"`.
  - `total` is the sum of the tier counts after the user's filters, before the `tier` and `q` filters.
  - `items` is capped at `limit`.
  - `scan_top_companies` is the pref, default `true`.
- **How rows are selected:**
  - Up to 5000 of the user's `(job, application)` rows where `company_tier` is not null and `is_active` is true, ordered by `match_score DESC NULLS LAST, discovered_at DESC`.
  - Rows rejected by hard `filter_reasons` are dropped. These are computed from the user's prefs plus the master resume's graduation year.
- **Side effects (writes):**
  - `orch.backfill_company_checks(db)` computes `company_verdict`, `company_tier` and `company_check` for up to 2000 jobs, globally, where `company_verdict` is null.
  - `orch.skip_ineligible_waiting(db, user)` handles the user's applications that are `discovered` or `matched`, have no review decision, and fail a hard filter. Each one has `match_reasoning` set to the reason and moves to `skipped` (agent), sending WS `application_updated`.
- **Errors:** `422 "Unknown tier"`

#### `POST /api/v1/jobs/company-trust`  *(not in the expected list)*
- **Handler:** `company_trust`, jobs.py:117
- **Body (`CompanyTrustIn`, defined inline at jobs.py:111-113):**

  | Field | Type / validation |
  |---|---|
  | `company` | `str`, `min_length=1`, `max_length=255` |
  | `trusted` | `bool \| None`. **Required key** (no default). `true` = legit, `false` = not legit (avoid), `null` = back to the agent's verdict. |

- **Response:** `200 {"company": <stripped name>, "trusted": bool|null, "applications_updated": int}`
- **Side effects:**
  1. `preferences.trusted_companies` and `companies_to_avoid` are rewritten. Entries with the same normalized company key are removed. Then the name is appended to `trusted_companies` (true) or `companies_to_avoid` (false), or neither (null).
  2. For each of the user's applications in `discovered`, `matched` or `pending_approval` whose job's company has the same normalized key:
     - **`trusted=false`:** `match_reasoning = "You marked <name> as not legit"`, then `set_status → skipped` (changed_by `"user"`), sending WS `application_updated`.
     - **`trusted=true`, the application is `pending_approval`, and `manual_review_reason` starts with `"Not sent automatically:"`:** clear `needs_manual_review` and `manual_review_reason`, then `orch.ready_or_submit`. That leads to one of two outcomes:
       - The application moves to `approved` with the note "Approved when you kept it in Swipe Review", and `enqueue("submit_application")` runs after commit.
       - Otherwise `_mark_ready`: `pending_approval` (no-op if unchanged) plus `notify("application_ready", "Review application: <role> @ <company>", ...)`, which inserts a notification row and sends WS `notification` and email.
- **Errors:** `422 "Company name required"` when the normalized key is empty; `422` on validation failure.

#### `GET /api/v1/jobs/{job_id}`
- **Handler:** `get_job`, jobs.py:153
- **Response:** `200 JobDetailOut` (with `application` and the owner's prefs). It does not filter `Job.is_active`.
- **Errors:** `404 "Not found"` (bad UUID), `404 "Job not found"` (no job, or no application for this user)

#### `POST /api/v1/jobs/import`
- **Handler:** `import_job` (async), jobs.py:162 (decorator `status_code=201`)
- **Body (`JobImportRequest`):** `url: str` (`min_length=8`, `max_length=2000`, no URL-format validation), `prepare: bool = False`
- **Processing:** `orch.import_job_url` runs in a worker thread:
  1. `fetch_job_from_url(url)` detects the ATS platform and uses the matching scraper. A URL containing `internshala.com/` uses the Internshala scraper. If the result is `None`, the generic scraper is tried as a fallback.
  2. `upsert_job` and `embed_jobs`.
  3. `ensure_application` (creates the application as `discovered` if new).
  4. If the application is `discovered`, `evaluate_application` runs with `use_llm=True`. This makes external LLM calls and may set `skipped` or `matched` (WS `application_updated`).
  5. If `prepare=true`, a master resume exists, and the status is `matched`, `skipped` or `discovered`, then `set_status → preparing` (user, "Prepared on request") and `enqueue("prepare_application", app_id, after_commit=db)`. Without a master resume, the prepare request is silently ignored.
- **Response:** `201 ApplicationSummary`
- **Side effects:** the HTTP fetch of the posting, job and application inserts, the embedding, the LLM call, and an optional task, as above.
- **Errors:** `422 "<ScraperError text>"`, for example `"Could not read a job posting at that URL"`.

#### `POST /api/v1/jobs/{job_id}/evaluate`
- **Handler:** `evaluate_job`, jobs.py:177
- **Behavior:**
  1. If the application is `skipped` or `matched`, its status is reset to `discovered` by a direct assignment. This writes no history and sends no event.
  2. `orch.evaluate_application(..., use_llm=True, resume_vec=resume_embedding(master))` then runs:
     - The prefilter and the already-applied check can set `skipped`.
     - Otherwise the LLM or heuristic match is scored. In swipe mode the result is `matched`. In `auto` mode the result is `matched` when the score is at least `auto_apply_threshold` (default 80) and the evaluation proceeds; otherwise it is `skipped` with the note `"Match score N below T"`.
     - The application's `match_score`, `match_reasoning`, `match_details` and `similarity_score` are set.
  3. The evaluation runs whatever the current status is.
- **Response:** `200 JobDetailOut`
- **Side effects:** external LLM call, DB writes, and WS `application_updated` on each status change.
- **Errors:** `404 "Not found"` (bad UUID), `404 "Job not found"` (no application), `400 "Upload a master resume first"`

#### `POST /api/v1/jobs/{job_id}/prepare`
- **Handler:** `prepare_job`, jobs.py:191 (decorator `status_code=202`)
- **Allowed current statuses:** `discovered`, `matched`, `skipped`, `failed`
- **Response:** `202 ApplicationSummary`, with status `preparing`
- **Side effects:**
  - `set_status → preparing` (changed_by `"user"`, notes `"Prepared on request"`), sending WS `application_updated`.
  - `enqueue("prepare_application", app_id, after_commit=db)` → `hireflow.prepare_application`. The task tailors the resume, writes the cover letter and fills the form, then waits for approval.
- **Errors:**
  - `404 "Not found"` / `"Job not found"`
  - `400 "Upload a master resume first"`
  - `409 "Application is already <status value>"`, for example `"Application is already pending_approval"`

---

### Files (`/api/v1/files`, `backend/app/api/files.py`, `APIRouter(tags=["files"])` without a router prefix)

| Method | Path | Auth | Rate limit |
|---|---|---|---|
| GET | `/api/v1/files/{key:path}` | access | global default |

The same router also defines `WS /api/v1/ws` and `POST /api/v1/webhooks/gmail`, which are documented under **Health & Core** above.

#### `GET /api/v1/files/{key:path}`
- **Handler:** `get_file`, files.py:29 (decorator L28)
- **Path:** `key` is a path-typed parameter, so it may contain `/`. It is URL-decoded (`unquote`) before the checks.
- **Access rule:** the key must start with `users/<current user id>/` and must not contain `..`. Otherwise `404 "File not found"`. Users can only read their own prefix.
- **Response:**
  - **S3 backend** (`STORAGE_BACKEND=s3` and `S3_BUCKET` set): a `307` redirect to a presigned `GET` URL that expires in **300 s**.
  - **Local backend:** `200` with the raw bytes. `Content-Type` comes from `mimetypes.guess_type(key)`, or `application/octet-stream`. The response carries **`Cache-Control: private, max-age=300`**.
- **Errors:**
  - `404 "File not found"` (prefix or `..` check fails, or `FileNotFoundError`/`OSError` on read)
  - `401` (auth)
- **Side effects:** none
- **Clients:** every `*_url` field produced by `file_url()` (`pdf_url`, `original_file_url`, and the application screenshot and PDF URLs in Part B) points at this endpoint.

---

### 1.x Reconciliation against the migration checklist (Part A scope)

**Defined in code but missing from the expected list** (all must be migrated):
1. `GET /api/v1/users/me/student`: `get_student`, users.py:62
2. `GET /api/v1/jobs/top-companies`: `top_companies`, jobs.py:78
3. `POST /api/v1/jobs/company-trust`: `company_trust`, jobs.py:117
4. FastAPI-generated `GET /docs`, `GET /docs/oauth2-redirect`, `GET /redoc` and `GET /api/v1/openapi.json`. These come from `main.py` settings and are not hand-written.

**Path corrections to the expected list**

| Expected | Actual |
|---|---|
| `WebSocket /ws?token=...` | **`/api/v1/ws?token=...`** |
| `POST /webhooks/gmail` | **`POST /api/v1/webhooks/gmail`** |

Both are defined in `api/files.py`, not `main.py`, and are mounted with the `/api/v1` prefix. The frontend (`src/hooks/use-websocket.ts`), the tests and the README all use the `/api/v1/...` forms.

Every other expected endpoint exists in code with the stated method and path. Nothing on the expected list is missing from the code.

**HireFlow renames observed in this scope**

| Original | HireFlow |
|---|---|
| Cookie `autoapply_session` | `hireflow_session` |
| Celery `autoapply.<task>` | `hireflow.<task>` |
| Redis key `autoapply:ollama-pull:{model}` | `hireflow:ollama-pull:{model}` |
| Export filename `autoapply-export-<date>.json` | `hireflow-export-<date>.json` |
| Notification email prefix `[AutoApply AI]` | `[HireFlow]` |
| `MANUAL_URL_PREFIX` `https://manual.autoapply.invalid/` | `https://manual.hireflow.invalid/` |
| FastAPI title `AutoApply AI` | `HireFlow` |
| Startup log `AutoApply AI API ready ...` | `HireFlow API ready ...` |
| Local task thread prefix `autoapply-task` | `hireflow-task` |

`auto_apply_threshold` is unchanged.

### Applications

> Section 1, part B. It covers the routers `applications`, `review`, `agent`, `communications`, `interviews` and `analytics` (which also serves `/notifications`), plus the request schemas and the serializers they use. All names are HireFlow names. Source paths are relative to `backend/app/`.

#### Conventions shared by every endpoint in this part

| Topic | Behaviour (source) |
|---|---|
| Mounting | `api/__init__.py` is empty (0 lines). Routers are mounted in `main.py:82-84`: `for router in (auth, users, resumes, jobs, applications, agent, communications, interviews, analytics, review, files): app.include_router(router, prefix=settings.API_PREFIX)`, with `API_PREFIX = "/api/v1"` (`config.py:49`). Router prefixes: `/applications` (`api/applications.py:43`), `/review` (`api/review.py:34`), `/agent` (`api/agent.py:23`), `/communications` (`api/communications.py:17`), `/interviews` (`api/interviews.py:21`). The analytics router has no prefix (`api/analytics.py:13`, `APIRouter(tags=["analytics"])`) and declares the full paths `/analytics/overview` and `/notifications…`. |
| Auth | Every endpoint takes `CurrentUser = Annotated[User, Depends(get_current_user)]` (`api/deps.py:53,61`), which calls `_user_from_request(request, db, scopes=("access",))`. The token comes from the `Authorization: Bearer <jwt>` header when one is present. Otherwise it comes from the cookie `hireflow_session` (`settings.COOKIE_NAME`). The JWT is HS256, signed with `SECRET_KEY`, and its `scope` must be `"access"`, so extension-scope tokens are rejected here. The `sub` claim holds the user UUID. **401** details: `"Not authenticated"` (no token), `"Token expired"`, `"Invalid token"`, `"Token scope not allowed here"`, `"User not found or inactive"`, or `str(exc)` for a bad `sub`. No endpoint in this part is public or extension-accessible. |
| Rate limit | No handler in this part has an `@limiter.limit(...)` decorator. All of them get the **global default** `settings.RATE_LIMIT_DEFAULT = "300/minute"` (`config.py:62`), applied by `SlowAPIMiddleware` through `Limiter(default_limits=[...])` (`api/deps.py:24-26`, `main.py:57-58`). The key is `"{remote_ip}:{hash(token)}"`, where the token is the session cookie or else the raw `authorization` header. Storage is Redis when `REDIS_URL` is set and the DB is not SQLite, otherwise `memory://`. The limiter is disabled when `ENVIRONMENT == "test"`. Exceeding it returns **429** `{"detail": "Rate limit exceeded: <limit>"}` (`main.py:68-70`). |
| Transactions | `get_db()` (`core/database.py:149`) commits after the handler returns and rolls back on any exception, including `HTTPException`. A 4xx raised mid-handler therefore persists nothing. Tasks queued with `enqueue(..., after_commit=db)` are dispatched only after that commit. |
| Path IDs | Every `{…_id}` path parameter is a `str` parsed with `parse_uuid()` (`api/deps.py:65`). A malformed UUID returns **404** `"Not found"`. A well-formed ID that is missing or belongs to another user returns **404** with the router-specific detail listed per endpoint. |
| Validation | Pydantic/FastAPI validation failures return **422** with FastAPI's standard `{"detail": [...]}` list. Handler-raised 422s use a plain string `detail`. Request models use pydantic defaults, so unknown extra fields are ignored. No endpoint declares a `response_model`: responses are plain JSON dicts built by the serializers (see **Serializers**). Status code is 200 unless stated otherwise. |
| Task dispatch | `worker/dispatch.py:enqueue(name, *args, countdown=None, after_commit=None)`. When Redis is reachable and `CELERY_TASK_ALWAYS_EAGER` is false, it calls `celery_app.send_task("hireflow.<name>", args=[...])`. Otherwise it runs the registered function in a local `ThreadPoolExecutor(max_workers=4, thread_name_prefix="hireflow-task")`. Task names used in this part: `hireflow.submit_application`, `hireflow.stage_application`, `hireflow.prepare_application`, `hireflow.scan_user`, `hireflow.check_user_email`. |
| WebSocket events | `core/websocket.py:publish_event(user_id, type, data)` publishes `{"type": <type>, "data": {...}}` to Redis channel `events:<user_id>`, or delivers in-process when there is no Redis. Event types emitted from this part: **`application_updated`** `{id, status, old_status}`, sent by every `set_status()` that changes status; **`agent_run_updated`** `{id, status}`; **`notification`** `{id, event_type, title, body, link, data, created_at}`, sent by `notify()` on the dashboard channel. |
| `set_status()` | `services/application_service.py:14` `set_status(db, app, new_status, changed_by="agent", notes=None, only_forward=False) -> bool`. It is a no-op (no history row, no event) when the status is unchanged, or when `only_forward` is set and `STATUS_RANK[new] < STATUS_RANK[old]`. Otherwise it sets `status` and `updated_at=now`. It also sets `submitted_at=now` on `applied` if unset, `approved_at=now` on `approved`, and `rejected_at=now` on `rejected`. `first_response_at=now` is set when the new status is in RESPONSE_STATUSES, `first_response_at` is unset and `submitted_at` is set. It then inserts an `ApplicationStatusHistory(application_id, old_status, new_status, changed_by, notes)` row, flushes, and emits WS `application_updated`. |
| `notify()` | `services/notifier.py:109` `notify(db, user, event_type, title, body="", link=None, data=None)`. Channels come from `EVENT_CHANNELS[event_type]`. Progress events (`application_submitted`, `self_applied`, `recruiter_email`, `status_changed`, `interview_scheduled`, `offer_received`) get ALL channels when `prefs.progress_updates_everywhere` is true (the default). **dashboard** inserts a `notifications` row and emits WS `notification`. **email** is sent only if `"email"` is in `prefs.notification_channels` (default `["email","dashboard"]`), with subject `"[HireFlow] <title>"`, through SMTP or the user's own Gmail. **chat** posts to Discord/Slack webhooks when configured. |

**`ApplicationStatus` values** (`models/enums.py:45`): `discovered, matched, skipped, preparing, pending_approval, approved, applied, acknowledged, screening, interview, assessment, final_round, offer, accepted, rejected, withdrawn, failed`.
**`STATUS_RANK`**: discovered 0; matched 1; skipped 1; preparing 2; pending_approval 3; approved 4; failed 4; applied 5; acknowledged 6; screening 7; assessment 8; interview 9; final_round 10; offer 11; accepted 12; rejected 12; withdrawn 12.
**`MANUAL_STATUSES`** (`api/applications.py:45-49`, the statuses a user may set directly): `applied, acknowledged, screening, interview, assessment, final_round, offer, accepted, rejected, withdrawn, skipped`. The statuses `discovered, matched, preparing, pending_approval, approved, failed` cannot be set manually.

#### Summary — `/api/v1/applications` (`api/applications.py`)

| Method | Path | Auth | Rate limit |
|---|---|---|---|
| GET | `/api/v1/applications` | Bearer access JWT or `hireflow_session` cookie | global default (300/minute) |
| GET | `/api/v1/applications/review-queue` | same | global default |
| POST | `/api/v1/applications/{application_id}/submit` | same | global default |
| POST | `/api/v1/applications/{application_id}/bot-apply` | same | global default |
| GET | `/api/v1/applications/{application_id}` | same | global default |
| PATCH | `/api/v1/applications/{application_id}` | same | global default |
| POST | `/api/v1/applications/{application_id}/approve` | same | global default |
| POST | `/api/v1/applications/{application_id}/skip` | same | global default |
| POST | `/api/v1/applications/{application_id}/withdraw` | same | global default |
| POST | `/api/v1/applications/{application_id}/mark-applied` | same | global default |
| POST | `/api/v1/applications/manual` | same | global default |
| POST | `/api/v1/applications/{application_id}/restage` | same | global default |
| POST | `/api/v1/applications/{application_id}/prepare` | same | global default |
| PUT | `/api/v1/applications/{application_id}/resume` | same | global default |
| POST | `/api/v1/applications/{application_id}/status` | same | global default |
| GET | `/api/v1/applications/{application_id}/history` | same | global default |

Shared helpers:
- `_get(db, user_id, application_id)` (`:52`) loads the application. It returns **404** `"Application not found"` when the row is missing or owned by another user.
- `_detail(db, app)` (`:59`) returns `application_detail(app, comms, interviews)`. Communications are ordered by `received_at DESC` and interviews by `scheduled_at ASC`. See **Serializers › application_detail**.
- `MANUAL_URL_PREFIX = "https://manual.hireflow.invalid/"` (`api/serializers.py:55`) is the synthetic `source_url` prefix for manually logged applications that have no link.

---

#### `GET /api/v1/applications`
- **Handler:** `list_applications`, `api/applications.py:66-116`
- **Auth / rate limit:** CurrentUser (access JWT) / global default.
- **Query parameters:**

| Name | Type | Default | Validation / semantics |
|---|---|---|---|
| `status` (Python name `status_filter`, `alias="status"`) | `list[str] \| None` | `None` | Repeatable (`?status=a&status=b`), and each value may also be comma-separated (`?status=a,b`). Empty parts are ignored. Every part must be an `ApplicationStatus` value, otherwise **422** `"Unknown status"`. Filters `Application.status IN (...)`. **When absent or empty**, the list excludes `discovered`, `matched` and `skipped`, because jobs not yet picked live in Swipe Review. |
| `q` | `str \| None` | `None` | Case-insensitive substring: `lower(Job.role_title) LIKE %q%` OR `lower(Job.company_name) LIKE %q%`. |
| `platform` | `str \| None` | `None` | Exact match on `Job.source_platform`. Should be an `ATSPlatform` value; the handler does not validate it. |
| `needs_review` | `bool \| None` | `None` | `Application.needs_manual_review IS <value>`. |
| `applied_by` | `Literal["me","agent"] \| None` | `None` | `"me"` keeps applications that have a history row with `new_status='applied' AND changed_by='user'` ("I Applied"). `"agent"` keeps applications without such a row. Any other value returns a FastAPI **422**. |
| `sort` | `str` | `"updated"` | `updated` sorts by `updated_at DESC`, `match` by `match_score DESC NULLS LAST`, `created` by `created_at DESC`, `company` by `Job.company_name ASC`. An unknown key silently falls back to `updated_at DESC`. |
| `page` | `int` | `1` | `ge=1` |
| `page_size` | `int` | `25` | `ge=1, le=100` |

- **Response 200:**
  - `items`: list of `application_summary(app, self_applied=<bool>)`, where `self_applied` is computed in one query for the page.
  - `total` (int): row count after all filters.
  - `page` (int), `page_size` (int).
  - `counts` (`{status_value: int}`): per-status counts over **all** of the user's applications, including discovered/matched/skipped. These counts ignore `status`, `q`, `platform` and `needs_review`, but `applied_by` is applied when given.
  - `self_applied_total` (int): count of the user's applications that have a user "applied" history row. It ignores all filters.
- **Side effects:** none (read-only).
- **Errors:** 422 `"Unknown status"`; 422 validation errors for `applied_by`, `page` and `page_size`.

#### `GET /api/v1/applications/review-queue`
- **Handler:** `review_queue`, `api/applications.py:163-168` (helpers `_submit_queue` `:128`, `_queue_item` `:136`)
- **Purpose:** the "Ready to submit" queue. It returns every `pending_approval` application as a review sheet.
- **Query:** `limit: int = 100` (`ge=1, le=200`).
- **Selection:** `Application.user_id == user AND status == pending_approval`, ordered by `match_score DESC NULLS LAST, staged_at ASC NULLS LAST, created_at ASC`.
- **Response 200:** `{"items": [queue_item…], "total": int}`. `total` counts all pending_approval applications and ignores `limit`. Each `queue_item` is `application_summary(app)` plus:

| Field | Type | Value |
|---|---|---|
| `form_screenshot_url` | str\|null | `file_url(app.form_screenshot_url)` |
| `tailored_resume_pdf_url` | str\|null | `file_url(app.tailored_resume_pdf_url)` |
| `staged_at` | ISO str\|null | |
| `blocker` | str\|null | `orch.direct_submit_blocker(user, app)`: the reason HireFlow cannot submit this itself (messages below), or null when one click will submit it. |
| `bot` | object\|null | `{"site": "Internshala", "missing": "bot_off" \| "not_synced" \| "expired" \| null}` when the job is an Internshala job (`raw_data.listing_source == "internshala"` or URL contains `internshala.com/`), else null. |
| `apply_url` | str\|null | `job.application_url`, else `job.source_url` unless it starts with `MANUAL_URL_PREFIX` (then null). |
| `rows` | list[ReviewRow] | `review_sheet.review_rows(app, resume_url=file_url(app.tailored_resume_pdf_url))`. See the shape below. |
| `attention` | int | Number of rows where `needs_attention(row)` is true: the row is flagged, or it is required and empty and its kind is not resume/file. |

- **ReviewRow shape** (`services/review_sheet.py:31`): `{key, label, kind, value, type, options, required, filled, flagged, source, confidence, note, url}`.
  - `kind` is one of `profile | question | cover_letter | resume | file`.
  - `key` is the profile kind for profile rows (`first_name, last_name, full_name, email, phone, location, linkedin, github, portfolio, current_company, current_title`), `label:<lower-cased, whitespace-collapsed label>` for questions, or `cover_letter`, `resume`, or `file:<normalized label>`.
  - `type` is the form input type: `text`, `textarea`, `select`, `radio`, `checkbox`, `number` or `file`.
  - `options` holds at most 50 items.
  - `source` is `user`, `profile`, `agent`, or the answer's own source.
  - `confidence` is null when the user set the value.
  - `url` is set only on the resume row.
  - Row order: rows needing attention first, then the rest in form order. Rows come from `form_fields`, then extra `custom_answers` not shown on the form, then a cover-letter row (when a letter exists), then a resume row (when a resume URL exists).
  - `note` values: `"Required: the agent couldn't fill this in"`, `"The form didn't take this value: check it or pick another"`, `"The agent is only N% sure: check it"` (confidence < 0.7), `"The agent wants you to check this one"`, `"Required: write or paste a cover letter"`, `"The upload didn't take on the staged form: check the screenshot"`, `"This upload didn't take on the staged form"`.
- **`blocker` messages** (`services/agent_orchestrator.py:1148`):
  1. Company verdict `suspicious` and not in `prefs.trusted_companies`: `"⚠ {company} looks like a possible fraud{ (r1; r2)}, so nothing is sent to it. If you're sure it's real, mark it legit first."`
  2. Internshala job with the bot not ready (`INTERNSHALA_MISSING`):
     - `bot_off`: `"The Internshala bot is off: turn on “Let the agent apply on Internshala” in Settings › Integrations — or apply yourself and click “I Applied”."`
     - `not_synced`: `"The Internshala bot is on, but your Internshala login isn't synced yet: log into internshala.com in Chrome, open the HireFlow extension and click “Sync Internshala session” — or apply yourself and click “I Applied”."`
     - `expired`: `"Your synced Internshala login has expired: log into internshala.com in Chrome again and click “Sync Internshala session” in the extension — or apply yourself and click “I Applied”."`
  3. Internshala job with no `form_fields` yet: `"The bot hasn't filled this Internshala form yet: click “Apply with the bot” and it fills the form and submits it for you — or apply yourself and click “I Applied”."`
  4. `job.raw_data.apply_on_site` set: `"{site} needs your own {site} login: apply there, then click “I Applied”."`
- **Side effects:** none (read-only).

#### `POST /api/v1/applications/{application_id}/submit`  → **202**
- **Handler:** `submit_now`, `api/applications.py:171-199`
- **Purpose:** the one-click submit from "Ready to submit". It saves the user's row corrections, then follows the normal explicit-approval path, the same as `/approve`.
- **Path:** `application_id` (UUID string).
- **Body:** `DirectSubmitRequest` (`schemas/application.py:40`)
  - `rows`: `list[ReviewRowIn]`, default `[]`, `max_length=500`. Each `ReviewRowIn` (`:33`) has `key: str` (`min_length=1, max_length=600`) and `value: str` (default `""`, `max_length=20000`).
  - `cover_letter`: `str | None`, default `None`, `max_length=20000`.
- **Steps and errors:**
  1. `_get`: 404 `"Application not found"`.
  2. Status must be `pending_approval` or `failed`. Otherwise **409** `"This application is {status with '_'→' '}: there's nothing to submit"`.
  3. When `direct_submit_blocker(user, app)` returns a message, **409** with that message as `detail` (messages above).
  4. `review_sheet.apply_edits(app, [(key, value)…], cover_letter)`:
     - `resume` and `file:*` keys are ignored.
     - The `cover_letter` key replaces the letter.
     - Any other key must be a profile kind or start with `label:` and be longer than 6 characters, otherwise **422** `"Unknown field '<key[:80]>'"`.
     - A row whose `value.strip()` equals the current row value counts as confirmed (no change).
     - A changed profile row becomes `overrides[key] = value`.
     - A changed question becomes `overrides["label:…"] = value`, and the matching `custom_answers` entry is updated (or appended, built from the row) with `answer=value, needs_user_review=False, source="user", confidence=1.0`.
     - A non-null body `cover_letter` that differs also replaces the letter.
  5. `review_sheet.missing_required(form_fields, edits)`: any required non-upload row that would still be empty returns **422** `"Fill in the required field(s) before submitting: <label1>; <label2>"`.
  6. Captures the current queue order (pending_approval IDs), then sets `app.field_overrides = edits.overrides or None`.
  7. Builds `note = "Submitted from Ready to submit"`, plus `" (you corrected: <comma-joined changed labels, truncated to 300 chars>)"` when anything changed.
  8. Calls `orch.approve_application(db, app, cover_letter=edits.cover_letter, custom_answers=edits.answers, note=note)`. A `ValueError` returns **409** `"Cannot approve an application in status '<status>'"`.
- **`approve_application` effects** (`services/agent_orchestrator.py:1397`). Allowed source statuses: `pending_approval, failed, matched`.
  - Sets `cover_letter` when it is not None.
  - Sets `custom_answers` with every answer forced to `needs_user_review=False` and `source=<source or "user">`.
  - `remember_answers()` inserts `user_field_mappings(field_name=<learnable key>, field_value, field_type="text")` for recognised standard questions not yet mapped.
  - Sets `retry_count = 0`.
  - `set_status(APPROVED, "user", note)` writes a history row, sets `approved_at`, and emits WS `application_updated`.
  - Enqueues **`hireflow.submit_application(application_id)`** after commit. The worker submits the form; before doing so it re-checks the blocker, rate limits and the Internshala daily limit.
- **Response 202:** `application_detail` plus `"next_id": str | null`. `next_id` is the ID of the next `pending_approval` application in queue order after this one, wrapping around. When this application was not in the queue (status `failed`), it is the first queued ID. It is null when nothing else is waiting.

#### `POST /api/v1/applications/{application_id}/bot-apply`  → **202**  *(not in the original expected list; present in code)*
- **Handler:** `bot_apply`, `api/applications.py:202-211` (calls `orch.bot_apply`, `services/agent_orchestrator.py:1049`)
- **Purpose:** "Apply with the bot" for Internshala. The click is the user's approval for this one application.
- **Body:** none.
- **Errors:**
  - 404 `"Application not found"`.
  - **409** (from a `ValueError`), in check order:
    1. `"“Apply with the bot” is for Internshala postings; use Submit for this one"`
    2. The suspicious-company message (when the company is suspicious and not trusted).
    3. The matching `INTERNSHALA_MISSING[...]` message (bot off, not synced, or expired).
    4. When the status is not one of `pending_approval, failed, matched, discovered`: `"This application is {status spaced}"`.
- **Effects:**
  - `match_details["bot_apply_requested_at"] = now ISO`
  - `review_decision = "keep"`, `auto_submit = True`, `needs_manual_review = False`, `manual_review_reason = None`, `retry_count = 0`
  - `set_status(PREPARING, "user", "You asked the bot to fill and submit this on Internshala")`, which writes a history row and emits WS `application_updated`
  - Enqueues **`hireflow.stage_application(application_id)`** after commit. The stage step fills the form and, because the bot was requested, submits automatically when no question blocks it.
- **Response 202:** `application_detail` plus `"next_id"` (same semantics as `/submit`).

#### `GET /api/v1/applications/{application_id}`
- **Handler:** `get_application`, `api/applications.py:214-216`
- **Response 200:** `application_detail(app, communications, interviews)`.
- **Errors:** 404 `"Application not found"`, or `"Not found"` for a malformed UUID.
- **Side effects:** none.

#### `PATCH /api/v1/applications/{application_id}`
- **Handler:** `update_application`, `api/applications.py:219-236`
- **Body:** `ApplicationUpdate` (`schemas/application.py:21`). All fields are optional and default to `None`. Each non-None field is applied.
  - `cover_letter: str | None` sets `app.cover_letter`.
  - `custom_answers: list[CustomAnswer] | None` replaces `app.custom_answers` with `[a.model_dump(exclude_none=True)]`. The `CustomAnswer` fields are listed under **Request schemas**.
  - `notes: str | None` sets `app.notes`. It overwrites; it does not append.
  - `status: str | None`. When truthy, it must be an `ApplicationStatus` value, otherwise **422** `"Unknown status"`. It must also be in `MANUAL_STATUSES`, otherwise **422** `"Cannot set status '<value>' manually"`. On success it calls `set_status(new, "user", "Updated manually")`, which writes a history row and emits WS `application_updated`. No ordering is enforced, so a status can move backwards.
- **Response 200:** `application_detail`.
- **Errors:** 404 `"Application not found"`; the 422s above. A 422 rolls back the field edits too.

#### `POST /api/v1/applications/{application_id}/approve`  → **202**
- **Handler:** `approve`, `api/applications.py:239-252`
- **Purpose:** explicit user approval. Together with `/submit` and `/bot-apply`, this is the only path that leads to a submission.
- **Body:** `ApproveRequest` (`schemas/application.py:28`) with `cover_letter: str | None = None` and `custom_answers: list[CustomAnswer] | None = None`.
- **Steps and errors:**
  1. 404 `"Application not found"`.
  2. Required-answer check. It runs on `body.custom_answers` (dumped with `exclude_none=True`) when provided, otherwise on the stored `app.custom_answers`. Any entry with a truthy `required` and a blank `answer` returns **422** `"Answer the required question(s) before approving: <q1>; <q2>"`.
  3. `orch.approve_application(db, app, cover_letter=body.cover_letter, custom_answers=edited)` with the default note `"Approved by user"`. Allowed statuses are `pending_approval, failed, matched`; any other status returns **409** `"Cannot approve an application in status '<status>'"`.
- Unlike `/submit`, this endpoint does no `direct_submit_blocker` check. The submit worker re-checks the blocker; when blocked, it sets `needs_manual_review` and moves the application back to `pending_approval` with the blocker as the note.
- **Effects:** same as `/submit` step 8 (`approved` status, history row, WS event, answers learned, `hireflow.submit_application` queued).
- **Response 202:** `application_detail`. There is no `next_id`.

#### `POST /api/v1/applications/{application_id}/skip`
- **Handler:** `skip`, `api/applications.py:255-261`
- **Body:** none.
- **Transition guard:** when the status is `applied` or `approved`, **409** `"Already submitted / being submitted"`. Every other status, including post-submission ones such as `interview`, may move to `skipped`.
- **Effects:** `set_status(SKIPPED, "user", "Skipped by user")` writes a history row and emits WS `application_updated`. `review_decision` is not changed.
- **Response 200:** `application_detail`.

#### `POST /api/v1/applications/{application_id}/withdraw`
- **Handler:** `withdraw`, `api/applications.py:264-268`
- **Body:** none. There is no status guard: any status can move to `withdrawn`. When the status is already `withdrawn`, nothing happens.
- **Effects:** `set_status(WITHDRAWN, "user", "Withdrawn by user")` writes a history row and emits WS `application_updated`.
- **Response 200:** `application_detail`.

#### `POST /api/v1/applications/{application_id}/mark-applied`
- **Handler:** `mark_applied`, `api/applications.py:271-279` (calls `orch.mark_self_applied`, `services/agent_orchestrator.py:1415`)
- **Purpose:** "I Applied". The user applied on their own; the agent stops working on the application and only tracks it.
- **Body (optional):** `SelfAppliedRequest | None` (`schemas/application.py:54`). It defaults to an empty `SelfAppliedRequest()` when omitted.
  - `applied_on: date | None`, as `YYYY-MM-DD`.
  - `notes: str | None`, `max_length=2000`.
- **Effects:**
  - When `notes` is given: `app.notes = f"{app.notes}\n{notes}".strip()` if notes already exist, else `app.notes = notes`. This happens even when the status move below is a no-op.
  - `mark_self_applied` is a **no-op** (returns False) when `STATUS_RANK[status] >= 5` (applied or further) and the status is not `withdrawn`. Otherwise:
    - `auto_submit = False`, `needs_manual_review = False`, `manual_review_reason = None`
    - `set_status(APPLIED, "user", "You applied on your own")` writes the history row with `changed_by="user"` that marks the application as self-applied, sets `submitted_at`, and emits WS `application_updated`.
    - When `applied_on` is today or earlier (UTC), `submitted_at = applied_on 12:00 UTC`. Future dates are ignored.
    - `notify(db, user, "self_applied", ...)` with:
      - title `"📌 Tracking: {role_title} @ {company_name}"`
      - body `"You applied on your own. HireFlow now watches your inbox for replies from {company_name} and will tell you about every update (acknowledgement, test, interview, offer)."`
      - link `"/dashboard/applications/{id}"`
      - data `{"application_id", "company", "role"}`
      - This creates a `notifications` row and emits WS `notification`. By default it also emails (subject `"[HireFlow] 📌 Tracking: …"`) and posts to chat webhooks, since `self_applied` uses all channels.
- **Response 200:** `application_detail`.
- **Errors:** 404 `"Application not found"`; 422 for a bad date or notes longer than 2000 characters.

#### `POST /api/v1/applications/manual`  → **201**
- **Handler:** `log_manual_application`, `api/applications.py:282-312`
- **Purpose:** log an application made anywhere. It lands in "I Applied" and is tracked like the rest.
- **Body:** `ManualApplicationCreate` (`schemas/application.py:61`)

| Field | Type | Default | Validation |
|---|---|---|---|
| `company_name` | str | required | `min_length=1, max_length=255`; stripped |
| `role_title` | str | required | `min_length=1, max_length=255`; stripped |
| `url` | str\|None | None | `max_length=2000`; stripped; when non-empty it must start with `http://` or `https://`, otherwise **422** `"The link must start with http:// or https://"` |
| `location` | str\|None | None | `max_length=255`; stripped; empty becomes None |
| `job_type` | str | `"internship"` | Must be a `JobType` value (`full-time, part-time, internship, contract, freelance`), otherwise **422** `"Unknown job type"` |
| `applied_on` | date\|None | None | |
| `notes` | str\|None | None | `max_length=2000` |

- **Effects:**
  1. Builds a `ScrapedJob` and calls `.finalize()`, which infers remote, experience level and salary and truncates title, company and location to 255 characters. The fields are:
     - `description = "{role} at {company} (logged by you)."`
     - `source_url = url` or `"https://manual.hireflow.invalid/{user_id}/{uuid4}"`
     - `application_url = url or None`
     - `source_platform = detect_ats_platform(url)` when a URL is given, else `custom` (`unknown` is also coerced to `custom`)
     - `raw = {"logged_manually": True}`
  2. `orch.upsert_job(db, scraped)` reuses a job with the same `source_url`, refreshing `last_checked` and `is_active`. Failing that, it reuses an active job with the same dedupe key (company, role, location). Otherwise it inserts a new `jobs` row and runs the company check. For a newly created job without a URL, `application_url` is reset to None.
  3. `orch.ensure_application(db, user, job)` reuses the user's application for that job, or inserts one with status `discovered` and `ats_platform = application_platform(job)`.
  4. When `notes` is given, `app.notes = notes`, overwriting.
  5. `orch.mark_self_applied(db, user, app, applied_on=...)`, with the same effects and no-op rule as `/mark-applied`: history row, WS `application_updated`, `self_applied` notification and emails.
- **Response 201:** `application_detail`. In it, `job.source_url` is null for synthetic manual URLs.

#### `POST /api/v1/applications/{application_id}/restage`  → **202**
- **Handler:** `restage`, `api/applications.py:315-323`
- **Body:** none.
- **Transition guard:** the status must be `pending_approval` or `failed`, otherwise **409** `"Only pending or failed applications can be re-staged"`.
- **Effects:**
  - `app.auto_submit = False`. The user is now reviewing this one personally.
  - `set_status(PREPARING, "user", "Re-filling the form")` writes a history row and emits WS `application_updated`.
  - Enqueues **`hireflow.stage_application(application_id)`** after commit. That task fills the form without submitting, screenshots it, and returns the application to `pending_approval`.
- **Response 202:** `application_detail`.

#### `POST /api/v1/applications/{application_id}/prepare`  → **202**
- **Handler:** `reprepare`, `api/applications.py:326-336`
- **Body:** none.
- **Errors (in order):**
  - 404 `"Application not found"`.
  - When the status is `approved` or `applied`: **409** `"Already submitted / being submitted"`. Every other status is allowed.
  - When the user has no active master resume: **400** `"Upload a master resume first"`.
- **Effects:**
  - `auto_submit = False`
  - `set_status(PREPARING, "user", "Re-preparing documents")` writes a history row and emits WS `application_updated`.
  - Enqueues **`hireflow.prepare_application(application_id)`** after commit. That task re-runs resume tailoring according to `resume_strategy`, cover letter generation and Greenhouse question pre-answering, then stages or marks the application ready.
- **Response 202:** `application_detail`.

#### `PUT /api/v1/applications/{application_id}/resume`
- **Handler:** `update_tailored_resume`, `api/applications.py:339-348`
- **Body:** `TailoredResumeUpdate` (`schemas/application.py:45`) with `parsed_content: dict[str, Any]` (required).
- **Errors:** 404 `"Application not found"`. When `app.tailored_resume` is None (for example the "original" resume strategy, where no tailored copy exists): **404** `"No tailored resume for this application"`.
- **Effects:**
  - `resume.parsed_content = normalize_resume(body.parsed_content)`, i.e. `ResumeContent.model_validate(...).to_dict()`, which is lenient and ignores extra keys.
  - `resume.version = (version or 1) + 1`.
  - `app.tailored_resume_pdf_url = orch.render_tailored_pdf(user, resume)`. This renders a PDF with `prefs.resume_template` (default `"classic"`), stores it at `users/{user_id}/resumes/{uuid4hex}.pdf`, and also sets `resume.pdf_url`. This is a file write.
  - No status change and no WS event.
- **Response 200:** `resume_out(resume)` including `parsed_content`.

#### `POST /api/v1/applications/{application_id}/status`
- **Handler:** `update_status`, `api/applications.py:351-361`
- **Body:** `StatusUpdate` (`schemas/application.py:49`) with `status: str` (required) and `notes: str | None` (`max_length=2000`).
- **Errors:** 404 `"Application not found"`; **422** `"Unknown status"`; **422** `"Cannot set status '<value>' manually"` when the status is not in `MANUAL_STATUSES`.
- **Effects:** `set_status(new, "user", body.notes or "Updated manually")` writes a history row and emits WS `application_updated`. There is no forward-only rule, and setting the same status is a no-op.
- **Response 200:** `application_detail`.

#### `GET /api/v1/applications/{application_id}/history`
- **Handler:** `history`, `api/applications.py:364-367`
- **Response 200:** `{"items": [history_out(h) …]}`, ordered by `created_at ASC` (relationship `order_by`).
- **Errors:** 404 `"Application not found"`.

---

### Review

Router `api/review.py` (`APIRouter(prefix="/review", tags=["review"])`, `:34`). This is Swipe Review: the user decides, card by card, which discovered jobs to apply to. Constants: `QUEUE_STATUSES = (discovered, matched)` and `MAX_BULK = 500`. `POST /bulk` is declared **before** `POST /{application_id}`, so the literal path wins.

| Method | Path | Auth | Rate limit |
|---|---|---|---|
| GET | `/api/v1/review/queue` | Bearer access JWT or `hireflow_session` cookie | global default (300/minute) |
| POST | `/api/v1/review/bulk` | same | global default |
| POST | `/api/v1/review/{application_id}` | same | global default |
| POST | `/api/v1/review/{application_id}/undo` | same | global default |
| POST | `/api/v1/review/{application_id}/details` | same | global default |

Shared helpers:
- `_get(db, user, application_id)` (`:130`) returns **404** `"Job not found"` when the application is missing or owned by another user.
- `_queue_query(user, min_score, job_type, remote, q)` (`:53`) selects the user's applications that are joined to their Job and meet all of these conditions:
  - `status IN (discovered, matched)`
  - `review_decision IS NULL`
  - `Job.is_active IS TRUE`
  - plus the optional filters:
    - `min_score`: `match_score >= min_score`
    - `job_type`: must be a `JobType` value, otherwise **422** `"Unknown job type"`; matches `Job.job_type`
    - `remote`: `Job.is_remote IS remote`
    - `q`: case-insensitive substring of role_title, company_name or location
- `_stats(db, user)` (`:117`) returns `{"remaining": int, "kept_today": int, "skipped_today": int, "kept_total": int}`:
  - `remaining` is the size of the unfiltered queue.
  - `kept_today` and `skipped_today` count the user's applications with `review_decision` keep or skip and `reviewed_at` within the **last 24 hours** (rolling).
  - `kept_total` is the all-time count of `review_decision == "keep"`.
- `_card(app, prefs)` (`:88`) returns:

| Field | Type | Value |
|---|---|---|
| `focus.location_tier` | int\|null | 0 = prime city, 1 = focus country, 2 = remote or unspecified, 3 = abroad. Set when `prefs.location_focus` is enabled and has a country, else null. |
| `focus.season` | str\|null | `season_status(...)[0]`: `match`, `conflict`, `other_mentioned`, `immediate` or `unknown`. Set when `prefs.internship_season` parses, else null. |
| `focus.season_label` | str\|null | e.g. `"Summer 2027"` |
| `focus.country` | str\|null | The focus country, title-cased. |
| `application_id` | str | |
| `status` | str | |
| `match_score` | int\|null | |
| `match_reasoning` | str\|null | |
| `strong_matches` | list | `match_details.strong_matches`, or `[]` |
| `missing_skills` | list | `match_details.missing_skills`, or `[]` |
| `heads_up` | list | `match_details.heads_up`, or `[]` |
| `scores` | object | The subset of `skills_match, experience_match, industry_match, location_match, compensation_match` from `match_details` whose values are not null. |
| `job` | object | `job_out(job, prefs=prefs)` plus `description` (first 2500 characters), `sponsorship` (`raw_data.sponsorship`), `terms` (`raw_data.terms` or `[]`) and `listing_source` (`raw_data.listing_source`). |
| `discovered_at` | ISO str | `job.discovered_at` |

- **Keep and skip transitions** (`services/agent_orchestrator.py:737-775`):
  - `REVIEWABLE = (discovered, matched, skipped)`.
  - `keep_application` requires a reviewable status, otherwise `ValueError("This job is already {status spaced}")`. It then:
    - sets `review_decision="keep"`, `reviewed_at=now`, `auto_submit=prefs.auto_submit_kept` (default true)
    - calls `set_status(PREPARING, decided_by="user", note)`
    - enqueues **`hireflow.prepare_application`** after commit
  - `skip_application` has the same guard. It sets `review_decision="skip"` and `reviewed_at=now`, then calls `set_status(SKIPPED, "user", note)`.

#### `GET /api/v1/review/queue`
- **Handler:** `queue`, `api/review.py:137-167`
- **Query:**

| Name | Type | Default | Validation |
|---|---|---|---|
| `limit` | int | 20 | `ge=1, le=100` |
| `min_score` | int\|None | None | `ge=0, le=100` |
| `job_type` | str\|None | None | `JobType` value, otherwise **422** `"Unknown job type"` |
| `remote` | bool\|None | None | |
| `q` | str\|None | None | Substring of role, company or location |

- **Side effects (writes despite being a GET):**
  1. `orch.backfill_company_checks(db, limit=500)` gives up to 500 jobs (any user's) that have a NULL `company_verdict` a rule-based verdict, tier and check.
  2. `orch.skip_suspicious_waiting(db, user)` runs when `prefs.skip_suspicious_companies` (default true) is set. It looks at the user's undecided `discovered`/`matched` applications whose job verdict is `suspicious` and that are not trusted. For each, it sets `match_reasoning = "Possible fraud: <up to 2 reasons>"` (or `"Possible fraud: the company check flagged this posting"`), then calls `set_status(SKIPPED, "agent", reasoning)`.
  3. `orch.skip_ineligible_waiting(db, user)` looks at the user's undecided `discovered`/`matched` applications that fail a hard filter (`filter_reasons(job, prefs)[0]`, the same filters a scan applies, with graduation year taken from the master resume). For each, it sets `match_reasoning = <first reason>`, then calls `set_status(SKIPPED, "agent", reason)`.
  - Each status change writes a history row and emits WS `application_updated`.
- **Ordering:**
  1. Trust: `company_tier IS NOT NULL` → 0, verdict `verified` → 1, other → 2, `suspicious` → 3.
  2. Location-focus tier, when a focus is configured.
  3. Season rank (0 when the title contains the season year, or the description contains `"<season> <year>"` or `"<year> <season>"`), when a season is configured.
  4. `match_score DESC NULLS LAST`, `Job.posted_date DESC NULLS LAST`, `Job.discovered_at DESC`, `Application.id`. The final key keeps the order stable across refetches.
- **Response 200:**
  - `items`: `[card…]`, at most `limit`.
  - `matching` (int): count matching the filters.
  - `stats`: `_stats`.
  - `settings`: `{"auto_submit_kept": bool (prefs, default true), "review_mode": str (prefs.review_mode or "swipe")}`.
  - `has_master_resume` (bool).

#### `POST /api/v1/review/bulk`
- **Handler:** `bulk_decide`, `api/review.py:170-184`
- **Body:** `BulkDecisionIn` (`api/review.py:44`)

| Field | Type | Default | Validation |
|---|---|---|---|
| `decision` | `Literal["keep","skip"]` | required | |
| `application_ids` | `list[str] \| None` | None | `max_length=500`. Each ID goes through `parse_uuid` (malformed returns 404 `"Not found"`). An empty list matches nothing. |
| `min_score` | int\|None | None | `ge=0, le=100` |
| `job_type` | str\|None | None | `JobType` value, otherwise 422 `"Unknown job type"` |
| `remote` | bool\|None | None | |
| `q` | str\|None | None | |

- **Steps and errors:**
  - When `decision == "keep"` and there is no master resume: **400** `"Upload a master resume first"`.
  - Selects from `_queue_query` with the filters, restricted to `application_ids` when given, ordered by `match_score DESC NULLS LAST`, limited to 500.
  - `keep` calls `keep_application(..., note="Kept in Swipe Review (bulk)")` for each: status becomes `preparing`, a history row is written, WS `application_updated` is emitted, and `hireflow.prepare_application` is queued per application.
  - `skip` calls `skip_application(..., note="Skipped in Swipe Review (bulk)")` for each: status becomes `skipped`.
- **Response 200:** `{"count": int, "decision": "keep" | "skip", "stats": {...}}`.

#### `POST /api/v1/review/{application_id}`
- **Handler:** `decide`, `api/review.py:187-199`
- **Body:** `DecisionIn` (`api/review.py:40`) with `decision: Literal["keep","skip"]`.
- **Errors:**
  - 404 `"Job not found"`.
  - `keep` without a master resume: **400** `"Upload a master resume first"`.
  - Status not in `discovered, matched, skipped`: **409** `"This job is already {status spaced}"`.
- **Effects:**
  - `keep`: `keep_application(db, user, app)` with note `"Kept in Swipe Review"`. Status becomes `preparing`, `review_decision`, `reviewed_at` and `auto_submit` are set, and `hireflow.prepare_application` is queued.
  - `skip`: `skip_application(db, app)` with note `"Skipped in Swipe Review"`. Status becomes `skipped`.
  - Both write a history row and emit WS `application_updated`.
  - Unlike the queue, a single decision may keep an application that is already `skipped`.
- **Response 200:** `{"application": application_summary(app), "stats": {...}}`.

#### `POST /api/v1/review/{application_id}/undo`
- **Handler:** `undo`, `api/review.py:202-209` (calls `orch.undo_review`, `services/agent_orchestrator.py:764`)
- **Errors:** 404 `"Job not found"`. A `ValueError` returns **409** with one of:
  - `"This job has not been swiped"`, when `review_decision` is null.
  - `"This job is already {status spaced}"`, when the decision was `skip` and the status is no longer `skipped`.
  - `"Preparation has already started — withdraw it from Applications instead"`, when the decision was `keep` and either the status is not `preparing` or a `tailored_resume_id` already exists.
- **Effects:**
  - `review_decision = None`, `auto_submit = False`. `reviewed_at` is not cleared.
  - `set_status(MATCHED, "user", "Swipe undone")` writes a history row and emits WS `application_updated`.
  - A `prepare_application` task already queued becomes stale. It exits because the status is no longer `preparing`.
- **Response 200:** `{"card": _card(app, user.prefs), "stats": {...}}`.

#### `POST /api/v1/review/{application_id}/details`
- **Handler:** `details`, `api/review.py:212-217` (calls `orch.enrich_job`, `services/agent_orchestrator.py:928`)
- **Purpose:** fetch the full description for a curated-list posting that carries only a title.
- **Effects:** runs only when `job.raw_data.listing_source` is set and the description is shorter than 400 characters. It fetches the posting with `fetch_job_from_url(application_url or source_url)`, using the network. When the fetched description is longer, it updates:
  - `description`
  - `requirements`, when empty
  - `salary_min`, `salary_max` and `salary_currency`, when found
  - `extracted_skills`
  - the job embedding (cleared and recomputed)
  - Fetch errors are swallowed.
- **Response 200:** `_card(app, user.prefs)`, unwrapped (not inside `{"card": …}`).
- **Errors:** 404 `"Job not found"`.

---

### Agent

Router `api/agent.py` (`APIRouter(prefix="/agent", tags=["agent"])`, `:23`). It starts scans, inspects runs (the audit log) and triggers e-mail checks.

| Method | Path | Auth | Rate limit |
|---|---|---|---|
| POST | `/api/v1/agent/start-scan` | Bearer access JWT or `hireflow_session` cookie | global default (300/minute) |
| GET | `/api/v1/agent/status` | same | global default |
| GET | `/api/v1/agent/runs` | same | global default |
| GET | `/api/v1/agent/runs/{run_id}` | same | global default |
| POST | `/api/v1/agent/runs/{run_id}/cancel` | same | global default |
| POST | `/api/v1/agent/check-email` | same | global default |

#### `POST /api/v1/agent/start-scan`  → **202**
- **Handler:** `start_scan`, `api/agent.py:26-42`
- **Body:** `StartScanRequest` (`schemas/agent.py:8`) with `platforms: list[str] | None = None`.
- **Platform resolution** (`orch.scan_platforms`, `services/agent_orchestrator.py:272`):
  - A non-empty `platforms` in the body is used as given.
  - Otherwise the scan uses `prefs.platforms` (default `["internshala","linkedin","internships","greenhouse","lever","ashby","workday","generic"]`), or else every scraper key. In this case, when `prefs.scan_top_companies` is set (default true), `"top_companies"` is prepended if it is missing.
  - Valid keys (`scrapers/__init__.py:21`): `top_companies, internshala, internships, greenhouse, lever, ashby, workday, linkedin, indeed, glassdoor, wellfound, generic`.
- **Errors:**
  - Unknown platform: **422** `"Unknown platforms: ['x', 'y']"` (Python list repr).
  - When the user already has an `agent_runs` row with `run_type="scan"`, `status="running"` and `started_at` in the last hour: **409** `"A scan is already running"`.
- **Effects:**
  - Inserts `AgentRun(user_id, run_type="scan", trigger="user", status="running", log=[{"ts": now ISO, "level": "info", "message": "Scan queued"}])` and flushes it to obtain the ID.
  - Enqueues **`hireflow.scan_user(user_id, "user", platforms, run_id)`** after commit. The task runs `orch.run_scan` on that existing run, which pushes WS `agent_run_updated` as the run progresses and finishes.
- **Response 202:** `run_out(run, include_log=True)`.

#### `GET /api/v1/agent/status`
- **Handler:** `agent_status`, `api/agent.py:45-72`
- **Response 200:**

| Field | Type | Value |
|---|---|---|
| `has_master_resume` | bool | An active master resume exists. |
| `to_review` | int | Applications with status `discovered` or `matched` and `review_decision IS NULL`. |
| `review_mode` | str | `prefs.review_mode`, or `"swipe"`. |
| `pending_approval` | int | Count with status `pending_approval`. |
| `preparing` | int | Count with status `preparing`. |
| `approved` | int | Count with status `approved`. |
| `applied_today` | int | `rate_limiter.applications_today(user_id)`, the Redis or in-memory daily counter. |
| `daily_limit` | int\|null | `prefs.max_applications_per_day` (default 25). |
| `running_runs` | list | Up to 5 `run_out(r)` for runs with `status="running"`, `started_at DESC`, without the log. |
| `last_scan_at` | ISO\|null | `user.last_scan_at` |
| `next_scan_at` | ISO\|null | `last_scan_at + scan_interval_hours` (default 6) when `last_scan_at` is set and `prefs.scan_enabled` is true (default), else null. |
| `scan_enabled` | bool | `prefs.scan_enabled`, default true. |
| `google_connected` | bool | A Google access or refresh token is stored. |
| `linkedin_connected` | bool | `bool(user.linkedin_session_cookie)` |

- **Side effects:** none.

#### `GET /api/v1/agent/runs`
- **Handler:** `list_runs`, `api/agent.py:75-83`
- **Query:**
  - `run_type: str | None`. Exact match on `AgentRun.run_type`, which is one of `scan | apply | email_check | linkedin_sync | prepare`. Not validated.
  - `page: int = 1` (`ge=1`).
  - `page_size: int = 25` (`ge=1, le=100`).
- **Response 200:** `{"items": [run_out(r) …] (no log), "total": int, "page": int}`, ordered by `started_at DESC`. The response has no `page_size` key.

#### `GET /api/v1/agent/runs/{run_id}`
- **Handler:** `get_run`, `api/agent.py:86-91`
- **Response 200:** `run_out(run, include_log=True)`.
- **Errors:** **404** `"Run not found"` when the run is missing or belongs to another user.

#### `POST /api/v1/agent/runs/{run_id}/cancel`
- **Handler:** `cancel_run`, `api/agent.py:94-103`
- **Errors:** **404** `"Run not found"`.
- **Effects:** only when `run.status == "running"`. Sets `status = "cancelled"` and `completed_at = now`, and emits WS **`agent_run_updated`** `{"id": run_id, "status": "cancelled"}`. A running scan notices within a second or two and stops. A run that is not running is returned unchanged; this is not an error.
- **Response 200:** `run_out(run)`, without the log.

#### `POST /api/v1/agent/check-email`  → **202**
- **Handler:** `check_email`, `api/agent.py:106-111`
- **Errors:** when Google is not connected, **400** `"Connect your Google account first"`.
- **Effects:** enqueues **`hireflow.check_user_email(user_id)`** after commit. The task runs `sync_user_inbox`. On a `GoogleAuthError` it sends `notify("session_expired", "Google access expired", "Reconnect Google in Settings to keep monitoring recruiter e-mails. (<err>)", link="/dashboard/settings")`.
- **Response 202:** `{"queued": true}`.

---

### Communications

Router `api/communications.py` (`APIRouter(prefix="/communications", tags=["communications"])`, `:17`). It covers recruiter e-mail held in Gmail. The helper `_get` (`:20`) returns **404** `"Communication not found"` when the row is missing or belongs to another user.

| Method | Path | Auth | Rate limit |
|---|---|---|---|
| GET | `/api/v1/communications` | Bearer access JWT or `hireflow_session` cookie | global default (300/minute) |
| GET | `/api/v1/communications/{comm_id}` | same | global default |
| PATCH | `/api/v1/communications/{comm_id}` | same | global default |
| POST | `/api/v1/communications/{comm_id}/draft` | same | global default |
| POST | `/api/v1/communications/{comm_id}/send` | same | global default |

#### `GET /api/v1/communications`
- **Handler:** `list_communications`, `api/communications.py:27-54`
- **Query:**

| Name | Type | Default | Validation / semantics |
|---|---|---|---|
| `intent` | str\|None | None | Must be an `EmailIntent` value (`acknowledgment, rejection, interview_invite, assessment, offer, follow_up, info_request, generic, unknown`), otherwise **422** `"Unknown intent"`. Matches `detected_intent`. |
| `action_required` | bool\|None | None | When given: `is_action_required IS <value> AND action_taken IS FALSE`. |
| `application_id` | str\|None | None | Goes through `parse_uuid` (malformed returns 404 `"Not found"`). Matches `Communication.application_id`. |
| `page` | int | 1 | `ge=1` |
| `page_size` | int | 25 | `ge=1, le=100` |

- **Ordering:** `received_at DESC NULLS LAST`.
- **Response 200:** `{"items": [...], "total": int, "page": int}`. Each item is the **full** `communication_out(c)` plus `"application"`, which is `{"id", "company_name", "role_title", "status"}` for the linked application, or null.
- **Side effects:** none.

#### `GET /api/v1/communications/{comm_id}`
- **Handler:** `get_communication`, `api/communications.py:57-59`
- **Response 200:** the full `communication_out(comm)`. Errors: 404 `"Communication not found"`.

#### `PATCH /api/v1/communications/{comm_id}`
- **Handler:** `update_communication`, `api/communications.py:62-77`
- **Body:** `CommunicationUpdate` (`schemas/agent.py:36`). All fields are optional and default to None. Each non-None field is applied.
  - `action_taken: bool | None`
  - `suggested_reply: str | None`
  - `application_id: str | None`. `""` unlinks the communication (sets it to null). Otherwise the value must be the UUID of one of the user's applications, else **404** `"Application not found"` (or `"Not found"` when malformed).
- **Response 200:** the full `communication_out(comm)`.

#### `POST /api/v1/communications/{comm_id}/draft`
- **Handler:** `create_draft`, `api/communications.py:80-91`
- **Body:** `SendReplyRequest` (`schemas/agent.py:42`) with `body: str` (`min_length=1, max_length=20000`).
- **Effects:**
  - Builds the Gmail v1 service with the user's OAuth credentials, refreshing the access token if needed and persisting it.
  - `create_reply_draft` (`services/gmail_service.py:127`) creates a **Gmail draft** (`users.drafts.create`):
    - `To = comm.sender_email`
    - `From = user.google_email` when set
    - `Subject = "Re: <subject>"`, unless the subject already starts with `re:` (case-insensitive)
    - the body text, and `threadId = comm.gmail_thread_id`
    - no In-Reply-To header
  - Sets `comm.gmail_draft_id = <draft id>` and `comm.suggested_reply = body.body`.
- **Errors:** **400** with `str(exc)` for a `GoogleAuthError` or `GoogleNotConfigured`, e.g. `"Google OAuth is not configured"`, `"Google account not connected"`, `"Google token refresh failed: …"`. Gmail API errors are not caught and return 500.
- **Response 200:** the full `communication_out(comm)`.

#### `POST /api/v1/communications/{comm_id}/send`
- **Handler:** `send`, `api/communications.py:94-102` (calls `send_reply`, `services/gmail_service.py:145`)
- **Purpose:** send a reply from the user's Gmail. This happens only on explicit user action.
- **Body:** `SendReplyRequest`, with `body` of 1–20000 characters.
- **Effects:**
  - **Gmail send** (`users.messages.send`) with `To=comm.sender_email`, `From=user.google_email` (when set), `Subject` `"Re: …"` as above, and `threadId=comm.gmail_thread_id`.
  - Inserts a new **outbound** `communications` row with:
    - `direction="outbound"`, `gmail_message_id=<sent id>`, `gmail_thread_id`
    - `application_id` copied from the original
    - `sender_email = user.google_email or user.email`, `sender_name = user.full_name`
    - `recipient_email = comm.sender_email`
    - `subject`, `body_text`, `received_at = now`
  - Sets `comm.action_taken = True` on the original.
- **Errors:** **400** `str(exc)` for Google auth or configuration errors.
- **Response 200:** `{"sent": true, "message_id": "<gmail message id or ''>"}`.

---

### Interviews

Router `api/interviews.py` (`APIRouter(prefix="/interviews", tags=["interviews"])`, `:21`). It covers interviews with Google Calendar sync and AI prep notes.
- `_get` (`:24`) returns **404** `"Interview not found"` when the interview is missing or its application belongs to another user.
- `_itype(value)` (`:31`) returns None for a falsy value. Otherwise the value must be an `InterviewType` (`phone_screen, video_call, onsite, technical, behavioral, panel, take_home, pair_programming, other`), else **422** `"Unknown interview type"`.

| Method | Path | Auth | Rate limit |
|---|---|---|---|
| GET | `/api/v1/interviews` | Bearer access JWT or `hireflow_session` cookie | global default (300/minute) |
| GET | `/api/v1/interviews/{interview_id}` | same | global default |
| POST | `/api/v1/interviews` | same | global default |
| PATCH | `/api/v1/interviews/{interview_id}` | same | global default |
| POST | `/api/v1/interviews/{interview_id}/prep` | same | global default |
| DELETE | `/api/v1/interviews/{interview_id}` | same | global default |

Shared services:
- `generate_prep(resume_content, application, interview)` (`services/calendar_manager.py:71`) uses the LLM prompt `interview_prep` (schema `INTERVIEW_PREP_SCHEMA`, effort medium) when an LLM is available and returns `prep_notes`. Otherwise it falls back to `heuristic_prep`. The result is `{prep_notes, company_research, likely_questions: [{question, answer_outline}], method}`.
- `upsert_calendar_event(db, user, application, interview)` (`:136`) does nothing unless Google is connected **and** a granted scope contains `"calendar"`. It calls Google Calendar `events.update` on `primary` when `google_event_id` is set, else `events.insert`. It then sets `interview.google_event_id` and `interview.google_event_link` (the `htmlLink`). All errors are logged and swallowed. The event body (`build_event_body`, `:103`):
  - `summary`: `"Interview: {role} @ {company}"`.
  - `description`: up to 7900 characters, made of `"Join: <link>"`, `"PREP NOTES\n…"`, `"LIKELY QUESTIONS\n- …"` (at most 12), `"COMPANY RESEARCH\n…"` and `"Created by HireFlow"`.
  - `location`: the meeting link, else the physical location, else `""`.
  - `start` and `end` (start + `duration_minutes`), with `timeZone` set to `interview.timezone` or `"UTC"`.
  - `reminders`: `{useDefault: false, overrides: [{email, 1440}, {popup, 60}]}`.
  - `extendedProperties.private.hireflow_interview_id = <interview id>`.
- `meeting_platform(link)` (`services/email_parser.py:101`) maps the link to a platform: `zoom.us` → `zoom`, `meet.google` → `google_meet`, `teams.` → `teams`, `webex` → `webex`, `calendly` → `calendly`, `coderpad` → `coderpad`, `jit.si` → `jitsi`. Any other link gives `other`, and no link gives null.

#### `GET /api/v1/interviews`
- **Handler:** `list_interviews`, `api/interviews.py:40-50`
- **Query:** `upcoming: bool | None = None`.
  - `true`: `scheduled_at >= now`, ordered ASC.
  - `false`: `scheduled_at < now`, ordered DESC.
  - Omitted: all interviews, ordered `scheduled_at DESC`.
  - The result is always limited to **200** rows.
- **Response 200:** `{"items": [interview_out(i) …]}`, using the full (not brief) form.

#### `GET /api/v1/interviews/{interview_id}`
- **Handler:** `get_interview`, `api/interviews.py:53-55`
- **Response 200:** the full `interview_out`. Errors: 404 `"Interview not found"`.

#### `POST /api/v1/interviews`  → **201**
- **Handler:** `create_interview`, `api/interviews.py:58-79`
- **Body:** `InterviewCreate` (`schemas/agent.py:12`)

| Field | Type | Default | Validation |
|---|---|---|---|
| `application_id` | str | required | One of the user's applications, otherwise **404** `"Application not found"` (`"Not found"` when malformed) |
| `scheduled_at` | datetime | required | A naive value is treated as UTC |
| `duration_minutes` | int | 60 | `ge=5, le=600` |
| `timezone` | str | `"UTC"` | |
| `interview_type` | str\|None | `"video_call"` | `InterviewType` value, otherwise 422 `"Unknown interview type"`; empty or null gives null |
| `meeting_link` | str\|None | None | |
| `physical_location` | str\|None | None | |
| `interviewer_names` | list[str]\|None | None | |

- **Effects:**
  1. Inserts an `interviews` row with `meeting_platform = meeting_platform(link)`, or `"onsite"` when there is no link but a `physical_location`, and `outcome = "pending"`.
  2. Generates prep with `generate_prep` against the master resume's `parsed_content` (`{}` when there is none) and sets `prep_notes`, `company_research` and `likely_questions`.
  3. Writes the Google Calendar event (insert) via `upsert_calendar_event`, when calendar access is available.
  4. `set_status(app, INTERVIEW, "user", "Interview added", only_forward=True)` writes a history row and emits WS `application_updated`, but only when that moves the application forward: nothing changes when the current rank is above `interview` (9), e.g. `final_round`, `offer`, `accepted`, `rejected`, `withdrawn`.
  - No notification is created.
- **Response 201:** the full `interview_out(interview)`.

#### `PATCH /api/v1/interviews/{interview_id}`
- **Handler:** `update_interview`, `api/interviews.py:82-100`
- **Body:** `InterviewUpdate` (`schemas/agent.py:23`). Every field is optional. Only fields **present in the JSON** are applied (`model_dump(exclude_unset=True)`), including explicit nulls.

| Field | Type | Validation |
|---|---|---|
| `scheduled_at` | datetime\|None | A naive value is treated as UTC |
| `duration_minutes` | int\|None | `ge=5, le=600` |
| `timezone` | str\|None | |
| `interview_type` | str\|None | Goes through `_itype` (422 `"Unknown interview type"`) |
| `meeting_link` | str\|None | |
| `physical_location` | str\|None | |
| `interviewer_names` | list[str]\|None | |
| `outcome` | str\|None | Free text (convention: `passed`, `failed`, `pending`, `rescheduled`, `cancelled`) |
| `feedback` | str\|None | |
| `prep_notes` | str\|None | |

- **Effects:**
  - Sets each attribute.
  - When `meeting_link` is present, recomputes `meeting_platform` from it. There is no onsite fallback here.
  - When `scheduled_at` is present, resets `reminder_24h_sent` and `reminder_1h_sent` to false.
  - When any of `scheduled_at, duration_minutes, meeting_link, physical_location, timezone, prep_notes` is present, writes the Google Calendar event (update, or insert if it has no ID yet).
  - Does not change the application status.
- **Response 200:** the full `interview_out`. Errors: 404 `"Interview not found"`; 422s.

#### `POST /api/v1/interviews/{interview_id}/prep`
- **Handler:** `regenerate_prep`, `api/interviews.py:103-112`
- **Body:** none.
- **Effects:** regenerates `prep_notes`, `company_research` and `likely_questions` (LLM or heuristic), overwriting them. Then upserts the Google Calendar event so its description holds the new prep.
- **Response 200:** the full `interview_out`. Errors: 404 `"Interview not found"`.

#### `DELETE /api/v1/interviews/{interview_id}`
- **Handler:** `delete_interview`, `api/interviews.py:115-120`
- **Effects:**
  - When `google_event_id` is set and calendar access is available, deletes the event with `events.delete(calendarId="primary", eventId=…)`. Errors are swallowed, and `google_event_id` is cleared.
  - Deletes the `interviews` row.
  - The application status is unchanged.
- **Response 200:** `{"ok": true}`. Errors: 404 `"Interview not found"`.

---

### Analytics

Router `api/analytics.py` (`APIRouter(tags=["analytics"])`, `:13`, no prefix).

| Method | Path | Auth | Rate limit |
|---|---|---|---|
| GET | `/api/v1/analytics/overview` | Bearer access JWT or `hireflow_session` cookie | global default (300/minute) |

#### `GET /api/v1/analytics/overview`
- **Handler:** `overview`, `api/analytics.py:16-18` (calls `compute_overview`, `services/analytics.py:28`)
- **Query:** `days: int | None = None` (`ge=1, le=3650`). When given, only applications with `updated_at >= now - days` are counted.
- **Definitions (over the filtered applications):**
  - *submitted*: status in SUBMITTED_STATUSES (`applied, acknowledged, screening, interview, assessment, final_round, offer, accepted, rejected`), or `submitted_at` set.
  - *responded*: submitted and (status in RESPONSE_STATUSES (`acknowledged … rejected`, excluding `applied`), or `first_response_at` set).
  - *interviewed*: submitted and status in INTERVIEW_STATUSES (`screening, interview, assessment, final_round, offer, accepted`).
  - *offers*: status `offer` or `accepted`.
  - Rates use `_pct(n, d) = round(100*n/d, 1)`, or `0.0` when `d = 0`.
- **Response 200:**
  - `totals`: `{total, discovered, matched, preparing, pending_approval, approved, applied (=#submitted), responses (=#responded), interviews (=#interviewed), offers, rejected, skipped, failed}`, all ints.
  - `by_status`: `{status_value: int}`, holding only statuses that are present.
  - `rates`: `{response_rate: responded/submitted, interview_rate: interviewed/submitted, offer_rate: offers/interviewed, avg_days_to_response: float|null}`. `avg_days_to_response` averages `(first_response_at − submitted_at)` in days, rounded to 1 decimal.
  - `timeline`: exactly 30 entries `{date: "YYYY-MM-DD", discovered, applied, responses}` for the last 30 UTC days, oldest first. Counts are bucketed by `created_at`, `submitted_at` and `first_response_at` respectively.
  - `match_distribution`: 10 buckets `{range: "0-9" | "10-19" | … | "80-89" | "90-100", count}`.
  - `platforms`: `[{platform, discovered, applied, responses, interviews, response_rate, interview_rate}]`, keyed by `Job.source_platform` and sorted by `applied` DESC.
  - `top_keywords`: at most 12 entries `{keyword, applications, callbacks, callback_rate, lift}`. They come from the skills of submitted jobs that appear at least twice, sorted by `callback_rate` DESC then `applications` DESC. A positive outcome is an interview stage, or a response that is not a rejection. `lift` is the rate divided by the base rate, or `0`.
  - `upcoming_interviews`: at most 5 entries `{id, company, role, scheduled_at, type}` with `scheduled_at >= now`, ascending. This list ignores `days`.
  - `recent_runs`: at most 10 entries `{id, run_type, status, started_at, jobs_discovered, jobs_matched, errors_count}`, ordered by `started_at DESC`. This list ignores `days`.
- **Side effects:** none.

---

### Notifications

These routes are served by the **analytics router** (`api/analytics.py`, no prefix), which declares the `/notifications…` paths itself.

| Method | Path | Auth | Rate limit |
|---|---|---|---|
| GET | `/api/v1/notifications` | Bearer access JWT or `hireflow_session` cookie | global default (300/minute) |
| POST | `/api/v1/notifications/{notification_id}/read` | same | global default |
| POST | `/api/v1/notifications/read-all` | same | global default |

#### `GET /api/v1/notifications`
- **Handler:** `list_notifications`, `api/analytics.py:21-30`
- **Query:**
  - `unread: bool | None = None`. Only `true` filters, to `is_read IS FALSE`. `false` and omitted both return all notifications.
  - `limit: int = 30` (`ge=1, le=200`).
- **Ordering:** `created_at DESC`.
- **Response 200:** `{"items": [notification_out(n) …], "unread": int}`. `unread` is the total unread count for the user, independent of `limit` and the filter.

#### `POST /api/v1/notifications/{notification_id}/read`
- **Handler:** `mark_read`, `api/analytics.py:33-39`
- **Errors:** **404** `"Notification not found"` (or `"Not found"` for a malformed UUID).
- **Effects:** `is_read = True`. No WS event.
- **Response 200:** `notification_out(n)`.

#### `POST /api/v1/notifications/read-all`
- **Handler:** `mark_all_read`, `api/analytics.py:42-46`
- **Effects:** a bulk `UPDATE notifications SET is_read = true WHERE user_id = :user AND is_read = false`. No WS event.
- **Response 200:** `{"ok": true}`.

---

### Request Schemas

These are the Pydantic request models used by the routers above. Pydantic defaults apply, so extra keys are ignored.

| Model (file:line) | Fields |
|---|---|
| `CustomAnswer` (`schemas/application.py:9`) | `question: str` (required); `answer: str = ""`; `field_type: str \| None = "text"`; `confidence: float \| None = None`; `needs_user_review: bool \| None = False`; `options: list[str] \| None = None`; `required: bool \| None = False`; `source: str \| None = None`; `field_id: str \| None = None` |
| `ApplicationUpdate` (`:21`) | `cover_letter: str \| None`; `custom_answers: list[CustomAnswer] \| None`; `notes: str \| None`; `status: str \| None` (all default None) |
| `ApproveRequest` (`:28`) | `cover_letter: str \| None = None`; `custom_answers: list[CustomAnswer] \| None = None` |
| `ReviewRowIn` (`:33`) | `key: str` (`min_length=1, max_length=600`); `value: str = ""` (`max_length=20000`) |
| `DirectSubmitRequest` (`:40`) | `rows: list[ReviewRowIn] = []` (`max_length=500`); `cover_letter: str \| None = None` (`max_length=20000`) |
| `TailoredResumeUpdate` (`:45`) | `parsed_content: dict[str, Any]` (required) |
| `StatusUpdate` (`:49`) | `status: str` (required); `notes: str \| None = None` (`max_length=2000`) |
| `SelfAppliedRequest` (`:54`) | `applied_on: date \| None = None`; `notes: str \| None = None` (`max_length=2000`) |
| `ManualApplicationCreate` (`:61`) | `company_name: str` (1–255); `role_title: str` (1–255); `url: str \| None` (≤2000); `location: str \| None` (≤255); `job_type: str = "internship"`; `applied_on: date \| None`; `notes: str \| None` (≤2000) |
| `StartScanRequest` (`schemas/agent.py:8`) | `platforms: list[str] \| None = None` |
| `InterviewCreate` (`schemas/agent.py:12`) | `application_id: str`; `scheduled_at: datetime`; `duration_minutes: int = 60` (`ge=5, le=600`); `timezone: str = "UTC"`; `interview_type: str \| None = "video_call"`; `meeting_link: str \| None`; `physical_location: str \| None`; `interviewer_names: list[str] \| None` |
| `InterviewUpdate` (`schemas/agent.py:23`) | `scheduled_at: datetime \| None`; `duration_minutes: int \| None` (`ge=5, le=600`); `timezone`, `interview_type`, `meeting_link`, `physical_location`: `str \| None`; `interviewer_names: list[str] \| None`; `outcome`, `feedback`, `prep_notes`: `str \| None` |
| `CommunicationUpdate` (`schemas/agent.py:36`) | `action_taken: bool \| None`; `application_id: str \| None` (`""` unlinks); `suggested_reply: str \| None` |
| `SendReplyRequest` (`schemas/agent.py:42`) | `body: str` (`min_length=1, max_length=20000`) |
| `DecisionIn` (`api/review.py:40`) | `decision: Literal["keep","skip"]` |
| `BulkDecisionIn` (`api/review.py:44`) | `decision: Literal["keep","skip"]`; `application_ids: list[str] \| None` (`max_length=500`); `min_score: int \| None` (`ge=0, le=100`); `job_type: str \| None`; `remote: bool \| None`; `q: str \| None` |

The other schema files are used by routers outside this part: `schemas/job.py` (`JobImportRequest`), `schemas/resume.py`, `schemas/resume_content.py` (here only through `normalize_resume`) and `schemas/user.py`.

---

### Serializers

`backend/app/api/serializers.py` turns models into JSON dicts. All datetimes and dates go through `iso()`, and enums through `enum()`.

| Function (line) | Output |
|---|---|
| `iso(value)` (`:22`) | `value.isoformat()` or `None`. |
| `enum(value)` (`:26`) | `value.value` when the value has a `.value`, else the value unchanged. |
| `file_url(key)` (`:30`) | `None` when the key is empty, else `f"/api/v1/files/{urllib.parse.quote(key)}"` (`/` kept unescaped). |
| `MANUAL_URL_PREFIX` (`:55`) | The constant `"https://manual.hireflow.invalid/"`. |
| `is_self_applied(app)` (`:102`) | `True` when any history row has `new_status == applied` and `changed_by == "user"`. |

#### `user_out(user)` (`:36`)
Not used by the routers in this part; listed for completeness. Fields:
- `id`: str
- `email`
- `full_name`
- `phone`
- `location`
- `linkedin_url`
- `has_password`: bool (`hashed_password` is set)
- `google_connected`: bool
- `google_email`
- `linkedin_connected`: bool (`linkedin_session_cookie` is set)
- `linkedin_session_valid`
- `preferences`: `user.prefs`, the stored preferences merged with defaults
- `last_scan_at`: ISO
- `created_at`: ISO

#### `job_out(job, application=None, prefs=None)` (`:58`)
| Field | Type / source |
|---|---|
| `id` | str |
| `company_name` | str |
| `company_logo_url` | str\|null |
| `role_title` | str |
| `location` | str\|null |
| `is_remote` | bool |
| `job_type` | `full-time \| part-time \| internship \| contract \| freelance \| null` |
| `experience_level` | `entry \| mid \| senior \| lead \| executive \| internship \| null` |
| `salary_min`, `salary_max` | int\|null |
| `salary_currency` | str\|null |
| `source_url` | str\|null. **null** when it starts with `MANUAL_URL_PREFIX`. |
| `source_platform` | ATSPlatform value (`linkedin, indeed, glassdoor, wellfound, greenhouse, lever, workday, ashby, bamboohr, icims, taleo, smartrecruiters, jobvite, custom, unknown`) |
| `application_url` | str\|null |
| `easy_apply` | bool |
| `extracted_skills` | list[str] (`[]` when null) |
| `posted_date`, `deadline_date` | ISO date\|null |
| `discovered_at` | ISO datetime |
| `is_active` | bool |
| `company` | `company_verifier.summary(job, prefs)`, see below |
| `year_fit` | `"Open to {1st\|2nd\|3rd\|<N>th}-year students"` when the user wants internships only, has a student year, and the posting names that year; else null |
| `application` | **Only when `application` is passed:** `{id, status, match_score, match_reasoning, similarity_score}` |

`company` has the shape `{verdict, score, reasons, method, tier, tier_label}`:
- `verdict` is `verified | unverified | suspicious | null`. It becomes `verified` when the normalized company name is in `prefs.trusted_companies`; in that case `"You marked this company legit"` is prepended to `reasons`.
- `score` is `company_check.score`.
- `reasons` holds at most 6 entries.
- `method` is `rules | ai`.
- `tier` is `job.company_tier`, or the catalog tier: `big_tech | product | startup_india | startup_global | ai`.
- `tier_label` is `Big Tech`, `Product companies`, `Indian startups`, `Global startups` or `AI companies`, or null.

#### `job_detail_out(job, application=None, prefs=None)` (`:95`)
`job_out(...)` plus `description`, `requirements` and `nice_to_haves`. When `prefs` is None and the application has a user, it uses `application.user.prefs`.

#### `application_summary(app, self_applied=None)` (`:107`)
| Field | Type |
|---|---|
| `self_applied` | bool. The passed value, else `is_self_applied(app)`. |
| `id` | str |
| `status` | ApplicationStatus value |
| `match_score` | int\|null |
| `match_reasoning` | str\|null |
| `ats_platform` | ATSPlatform value\|null |
| `needs_manual_review` | bool |
| `manual_review_reason` | str\|null |
| `created_at`, `updated_at`, `submitted_at` | ISO\|null |
| `job` | `job_out(job, prefs=app.user.prefs)`, or null |

#### `history_out(h)` (`:125`)
`{id: str, old_status: status|null, new_status: status, changed_by: "agent"|"user"|"system"|"email_parser", notes: str|null, created_at: ISO}`

#### `resume_out(resume, include_content=True)` (`:130`)
| Field | Type |
|---|---|
| `id` | str |
| `label` | str\|null |
| `original_filename` | str\|null |
| `is_master` | bool |
| `version` | int |
| `parent_resume_id` | str\|null |
| `tailored_for_job_id` | str\|null |
| `changes_made` | list[str] (`[]` when null) |
| `pdf_url` | `file_url(resume.pdf_url)` |
| `original_file_url` | `file_url(resume.original_file_url)` |
| `created_at`, `updated_at` | ISO |
| `parsed_content` | dict. **Only when `include_content=True`.** |

#### `application_detail(app, communications, interviews)` (`:150`)
`application_summary(app)` with `job` replaced, plus these fields:

| Field | Type |
|---|---|
| `job` | `job_detail_out(app.job, prefs=app.user.prefs)` (replaces the summary's `job`) |
| `match_details` | dict\|null, which may hold `strong_matches`, `missing_skills`, `heads_up`, `skills_match`, `experience_match`, `industry_match`, `location_match`, `compensation_match`, `proceed_with_application`, `reasoning`, `bot_apply_requested_at`, … |
| `similarity_score` | float\|null |
| `cover_letter` | str\|null |
| `custom_answers` | list (`[]` when null) |
| `field_overrides` | dict (`{}` when null) |
| `form_fields` | list (`[]` when null) |
| `tailored_resume` | `resume_out(app.tailored_resume)` with content, or null |
| `tailored_resume_pdf_url` | `file_url(...)` |
| `form_screenshot_url` | `file_url(...)` |
| `confirmation_screenshot_url` | `file_url(...)` |
| `confirmation_number` | str\|null |
| `staged_at`, `approved_at` | ISO\|null |
| `rejection_reason` | str\|null |
| `offer_details` | dict\|null |
| `error_log` | str\|null |
| `retry_count` | int |
| `notes` | str\|null |
| `history` | `[history_out(h)]`, ascending by `created_at` |
| `communications` | `[communication_out(c, brief=True)]` |
| `interviews` | `[interview_out(i, brief=True)]` |

#### `communication_out(c, brief=False)` (`:181`)
Always present:
- `id`: str
- `application_id`: str|null
- `direction`: `inbound | outbound`
- `sender_email`
- `sender_name`
- `subject`
- `detected_intent`: `acknowledgment | rejection | interview_invite | assessment | offer | follow_up | info_request | generic | unknown | null`
- `intent_confidence`: float|null
- `urgency`: str|null
- `is_action_required`: bool
- `action_taken`: bool
- `received_at`: ISO|null
- `snippet`: the first 220 characters of `body_text`, or `""`

Only when `brief=False`:
- `body_text`
- `extracted_details`: dict|null
- `suggested_reply`
- `gmail_thread_id`
- `gmail_draft_id`
- `attachments`: list (`[]` when null)

#### `interview_out(i, brief=False)` (`:209`)
Always present:
- `id`
- `application_id`
- `company_name`, `role_title`: from `application.job`, or null
- `interview_type`: InterviewType value|null
- `scheduled_at`: ISO
- `duration_minutes`: int
- `timezone`: str
- `meeting_link`
- `meeting_platform`
- `physical_location`
- `interviewer_names`: list (`[]` when null)
- `outcome`
- `google_event_id`
- `google_event_link`

Only when `brief=False`:
- `prep_notes`
- `company_research`
- `likely_questions`: list (`[]` when null), items `{question, answer_outline}`
- `feedback`

#### `run_out(run, include_log=False)` (`:234`)
- `id`: str
- `run_type`: `scan | apply | email_check | linkedin_sync | prepare`
- `status`: `running | completed | failed | cancelled`
- `trigger`: `user | schedule | system`
- `jobs_discovered`, `jobs_matched`, `applications_prepared`, `applications_submitted`, `errors_count`: int
- `started_at`: ISO
- `completed_at`: ISO|null
- `duration_seconds`: int|null
- `progress`: dict|null, the live scan progress
- `log`: list of `{ts, level, message, …}` (`[]` when null). **Only when `include_log=True`.**

#### `notification_out(n)` (`:255`)
`{id: str, event_type: str, title: str, body: str|null, link: str|null, data: dict ({} when null), is_read: bool, created_at: ISO}`

Known `event_type` values (`services/notifier.py:24`): `application_ready, application_submitted, application_failed, recruiter_email, interview_scheduled, interview_reminder_24h, interview_reminder_1h, session_expired, agent_error, weekly_summary, offer_received, scan_completed, linkedin_profile_changed, status_changed, self_applied, progress_digest`.

---

## Section 2: Complete Database Schema Registry

Source of truth: `backend/app/models/*.py` (SQLAlchemy 2.x declarative, `Mapped[...]` + `mapped_column`), cross-checked against `backend/alembic/versions/0001`–`0006` and against the DDL that SQLAlchemy compiles from the model metadata for PostgreSQL. All names below are HireFlow names; there is no product branding anywhere in table, column, index, constraint or enum names, so the schema is byte-identical to the source.

### 2.0 Overview and conventions

| Item | Value |
|---|---|
| Primary target | PostgreSQL 16 with the `vector` (pgvector) and `pg_trgm` extensions (image `pgvector/pgvector:pg16`) |
| Local / test target | SQLite (`sqlite:///…/backend/data/hireflow.db` in local mode, created with `create_all()`, never through Alembic) |
| Declarative base | `app.core.database.Base(DeclarativeBase)` with `type_annotation_map = {}`, so SQLAlchemy's default annotation map applies |
| Model registry | `app/models/__init__.py` imports and re-exports `AgentRun, Application, ApplicationStatusHistory, Communication, Interview, Job, Resume, Notification, User, UserFieldMapping` and the enums `ApplicationStatus, ATSPlatform, EmailDirection, EmailIntent, ExperienceLevel, InterviewType, JobType` (`__all__` holds these 17 names, sorted) |
| Tables | **10**: `users`, `user_field_mappings`, `notifications`, `jobs`, `resumes`, `applications`, `application_status_history`, `communications`, `interviews`, `agent_runs` |
| Columns | **199** in total (see per-table counts below) |
| Primary keys | Every table: `id` `Uuid` (PG `UUID`, SQLite `CHAR(32)`), Python-side `default=uuid.uuid4`, no server default |
| Timestamps | Every datetime column is `UTCDateTime` (PG `TIMESTAMP WITH TIME ZONE`, SQLite `DATETIME`). `created_at`, `started_at`, `discovered_at` and `last_checked` default to `utcnow()`. `updated_at` uses `default=utcnow, onupdate=utcnow` |
| JSON | `JSONType` = `JSON().with_variant(JSONB(), "postgresql")` (PG `JSONB`, SQLite `JSON`) |
| Nullability | Inferred from the annotation: `Mapped[X]` gives NOT NULL and `Mapped[X \| None]` gives NULL, unless `nullable=` is given explicitly |
| Server defaults | Only **two** columns have a DB-side default: `users.internshala_session_valid` and `applications.auto_submit` (`server_default=sqlalchemy.false()`, so PG DDL `DEFAULT false`, SQLite `DEFAULT 0`). Every other default is Python-side (`default=`) and does not appear in DDL |
| CHECK constraints | **None**, in models and migrations alike. Enums are native PG ENUM types; on SQLite they are non-native `VARCHAR(n)` with no CHECK (`create_constraint` is left at its default of False) |
| Naming convention | None configured on `MetaData`. ORM `index=True` indexes get Alembic/SQLAlchemy's default name `ix_<table>_<column>`. PostgreSQL auto-names the unnamed PK/UNIQUE/FK constraints as `<table>_pkey`, `<table>_<col>_key` and `<table>_<col>_fkey` |
| Extensions | `CREATE EXTENSION IF NOT EXISTS vector` and `CREATE EXTENSION IF NOT EXISTS pg_trgm`, run by migration 0001 and by `create_all()` on PostgreSQL |

| # | Table | Model class (file) | Columns |
|---|---|---|---|
| 1 | `users` | `User` (`models/user.py`) | 30 |
| 2 | `user_field_mappings` | `UserFieldMapping` (`models/user.py`) | 5 |
| 3 | `notifications` | `Notification` (`models/user.py`) | 9 |
| 4 | `jobs` | `Job` (`models/job.py`) | 33 |
| 5 | `resumes` | `Resume` (`models/resume.py`) | 17 |
| 6 | `applications` | `Application` (`models/application.py`) | 35 |
| 7 | `application_status_history` | `ApplicationStatusHistory` (`models/application.py`) | 7 |
| 8 | `communications` | `Communication` (`models/communication.py`) | 24 |
| 9 | `interviews` | `Interview` (`models/interview.py`) | 24 |
| 10 | `agent_runs` | `AgentRun` (`models/agent_run.py`) | 15 |
| | **Total** | | **199** |

Column-table legend: **Null** = DB nullability. **Default** = Python-side `default=` (client-side, not in DDL). **Srv default** = `server_default`. **Mig** = the source migration that created the column.

---

### 2.1 `users` (30 columns)

| # | Column | SQLAlchemy type | PG DDL type | Null | Default | Srv default | Keys / index | Mig |
|---|---|---|---|---|---|---|---|---|
| 1 | `id` | `Uuid` | `UUID` | NOT NULL | `uuid.uuid4` | — | PK (`users_pkey`) | 0001 |
| 2 | `email` | `String(255)` | `VARCHAR(255)` | NOT NULL | — | — | `unique=True, index=True` gives **unique index `ix_users_email`** (no separate constraint) | 0001 |
| 3 | `full_name` | `String(255)` | `VARCHAR(255)` | NOT NULL | — | — | — | 0001 |
| 4 | `phone` | `String(50)` | `VARCHAR(50)` | NULL | — | — | — | 0001 |
| 5 | `linkedin_url` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 6 | `location` | `String(255)` | `VARCHAR(255)` | NULL | — | — | — | 0001 |
| 7 | `hashed_password` | `String(255)` | `VARCHAR(255)` | NULL | — | — | bcrypt hash; NULL for Google-only accounts | 0001 |
| 8 | `google_access_token` | `EncryptedText` | `TEXT` | NULL | — | — | AES-256-GCM `v1:` ciphertext | 0001 |
| 9 | `google_refresh_token` | `EncryptedText` | `TEXT` | NULL | — | — | AES-256-GCM `v1:` ciphertext | 0001 |
| 10 | `google_token_expiry` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NULL | — | — | — | 0001 |
| 11 | `google_scopes` | `JSONType` | `JSONB` | NULL | — | — | `list[str]` | 0001 |
| 12 | `google_email` | `String(255)` | `VARCHAR(255)` | NULL | — | — | — | 0001 |
| 13 | `gmail_history_id` | `String(64)` | `VARCHAR(64)` | NULL | — | — | — | 0001 |
| 14 | `gmail_watch_expiration` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NULL | — | — | — | 0001 |
| 15 | `gmail_last_polled_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NULL | — | — | — | 0001 |
| 16 | `linkedin_session_cookie` | `EncryptedText` | `TEXT` | NULL | — | — | encrypted `li_at` cookie | 0001 |
| 17 | `linkedin_cookie_updated_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NULL | — | — | — | 0001 |
| 18 | `linkedin_session_valid` | `Boolean` | `BOOLEAN` | NOT NULL | `False` | — | — | 0001 |
| 19 | `linkedin_profile_snapshot` | `JSONType` | `JSONB` | NULL | — | — | `dict` | 0001 |
| 20 | `internshala_session` | `EncryptedJSON` | `TEXT` | NULL | — | — | encrypted JSON list of cookie dicts | **0004** |
| 21 | `internshala_session_updated_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NULL | — | — | — | **0004** |
| 22 | `internshala_session_valid` | `Boolean` | `BOOLEAN` | NOT NULL | `False` | **`false()`**, DDL `DEFAULT false` | — | **0004** |
| 23 | `internshala_user_agent` | `String(512)` | `VARCHAR(512)` | NULL | — | — | — | **0005** |
| 24 | `ats_credentials` | `EncryptedJSON` | `TEXT` | NULL | — | — | encrypted JSON `dict[str,str]` | 0001 |
| 25 | `preferences` | `JSONType` | `JSONB` | NOT NULL (explicit) | `default_preferences` (callable, see 2.13) | — | — | 0001 |
| 26 | `consents` | `JSONType` | `JSONB` | NULL | `dict` (gives `{}`) | — | — | 0001 |
| 27 | `is_active` | `Boolean` | `BOOLEAN` | NOT NULL | `True` | — | — | 0001 |
| 28 | `last_scan_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NULL | — | — | — | 0001 |
| 29 | `created_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | `utcnow` | — | — | 0001 |
| 30 | `updated_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | `utcnow`, `onupdate=utcnow` | — | — | 0001 |

- Table constraints: PK(`id`). The email uniqueness is enforced by the unique index `ix_users_email`. Registration and login also compare emails case-insensitively in code (`func.lower(User.email) == email.lower()`), and emails are stored lowercased.
- Indexes: `ix_users_email` UNIQUE (`email`).
- Relationships (all `lazy="select"`, the default):
  - `resumes: list[Resume]`: `relationship(back_populates="user", cascade="all, delete-orphan")`
  - `applications: list[Application]`: `relationship(back_populates="user", cascade="all, delete-orphan")`
  - `field_mappings: list[UserFieldMapping]`: `relationship(back_populates="user", cascade="all, delete-orphan")`
  - There is **no** ORM relationship to `notifications`, `communications` or `agent_runs`. Those rows go away through the DB-level `ON DELETE CASCADE`. SQLite enforces it through `PRAGMA foreign_keys=ON`.
- Python properties (not columns): `first_name` (first space-separated token of `full_name`), `last_name` (the rest, or `""`), `prefs` (`merge_preferences(self.preferences, None)`), `google_connected` (`bool(google_refresh_token or google_access_token)`).

### 2.2 `user_field_mappings` (5 columns)

| # | Column | SQLAlchemy type | PG DDL type | Null | Default | Srv default | Keys / index | Mig |
|---|---|---|---|---|---|---|---|---|
| 1 | `id` | `Uuid` | `UUID` | NOT NULL | `uuid.uuid4` | — | PK | 0001 |
| 2 | `user_id` | `Uuid` | `UUID` | NOT NULL | — | — | FK → `users.id` **ON DELETE CASCADE**; index `ix_user_field_mappings_user_id` | 0001 |
| 3 | `field_name` | `String(255)` | `VARCHAR(255)` | NOT NULL | — | — | part of `uq_user_field_mapping` | 0001 |
| 4 | `field_value` | `Text` | `TEXT` | NOT NULL | — | — | — | 0001 |
| 5 | `field_type` | `String(50)` | `VARCHAR(50)` | NULL | — (the API schema defaults it to `"text"`) | — | — | 0001 |

- Table constraints: `UniqueConstraint("user_id", "field_name", name="uq_user_field_mapping")`.
- Indexes: `ix_user_field_mappings_user_id` (`user_id`).
- Relationships: `user: User`, `relationship(back_populates="field_mappings")`.

### 2.3 `notifications` (9 columns)

| # | Column | SQLAlchemy type | PG DDL type | Null | Default | Srv default | Keys / index | Mig |
|---|---|---|---|---|---|---|---|---|
| 1 | `id` | `Uuid` | `UUID` | NOT NULL | `uuid.uuid4` | — | PK | 0001 |
| 2 | `user_id` | `Uuid` | `UUID` | NOT NULL | — | — | FK → `users.id` **ON DELETE CASCADE**; index `ix_notifications_user_id` | 0001 |
| 3 | `event_type` | `String(64)` | `VARCHAR(64)` | NOT NULL | — | — | — | 0001 |
| 4 | `title` | `String(255)` | `VARCHAR(255)` | NOT NULL | — | — | — | 0001 |
| 5 | `body` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 6 | `link` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 7 | `data` | `JSONType` | `JSONB` | NULL | — | — | — | 0001 |
| 8 | `is_read` | `Boolean` | `BOOLEAN` | NOT NULL | `False` | — | — | 0001 |
| 9 | `created_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | `utcnow` | — | index `ix_notifications_created_at` | 0001 |

- Indexes: `ix_notifications_user_id` (`user_id`), `ix_notifications_created_at` (`created_at`).
- Relationships: none.

### 2.4 `jobs` (33 columns)

| # | Column | SQLAlchemy type | PG DDL type | Null | Default | Srv default | Keys / index | Mig |
|---|---|---|---|---|---|---|---|---|
| 1 | `id` | `Uuid` | `UUID` | NOT NULL | `uuid.uuid4` | — | PK | 0001 |
| 2 | `company_name` | `String(255)` | `VARCHAR(255)` | NOT NULL | — | — | index `idx_jobs_company` | 0001 |
| 3 | `company_logo_url` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 4 | `company_domain` | `String(255)` | `VARCHAR(255)` | NULL | — | — | — | 0001 |
| 5 | `role_title` | `String(255)` | `VARCHAR(255)` | NOT NULL | — | — | GIN trigram index `idx_jobs_title_trgm` (raw SQL, migration only) | 0001 |
| 6 | `description` | `Text` | `TEXT` | NOT NULL | — | — | — | 0001 |
| 7 | `requirements` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 8 | `nice_to_haves` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 9 | `job_type` | `JOB_TYPE_ENUM` (`Enum(JobType, name="job_type")`) | `job_type` | NULL | — | — | — | 0001 |
| 10 | `experience_level` | `EXPERIENCE_LEVEL_ENUM` | `experience_level` | NULL | — | — | — | 0001 |
| 11 | `location` | `String(255)` | `VARCHAR(255)` | NULL | — | — | — | 0001 |
| 12 | `is_remote` | `Boolean` | `BOOLEAN` | NOT NULL | `False` | — | — | 0001 |
| 13 | `salary_min` | `Integer` | `INTEGER` | NULL | — | — | — | 0001 |
| 14 | `salary_max` | `Integer` | `INTEGER` | NULL | — | — | — | 0001 |
| 15 | `salary_currency` | `String(10)` | `VARCHAR(10)` | NULL | `"USD"` | — | — | 0001 |
| 16 | `source_url` | `Text` | `TEXT` | NOT NULL | — | — | **UNIQUE** (column `unique=True`, gives the unnamed constraint PG names `jobs_source_url_key`) | 0001 |
| 17 | `source_platform` | `ATS_PLATFORM_ENUM` | `ats_platform` | NOT NULL | — | — | index `idx_jobs_platform` | 0001 |
| 18 | `application_url` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 19 | `external_id` | `String(255)` | `VARCHAR(255)` | NULL | — | — | — | 0001 |
| 20 | `easy_apply` | `Boolean` | `BOOLEAN` | NOT NULL | `False` | — | — | 0001 |
| 21 | `dedupe_key` | `String(512)` | `VARCHAR(512)` | NULL | — | — | index `idx_jobs_dedupe` | 0001 |
| 22 | `description_embedding` | `EmbeddingType(1536)` | `VECTOR(1536)` (SQLite `TEXT`) | NULL | — | — | IVFFlat index `idx_jobs_embedding` (raw SQL, migration only) | 0001 |
| 23 | `extracted_skills` | `JSONType` | `JSONB` | NULL | — | — | `list[str]` | 0001 |
| 24 | `extracted_requirements` | `JSONType` | `JSONB` | NULL | — | — | `dict` | 0001 |
| 25 | `raw_data` | `JSONType` | `JSONB` | NULL | — | — | `dict` | 0001 |
| 26 | `company_verdict` | `String(16)` | `VARCHAR(16)` | NULL | — | — | index `idx_jobs_company_verdict`; values `verified` / `unverified` / `suspicious` | **0006** |
| 27 | `company_tier` | `String(32)` | `VARCHAR(32)` | NULL | — | — | index `idx_jobs_company_tier`; values `big_tech` / `product` / `startup_india` / `startup_global` / `ai` | **0006** |
| 28 | `company_check` | `JSONType` | `JSONB` | NULL | — | — | reasons `dict` | **0006** |
| 29 | `posted_date` | `Date` | `DATE` | NULL | — | — | — | 0001 |
| 30 | `deadline_date` | `Date` | `DATE` | NULL | — | — | — | 0001 |
| 31 | `is_active` | `Boolean` | `BOOLEAN` | NOT NULL | `True` | — | `index=True` gives `ix_jobs_is_active`, plus partial index `idx_jobs_active` (raw SQL) | 0001 |
| 32 | `discovered_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | `utcnow` | — | — | 0001 |
| 33 | `last_checked` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | `utcnow` | — | — | 0001 |

- Table constraints: PK(`id`), UNIQUE(`source_url`).
- `__table_args__` indexes: `Index("idx_jobs_company", "company_name")`, `Index("idx_jobs_platform", "source_platform")`, `Index("idx_jobs_dedupe", "dedupe_key")`, `Index("idx_jobs_company_tier", "company_tier")`, `Index("idx_jobs_company_verdict", "company_verdict")`.
- Column index: `ix_jobs_is_active` (`is_active`).
- Indexes created only by raw SQL in migration 0001 (not modelled; excluded from autogenerate by `env.py`):
  - `idx_jobs_embedding`: `CREATE INDEX IF NOT EXISTS idx_jobs_embedding ON jobs USING ivfflat (description_embedding vector_cosine_ops) WITH (lists = 100)`
  - `idx_jobs_active`: `CREATE INDEX IF NOT EXISTS idx_jobs_active ON jobs (is_active) WHERE is_active = true` (partial)
  - `idx_jobs_title_trgm`: `CREATE INDEX IF NOT EXISTS idx_jobs_title_trgm ON jobs USING gin (role_title gin_trgm_ops)`
- Relationships: none are declared on `Job`. `Application.job` and the FK `resumes.tailored_for_job_id` point at it one way only.
- Data convention: an application logged by hand without a link gets a synthetic `source_url` starting with `https://manual.hireflow.invalid/` (source: `https://manual.autoapply.invalid/`, `MANUAL_URL_PREFIX` in `api/serializers.py`). Internshala postings are stored with `source_platform = 'custom'`, because the `ats_platform` enum has no `internshala` value.

### 2.5 `resumes` (17 columns)

| # | Column | SQLAlchemy type | PG DDL type | Null | Default | Srv default | Keys / index | Mig |
|---|---|---|---|---|---|---|---|---|
| 1 | `id` | `Uuid` | `UUID` | NOT NULL | `uuid.uuid4` | — | PK | 0001 |
| 2 | `user_id` | `Uuid` | `UUID` | NOT NULL | — | — | FK → `users.id` **ON DELETE CASCADE**; index `ix_resumes_user_id` | 0001 |
| 3 | `label` | `String(255)` | `VARCHAR(255)` | NULL | — | — | — | 0001 |
| 4 | `original_file_url` | `Text` | `TEXT` | NULL | — | — | storage key of the uploaded file | 0001 |
| 5 | `original_filename` | `String(255)` | `VARCHAR(255)` | NULL | — | — | — | 0001 |
| 6 | `raw_text` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 7 | `parsed_content` | `JSONType` | `JSONB` | NOT NULL (explicit) | — | — | structured resume (personal_info, summary, education, experience, projects, skills{technical,languages,tools,soft_skills}, certifications, awards) | 0001 |
| 8 | `skills_embedding` | `EmbeddingType(1536)` | `VECTOR(1536)` | NULL | — | — | — | 0001 |
| 9 | `is_master` | `Boolean` | `BOOLEAN` | NOT NULL | `False` | — | — | 0001 |
| 10 | `is_active` | `Boolean` | `BOOLEAN` | NOT NULL | `True` | — | — | 0001 |
| 11 | `version` | `Integer` | `INTEGER` | NOT NULL | `1` | — | — | 0001 |
| 12 | `parent_resume_id` | `Uuid` | `UUID` | NULL | — | — | FK → `resumes.id` **ON DELETE SET NULL** (self-reference) | 0001 |
| 13 | `tailored_for_job_id` | `Uuid` | `UUID` | NULL | — | — | FK → `jobs.id` **ON DELETE SET NULL** | 0001 |
| 14 | `changes_made` | `JSONType` | `JSONB` | NULL | — | — | `list[str]` | 0001 |
| 15 | `pdf_url` | `Text` | `TEXT` | NULL | — | — | storage key of the rendered PDF | 0001 |
| 16 | `created_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | `utcnow` | — | — | 0001 |
| 17 | `updated_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | `utcnow`, `onupdate=utcnow` | — | — | 0001 |

- Indexes: `ix_resumes_user_id` (`user_id`). There are no indexes on `parent_resume_id` or `tailored_for_job_id`.
- Relationships: `user: User`, `relationship(back_populates="resumes")`. No relationship is declared for `parent_resume_id` or `tailored_for_job_id`.

### 2.6 `applications` (35 columns)

| # | Column | SQLAlchemy type | PG DDL type | Null | Default | Srv default | Keys / index | Mig |
|---|---|---|---|---|---|---|---|---|
| 1 | `id` | `Uuid` | `UUID` | NOT NULL | `uuid.uuid4` | — | PK | 0001 |
| 2 | `user_id` | `Uuid` | `UUID` | NOT NULL | — | — | FK → `users.id` **ON DELETE CASCADE**; index `ix_applications_user_id`; part of `uq_application_user_job` and `idx_applications_user_status` | 0001 |
| 3 | `job_id` | `Uuid` | `UUID` | NOT NULL | — | — | FK → `jobs.id` (**no ondelete**, so `NO ACTION`); index `ix_applications_job_id`; part of `uq_application_user_job` | 0001 |
| 4 | `status` | `APPLICATION_STATUS_ENUM` | `application_status` | NOT NULL (non-Optional annotation) | `ApplicationStatus.DISCOVERED` | — | index `ix_applications_status`; part of `idx_applications_user_status` | 0001 |
| 5 | `match_score` | `Integer` | `INTEGER` | NULL | — | — | — | 0001 |
| 6 | `match_reasoning` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 7 | `match_details` | `JSONType` | `JSONB` | NULL | — | — | — | 0001 |
| 8 | `similarity_score` | *(no explicit type; `Mapped[float \| None]`)*: resolves to `Double` on SQLAlchemy 2.1.x, `Float` on 2.0.x | `DOUBLE PRECISION` (migration: `sa.Double()`) | NULL | — | — | — | 0001 |
| 9 | `review_decision` | `String(16)` | `VARCHAR(16)` | NULL | — | — | values `keep` / `skip` | **0002** |
| 10 | `reviewed_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NULL | — | — | — | **0002** |
| 11 | `auto_submit` | `Boolean` | `BOOLEAN` | NOT NULL | `False` | **`false()`**, DDL `DEFAULT false` | — | **0002** |
| 12 | `tailored_resume_id` | `Uuid` | `UUID` | NULL | — | — | FK → `resumes.id` **ON DELETE SET NULL** | 0001 |
| 13 | `tailored_resume_pdf_url` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 14 | `cover_letter` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 15 | `custom_answers` | `JSONType` | `JSONB` | NULL | — | — | `[{question, field_type, answer, confidence, needs_user_review}]` | 0001 |
| 16 | `field_overrides` | `JSONType` | `JSONB` | NULL | — | — | review-queue corrections `{field key → value}` | **0004** |
| 17 | `ats_platform` | `ATS_PLATFORM_ENUM` | `ats_platform` | NULL | — | — | — | 0001 |
| 18 | `form_fields` | `JSONType` | `JSONB` | NULL | — | — | `list[dict]` | 0001 |
| 19 | `needs_manual_review` | `Boolean` | `BOOLEAN` | NOT NULL | `False` | — | — | 0001 |
| 20 | `manual_review_reason` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 21 | `form_screenshot_url` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 22 | `staged_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NULL | — | — | — | 0001 |
| 23 | `approved_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NULL | — | — | — | 0001 |
| 24 | `submitted_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NULL | — | — | — | 0001 |
| 25 | `confirmation_screenshot_url` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 26 | `confirmation_number` | `String(255)` | `VARCHAR(255)` | NULL | — | — | — | 0001 |
| 27 | `first_response_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NULL | — | — | — | 0001 |
| 28 | `rejection_reason` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 29 | `rejected_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NULL | — | — | — | 0001 |
| 30 | `offer_details` | `JSONType` | `JSONB` | NULL | — | — | — | 0001 |
| 31 | `error_log` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 32 | `retry_count` | `Integer` | `INTEGER` | NOT NULL | `0` | — | — | 0001 |
| 33 | `notes` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 34 | `created_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | `utcnow` | — | — | 0001 |
| 35 | `updated_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | `utcnow`, `onupdate=utcnow` | — | — | 0001 |

- Table constraints: PK(`id`), `UniqueConstraint("user_id", "job_id", name="uq_application_user_job")`.
- Indexes: `idx_applications_user_status` (`user_id`, `status`) (from `__table_args__`), `ix_applications_user_id`, `ix_applications_job_id`, `ix_applications_status`.
- Relationships:
  - `user: User`: `relationship(back_populates="applications")`
  - `job: Job`: `relationship(lazy="joined")` (one-way, always eager-joined)
  - `tailored_resume: Resume | None`: `relationship(foreign_keys=[tailored_resume_id])` (one-way, lazy select)
  - `history: list[ApplicationStatusHistory]`: `relationship(back_populates="application", cascade="all, delete-orphan", order_by="ApplicationStatusHistory.created_at")`

### 2.7 `application_status_history` (7 columns)

| # | Column | SQLAlchemy type | PG DDL type | Null | Default | Srv default | Keys / index | Mig |
|---|---|---|---|---|---|---|---|---|
| 1 | `id` | `Uuid` | `UUID` | NOT NULL | `uuid.uuid4` | — | PK | 0001 |
| 2 | `application_id` | `Uuid` | `UUID` | NOT NULL | — | — | FK → `applications.id` **ON DELETE CASCADE**; index `ix_application_status_history_application_id` | 0001 |
| 3 | `old_status` | `APPLICATION_STATUS_ENUM` | `application_status` | NULL | — | — | — | 0001 |
| 4 | `new_status` | `APPLICATION_STATUS_ENUM` | `application_status` | NOT NULL | — | — | — | 0001 |
| 5 | `changed_by` | `String(50)` | `VARCHAR(50)` | NOT NULL | `"agent"` | — | values `agent` / `user` / `system` / `email_parser` | 0001 |
| 6 | `notes` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 7 | `created_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | `utcnow` | — | — | 0001 |

- Indexes: `ix_application_status_history_application_id`.
- Relationships: `application: Application`, `relationship(back_populates="history")`.

### 2.8 `communications` (24 columns)

| # | Column | SQLAlchemy type | PG DDL type | Null | Default | Srv default | Keys / index | Mig |
|---|---|---|---|---|---|---|---|---|
| 1 | `id` | `Uuid` | `UUID` | NOT NULL | `uuid.uuid4` | — | PK | 0001 |
| 2 | `user_id` | `Uuid` | `UUID` | NOT NULL | — | — | FK → `users.id` **ON DELETE CASCADE**; index `ix_communications_user_id` | 0001 |
| 3 | `application_id` | `Uuid` | `UUID` | NULL | — | — | FK → `applications.id` **ON DELETE SET NULL**; index `ix_communications_application_id` | 0001 |
| 4 | `gmail_message_id` | `String(255)` | `VARCHAR(255)` | NULL | — | — | **UNIQUE** (unnamed; PG name `communications_gmail_message_id_key`) | 0001 |
| 5 | `gmail_thread_id` | `String(255)` | `VARCHAR(255)` | NULL | — | — | index `ix_communications_gmail_thread_id` | 0001 |
| 6 | `gmail_label_ids` | `JSONType` | `JSONB` | NULL | — | — | `list[str]` | 0001 |
| 7 | `direction` | `EMAIL_DIRECTION_ENUM` | `email_direction` | NOT NULL | — | — | — | 0001 |
| 8 | `sender_email` | `String(255)` | `VARCHAR(255)` | NULL | — | — | — | 0001 |
| 9 | `sender_name` | `String(255)` | `VARCHAR(255)` | NULL | — | — | — | 0001 |
| 10 | `recipient_email` | `String(255)` | `VARCHAR(255)` | NULL | — | — | — | 0001 |
| 11 | `subject` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 12 | `body_text` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 13 | `body_html` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 14 | `attachments` | `JSONType` | `JSONB` | NULL | — | — | `list[dict]` | 0001 |
| 15 | `detected_intent` | `EMAIL_INTENT_ENUM` | `email_intent` | NULL | — | — | — | 0001 |
| 16 | `intent_confidence` | `Float` (explicit) | `FLOAT` | NULL | — | — | — | 0001 |
| 17 | `urgency` | `String(16)` | `VARCHAR(16)` | NULL | — | — | — | 0001 |
| 18 | `extracted_details` | `JSONType` | `JSONB` | NULL | — | — | — | 0001 |
| 19 | `suggested_reply` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 20 | `gmail_draft_id` | `String(255)` | `VARCHAR(255)` | NULL | — | — | — | 0001 |
| 21 | `is_action_required` | `Boolean` | `BOOLEAN` | NOT NULL | `False` | — | index `idx_comms_action`, plus partial index `idx_comms_action_required` (raw SQL) | 0001 |
| 22 | `action_taken` | `Boolean` | `BOOLEAN` | NOT NULL | `False` | — | — | 0001 |
| 23 | `received_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NULL | — | — | — | 0001 |
| 24 | `created_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | `utcnow` | — | — | 0001 |

- Table constraints: PK(`id`), UNIQUE(`gmail_message_id`).
- Indexes: `idx_comms_action` (`is_action_required`) (from `__table_args__`), `ix_communications_user_id`, `ix_communications_application_id`, `ix_communications_gmail_thread_id`. Raw SQL in migration only: `CREATE INDEX IF NOT EXISTS idx_comms_action_required ON communications (is_action_required) WHERE is_action_required = true`.
- Relationships: none.

### 2.9 `interviews` (24 columns)

| # | Column | SQLAlchemy type | PG DDL type | Null | Default | Srv default | Keys / index | Mig |
|---|---|---|---|---|---|---|---|---|
| 1 | `id` | `Uuid` | `UUID` | NOT NULL | `uuid.uuid4` | — | PK | 0001 |
| 2 | `application_id` | `Uuid` | `UUID` | NOT NULL | — | — | FK → `applications.id` **ON DELETE CASCADE**; index `ix_interviews_application_id` | 0001 |
| 3 | `communication_id` | `Uuid` | `UUID` | NULL | — | — | FK → `communications.id` **ON DELETE SET NULL** (no index) | 0001 |
| 4 | `google_event_id` | `String(255)` | `VARCHAR(255)` | NULL | — | — | **UNIQUE** (unnamed; PG name `interviews_google_event_id_key`) | 0001 |
| 5 | `google_event_link` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 6 | `interview_type` | `INTERVIEW_TYPE_ENUM` | `interview_type` | NULL | — | — | — | 0001 |
| 7 | `scheduled_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NOT NULL (explicit) | — | — | index `ix_interviews_scheduled_at` | 0001 |
| 8 | `duration_minutes` | `Integer` | `INTEGER` | NOT NULL | `60` | — | — | 0001 |
| 9 | `timezone` | `String(50)` | `VARCHAR(50)` | NOT NULL | `"UTC"` | — | — | 0001 |
| 10 | `meeting_link` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 11 | `meeting_platform` | `String(50)` | `VARCHAR(50)` | NULL | — | — | values `zoom` / `google_meet` / `teams` / `onsite` / `phone` | 0001 |
| 12 | `physical_location` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 13 | `interviewer_names` | `JSONType` | `JSONB` | NULL | — | — | `list[str]` | 0001 |
| 14 | `interviewer_titles` | `JSONType` | `JSONB` | NULL | — | — | `list[str]` | 0001 |
| 15 | `interviewer_linkedin_urls` | `JSONType` | `JSONB` | NULL | — | — | `list[str]` | 0001 |
| 16 | `prep_notes` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 17 | `company_research` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 18 | `likely_questions` | `JSONType` | `JSONB` | NULL | — | — | `list` | 0001 |
| 19 | `outcome` | `String(50)` | `VARCHAR(50)` | NULL | — | — | values `passed` / `failed` / `pending` / `rescheduled` / `cancelled` | 0001 |
| 20 | `feedback` | `Text` | `TEXT` | NULL | — | — | — | 0001 |
| 21 | `reminder_24h_sent` | `Boolean` | `BOOLEAN` | NOT NULL | `False` | — | — | 0001 |
| 22 | `reminder_1h_sent` | `Boolean` | `BOOLEAN` | NOT NULL | `False` | — | — | 0001 |
| 23 | `created_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | `utcnow` | — | — | 0001 |
| 24 | `updated_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | `utcnow`, `onupdate=utcnow` | — | — | 0001 |

- Table constraints: PK(`id`), UNIQUE(`google_event_id`).
- Indexes: `ix_interviews_application_id`, `ix_interviews_scheduled_at`.
- Relationships: `application: Application`, `relationship(lazy="joined")` (one-way).

### 2.10 `agent_runs` (15 columns)

| # | Column | SQLAlchemy type | PG DDL type | Null | Default | Srv default | Keys / index | Mig |
|---|---|---|---|---|---|---|---|---|
| 1 | `id` | `Uuid` | `UUID` | NOT NULL | `uuid.uuid4` | — | PK | 0001 |
| 2 | `user_id` | `Uuid` | `UUID` | NOT NULL | — | — | FK → `users.id` **ON DELETE CASCADE**; index `ix_agent_runs_user_id` | 0001 |
| 3 | `run_type` | `String(50)` | `VARCHAR(50)` | NOT NULL | — | — | values `scan` / `apply` / `email_check` / `linkedin_sync` / `prepare` | 0001 |
| 4 | `status` | `String(20)` | `VARCHAR(20)` | NOT NULL | `"running"` | — | values `running` / `completed` / `failed` / `cancelled` | 0001 |
| 5 | `trigger` | `String(20)` | `VARCHAR(20)` | NULL | `"user"` | — | values `user` / `schedule` / `system` | 0001 |
| 6 | `jobs_discovered` | `Integer` | `INTEGER` | NOT NULL | `0` | — | — | 0001 |
| 7 | `jobs_matched` | `Integer` | `INTEGER` | NOT NULL | `0` | — | — | 0001 |
| 8 | `applications_prepared` | `Integer` | `INTEGER` | NOT NULL | `0` | — | — | 0001 |
| 9 | `applications_submitted` | `Integer` | `INTEGER` | NOT NULL | `0` | — | — | 0001 |
| 10 | `errors_count` | `Integer` | `INTEGER` | NOT NULL | `0` | — | — | 0001 |
| 11 | `started_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NOT NULL | `utcnow` | — | — | 0001 |
| 12 | `completed_at` | `UTCDateTime` | `TIMESTAMP WITH TIME ZONE` | NULL | — | — | — | 0001 |
| 13 | `duration_seconds` | `Integer` | `INTEGER` | NULL | — | — | — | 0001 |
| 14 | `log` | `JSONType` | `JSONB` | NULL | `list` (gives `[]`) | — | `list[dict]` | 0001 |
| 15 | `progress` | `JSONType` | `JSONB` | NULL | — | — | live scan progress (phase, percent, per-source status) | **0003** |

- Indexes: `ix_agent_runs_user_id`.
- Relationships: none.

### 2.11 Registries: foreign keys, unique constraints, indexes

**Foreign keys (14)**. No FK has an `onupdate` action. PG names them `<table>_<column>_fkey`.

| # | Column | References | ON DELETE |
|---|---|---|---|
| 1 | `user_field_mappings.user_id` | `users.id` | CASCADE |
| 2 | `notifications.user_id` | `users.id` | CASCADE |
| 3 | `resumes.user_id` | `users.id` | CASCADE |
| 4 | `resumes.parent_resume_id` | `resumes.id` | SET NULL |
| 5 | `resumes.tailored_for_job_id` | `jobs.id` | SET NULL |
| 6 | `applications.user_id` | `users.id` | CASCADE |
| 7 | `applications.job_id` | `jobs.id` | *(none, i.e. NO ACTION)* |
| 8 | `applications.tailored_resume_id` | `resumes.id` | SET NULL |
| 9 | `application_status_history.application_id` | `applications.id` | CASCADE |
| 10 | `communications.user_id` | `users.id` | CASCADE |
| 11 | `communications.application_id` | `applications.id` | SET NULL |
| 12 | `interviews.application_id` | `applications.id` | CASCADE |
| 13 | `interviews.communication_id` | `communications.id` | SET NULL |
| 14 | `agent_runs.user_id` | `users.id` | CASCADE |

**Uniqueness (6)**

| Table | Columns | How it is declared | Name |
|---|---|---|---|
| `users` | `email` | `unique=True, index=True` gives a unique index | `ix_users_email` |
| `jobs` | `source_url` | column `unique=True` gives a UNIQUE constraint | unnamed (PG: `jobs_source_url_key`) |
| `user_field_mappings` | `user_id, field_name` | `UniqueConstraint` | `uq_user_field_mapping` |
| `applications` | `user_id, job_id` | `UniqueConstraint` | `uq_application_user_job` |
| `communications` | `gmail_message_id` | column `unique=True` | unnamed (PG: `communications_gmail_message_id_key`) |
| `interviews` | `google_event_id` | column `unique=True` | unnamed (PG: `interviews_google_event_id_key`) |

**Explicit indexes (27 = 23 ORM-modelled + 4 raw SQL)**. This excludes the implicit PK and UNIQUE-constraint indexes.

| # | Name | Table | Columns / expression | Kind | Origin |
|---|---|---|---|---|---|
| 1 | `idx_jobs_company` | jobs | `company_name` | btree | `__table_args__`, migration 0001 |
| 2 | `idx_jobs_platform` | jobs | `source_platform` | btree | `__table_args__`, 0001 |
| 3 | `idx_jobs_dedupe` | jobs | `dedupe_key` | btree | `__table_args__`, 0001 |
| 4 | `ix_jobs_is_active` | jobs | `is_active` | btree | `index=True`, 0001 |
| 5 | `idx_jobs_company_tier` | jobs | `company_tier` | btree | `__table_args__`, **0006** |
| 6 | `idx_jobs_company_verdict` | jobs | `company_verdict` | btree | `__table_args__`, **0006** |
| 7 | `idx_jobs_embedding` | jobs | `description_embedding vector_cosine_ops` | **ivfflat**, `WITH (lists = 100)` | raw SQL, 0001 only |
| 8 | `idx_jobs_active` | jobs | `is_active WHERE is_active = true` | btree **partial** | raw SQL, 0001 only |
| 9 | `idx_jobs_title_trgm` | jobs | `role_title gin_trgm_ops` | **GIN trigram** | raw SQL, 0001 only |
| 10 | `ix_users_email` | users | `email` | btree **UNIQUE** | `unique=True, index=True`, 0001 |
| 11 | `ix_agent_runs_user_id` | agent_runs | `user_id` | btree | `index=True`, 0001 |
| 12 | `ix_notifications_user_id` | notifications | `user_id` | btree | `index=True`, 0001 |
| 13 | `ix_notifications_created_at` | notifications | `created_at` | btree | `index=True`, 0001 |
| 14 | `ix_resumes_user_id` | resumes | `user_id` | btree | `index=True`, 0001 |
| 15 | `ix_user_field_mappings_user_id` | user_field_mappings | `user_id` | btree | `index=True`, 0001 |
| 16 | `idx_applications_user_status` | applications | `user_id, status` | btree composite | `__table_args__`, 0001 |
| 17 | `ix_applications_user_id` | applications | `user_id` | btree | `index=True`, 0001 |
| 18 | `ix_applications_job_id` | applications | `job_id` | btree | `index=True`, 0001 |
| 19 | `ix_applications_status` | applications | `status` | btree | `index=True`, 0001 |
| 20 | `ix_application_status_history_application_id` | application_status_history | `application_id` | btree | `index=True`, 0001 |
| 21 | `idx_comms_action` | communications | `is_action_required` | btree | `__table_args__`, 0001 |
| 22 | `ix_communications_user_id` | communications | `user_id` | btree | `index=True`, 0001 |
| 23 | `ix_communications_application_id` | communications | `application_id` | btree | `index=True`, 0001 |
| 24 | `ix_communications_gmail_thread_id` | communications | `gmail_thread_id` | btree | `index=True`, 0001 |
| 25 | `idx_comms_action_required` | communications | `is_action_required WHERE is_action_required = true` | btree **partial** | raw SQL, 0001 only |
| 26 | `ix_interviews_application_id` | interviews | `application_id` | btree | `index=True`, 0001 |
| 27 | `ix_interviews_scheduled_at` | interviews | `scheduled_at` | btree | `index=True`, 0001 |

The four raw-SQL indexes are listed in `alembic/env.py` `MANUAL_INDEXES = {"idx_jobs_embedding", "idx_jobs_active", "idx_jobs_title_trgm", "idx_comms_action_required"}` and excluded from autogenerate comparison. `create_all()` never creates them, so they do not exist on SQLite or on a PostgreSQL database built with `create_all()`.

**Relationships summary (11 relationship attributes)**

| Owner.attr | Target | back_populates | cascade | lazy | Other |
|---|---|---|---|---|---|
| `User.resumes` | `Resume` (list) | `user` | `all, delete-orphan` | select | — |
| `User.applications` | `Application` (list) | `user` | `all, delete-orphan` | select | — |
| `User.field_mappings` | `UserFieldMapping` (list) | `user` | `all, delete-orphan` | select | — |
| `UserFieldMapping.user` | `User` | `field_mappings` | — | select | — |
| `Resume.user` | `User` | `resumes` | — | select | — |
| `Application.user` | `User` | `applications` | — | select | — |
| `Application.job` | `Job` | — (one-way) | — | **joined** | — |
| `Application.tailored_resume` | `Resume \| None` | — (one-way) | — | select | `foreign_keys=[tailored_resume_id]` |
| `Application.history` | `ApplicationStatusHistory` (list) | `application` | `all, delete-orphan` | select | `order_by="ApplicationStatusHistory.created_at"` |
| `ApplicationStatusHistory.application` | `Application` | `history` | — | select | — |
| `Interview.application` | `Application` | — (one-way) | — | **joined** | — |

These 11 attributes form 4 bidirectional pairs (`User`↔`Resume`, `User`↔`Application`, `User`↔`UserFieldMapping`, `Application`↔`ApplicationStatusHistory`), which account for 8 attributes, plus 3 one-way relationships: `Application.job`, `Application.tailored_resume` and `Interview.application`. `Job`, `Communication`, `Notification` and `AgentRun` declare no relationships.

Account deletion (`services/privacy.delete_user_data`) deletes rows explicitly in this FK-safe order: interviews of the user's applications, then communications, flush, then applications, flush, then tailored resumes (`parent_resume_id IS NOT NULL`), flush, then the user. The ORM `delete-orphan` cascades and the DB `ON DELETE CASCADE` remove the rest. Jobs are shared and never deleted with a user.

### 2.12 Enum registry (`app/models/enums.py`)

All enums are `class X(str, enum.Enum)`. They are persisted by **value** through the helper `pg_enum(enum_cls, name)`, which is `sqlalchemy.Enum(enum_cls, name=name, values_callable=lambda members: [m.value for m in members], validate_strings=True)`. One shared type instance exists per PG type (`JOB_TYPE_ENUM`, `EXPERIENCE_LEVEL_ENUM`, `ATS_PLATFORM_ENUM`, `APPLICATION_STATUS_ENUM`, `EMAIL_DIRECTION_ENUM`, `EMAIL_INTENT_ENUM`, `INTERVIEW_TYPE_ENUM`), so each PG ENUM is declared exactly once. On SQLite each one is a non-native `VARCHAR(n)`, where n is the longest value, and there is no CHECK constraint.

| Python class | PG type name | SQLite type | Values (in order) | Used by |
|---|---|---|---|---|
| `JobType` (5) | `job_type` | `VARCHAR(10)` | `full-time`, `part-time`, `internship`, `contract`, `freelance` (members FULL_TIME, PART_TIME, INTERNSHIP, CONTRACT, FREELANCE) | `jobs.job_type` |
| `ExperienceLevel` (6) | `experience_level` | `VARCHAR(10)` | `entry`, `mid`, `senior`, `lead`, `executive`, `internship` | `jobs.experience_level` |
| `ATSPlatform` (15) | `ats_platform` | `VARCHAR(15)` | `linkedin`, `indeed`, `glassdoor`, `wellfound`, `greenhouse`, `lever`, `workday`, `ashby`, `bamboohr`, `icims`, `taleo`, `smartrecruiters`, `jobvite`, `custom`, `unknown` | `jobs.source_platform`, `applications.ats_platform` |
| `ApplicationStatus` (17) | `application_status` | `VARCHAR(16)` | `discovered`, `matched`, `skipped`, `preparing`, `pending_approval`, `approved`, `applied`, `acknowledged`, `screening`, `interview`, `assessment`, `final_round`, `offer`, `accepted`, `rejected`, `withdrawn`, `failed` | `applications.status`, `application_status_history.old_status`, `application_status_history.new_status` |
| `EmailDirection` (2) | `email_direction` | `VARCHAR(8)` | `inbound`, `outbound` | `communications.direction` |
| `EmailIntent` (9) | `email_intent` | `VARCHAR(16)` | `acknowledgment`, `rejection`, `interview_invite`, `assessment`, `offer`, `follow_up`, `info_request`, `generic`, `unknown` | `communications.detected_intent` |
| `InterviewType` (9) | `interview_type` | `VARCHAR(16)` | `phone_screen`, `video_call`, `onsite`, `technical`, `behavioral`, `panel`, `take_home`, `pair_programming`, `other` | `interviews.interview_type` |

Member names are the upper-snake form of each value, with `-` replaced by `_` (for example `ApplicationStatus.PENDING_APPROVAL = "pending_approval"`).

Status helper constants in `enums.py`, which must be reproduced exactly:
- `SUBMITTED_STATUSES` = {APPLIED, ACKNOWLEDGED, SCREENING, INTERVIEW, ASSESSMENT, FINAL_ROUND, OFFER, ACCEPTED, REJECTED}
- `RESPONSE_STATUSES` = {ACKNOWLEDGED, SCREENING, INTERVIEW, ASSESSMENT, FINAL_ROUND, OFFER, ACCEPTED, REJECTED}
- `INTERVIEW_STATUSES` = {SCREENING, INTERVIEW, ASSESSMENT, FINAL_ROUND, OFFER, ACCEPTED}
- `STATUS_RANK` = DISCOVERED 0, MATCHED 1, SKIPPED 1, PREPARING 2, PENDING_APPROVAL 3, APPROVED 4, FAILED 4, APPLIED 5, ACKNOWLEDGED 6, SCREENING 7, ASSESSMENT 8, INTERVIEW 9, FINAL_ROUND 10, OFFER 11, ACCEPTED 12, REJECTED 12, WITHDRAWN 12. E-mail parsing uses this ranking so that it never moves an application backwards.

Free-text "pseudo-enum" `String` columns have no DB enforcement: `agent_runs.run_type`, `status`, `trigger`; `applications.review_decision` (`keep`/`skip`); `application_status_history.changed_by`; `jobs.company_verdict`, `company_tier`; `interviews.meeting_platform`, `outcome`; `communications.urgency`. The values are listed in the table sections above.

### 2.13 Default JSON documents: `users.preferences` and `users.consents`

`users.preferences` uses `default=default_preferences`, which returns `copy.deepcopy(DEFAULT_PREFERENCES)` (defined in `app/models/user.py`). Registration and Google sign-up also pass `preferences=default_preferences()` explicitly. `merge_preferences(current, updates)` starts from the defaults and overlays `current` and then `updates` key by key. The `sources` key is the exception: it is shallow-merged (`{**defaults.sources, **value}`). `User.prefs` returns `merge_preferences(self.preferences, None)`. `services/presets.py` (`apply_preset`) builds on `DEFAULT_PREFERENCES` and `merge_preferences` and has no defaults of its own. `PUT /users/me/preferences` accepts only the keys of the merged defaults plus `resume_template` and `auto_draft_replies` (`ALLOWED_PREF_KEYS`).

`DEFAULT_PREFERENCES` has **50 top-level keys**, listed in order:

| Key | Default |
|---|---|
| `target_roles` | `[]` |
| `target_locations` | `["Delhi, India", "India"]` |
| `remote_preference` | `"any"` (remote \| hybrid \| onsite \| any) |
| `salary_min` | `null` |
| `salary_max` | `null` |
| `salary_currency` | `"USD"` |
| `experience_level` | `["internship"]` |
| `industries` | `[]` |
| `company_size_preference` | `[]` |
| `companies_to_avoid` | `[]` |
| `companies_to_target` | `[]` |
| `max_applications_per_day` | `25` |
| `auto_apply_threshold` | `80` *(key name kept as is because it is not branding)* |
| `job_types` | `["internship"]` |
| `internships_only` | `true` |
| `year_of_study` | `2` |
| `graduation_year` | `null` |
| `focus_skills` | `[]` |
| `avoid_skills` | `[]` |
| `notification_channels` | `["email", "dashboard"]` |
| `notification_popups` | `true` |
| `keywords_exclude` | `[]` |
| `posted_within_days` | `14` |
| `scan_enabled` | `true` |
| `scan_interval_hours` | `6` |
| `platforms` | `["internshala", "linkedin", "internships", "greenhouse", "lever", "ashby", "workday", "generic"]` |
| `location_focus` | `{"enabled": true, "country": "India", "prime_cities": ["Delhi", "New Delhi", "Delhi NCR", "Gurugram", "Gurgaon", "Noida", "Greater Noida", "Faridabad", "Ghaziabad"], "country_share": 90}` |
| `internship_season` | `"Summer 2027"` |
| `progress_updates_everywhere` | `true` |
| `progress_digest` | `"daily"` (daily \| weekly \| off) |
| `review_mode` | `"swipe"` (swipe \| auto) |
| `resume_strategy` | `"original"` (original \| light \| full) |
| `auto_submit_kept` | `true` |
| `trust_generated_answers` | `true` |
| `auto_keep_min_score` | `null` |
| `max_jobs_per_source` | `null` (uses the server's `MAX_JOBS_PER_SOURCE`) |
| `exclude_no_sponsorship` | `false` |
| `internshala_bot_enabled` | `false` |
| `internshala_auto_submit` | `false` |
| `internshala_daily_limit` | `15` |
| `internshala_share` | `25` |
| `internshala_per_scan` | `10` |
| `skip_suspicious_companies` | `true` |
| `trusted_companies` | `[]` |
| `scan_top_companies` | `true` |
| `sources` | `{"greenhouse_boards": [], "lever_companies": [], "ashby_boards": [], "workday_sites": [], "career_pages": [], "internship_lists": ["simplify-internships", "vanshb03-internships"]}` |
| `discord_webhook_url` | `null` |
| `slack_webhook_url` | `null` |
| `timezone` | `"Asia/Kolkata"` |
| `cover_letter_enabled` | `true` |

`users.consents` uses `default=dict`, so it starts as `{}`. No default factory fills it. The code adds keys at runtime, and each value is an ISO-8601 UTC timestamp string:
- `gmail` and `calendar`: set by `google_oauth.store_tokens` when the granted scopes contain `gmail` or `calendar`
- `linkedin`: set on LinkedIn cookie sync
- `internshala`: set on Internshala session sync, which also removes `internshala_disconnected`
- `internshala_disconnected`: set on Internshala disconnect, which blocks background re-syncs that are not manual (HTTP 409)
- `internshala_bot`: set when the user turns on `internshala_bot_enabled`

Neither JSON column uses `MutableDict`/`MutableList`. Changing a dict in place is **not** detected, so code always assigns a new object (for example `consents = dict(user.consents or {}); …; user.consents = consents`).

### 2.14 Model ⇄ migration consistency findings

1. **Columns**: all 199 model columns exist after `0001…0006`, with identical types, lengths, nullability, FKs (including ondelete), unique constraints and server defaults. 0001 creates 187 columns and 0002–0006 add the other 12. No column exists in the migrations without a model column, and no model column is missing from the migrations.
2. **ORM indexes**: all 23 model-declared indexes are created by migrations under the same names. Twenty-one come from 0001, and `idx_jobs_company_tier` and `idx_jobs_company_verdict` come from 0006.
3. **Migration-only indexes (by design)**: `idx_jobs_embedding` (ivfflat), `idx_jobs_active` (partial), `idx_jobs_title_trgm` (GIN trigram) and `idx_comms_action_required` (partial) are not modelled. They are excluded from autogenerate through `env.py` `include_object`, and `create_all()` never creates them (SQLite / tests).
4. **Redundant index pairs**: `ix_jobs_is_active` and `idx_jobs_active` (partial) cover the same column, as do `idx_comms_action` and `idx_comms_action_required` (partial). Both members of each pair are kept.
5. **`applications.similarity_score`**: the model gives no explicit type, so SQLAlchemy 2.0.x resolves it to `Float` and 2.1.x to `Double`. Migration 0001 uses `sa.Double()`. On PostgreSQL both are `double precision`, and Alembic's PG implementation treats `FLOAT` and `DOUBLE PRECISION` as synonyms, so this produces no drift. `requirements.txt` allows `sqlalchemy>=2.0.30,<2.2`.
6. **JSON rendering**: 0001 uses `postgresql.JSONB(astext_type=sa.Text())` directly, while 0003, 0004 and 0006 use `sa.JSON().with_variant(postgresql.JSONB(...), 'postgresql')`. Both give `JSONB` on PG.
7. **Enums in 0001**: the seven types are created up front with `postgresql.ENUM(..., name=...).create(bind, checkfirst=True)`. Columns then reference them with `postgresql.ENUM(name=..., create_type=False)` and no value list.
8. **`users.ats_credentials`** was created by **0001**, not by a later migration.
9. **The chain is PostgreSQL-only**: 0001 executes `CREATE EXTENSION`, PG ENUMs and `Vector`. SQLite never runs Alembic; it uses `create_all()` plus `_add_missing_sqlite_columns()` (Section 3). The `batch_alter_table` and JSON-variant code in 0002–0006 is therefore never used on SQLite in practice.
10. **Physical column order on PG**: columns added by 0002–0006 are appended at the end of their tables, so `applications.review_decision`, `reviewed_at`, `auto_submit` and `field_overrides`, the 4 Internshala columns on `users`, and the 3 `company_*` columns on `jobs` come after `updated_at`/`last_checked`. The model order differs. This does not matter to Alembic.
11. Only 2 columns have server defaults. Every other NOT NULL column with a default (booleans, counters, timestamps, `preferences`) depends on Python-side defaults, so raw SQL inserts must supply them.
12. `EmbeddingType.comparator_factory.cosine_distance` (PG operator `<=>`) is defined but unused in application code. Its dimension is hard-coded to 1536 in the models and is independent of `settings.EMBEDDING_DIM` (default 1536).

---

---

## Section 3: Custom SQLAlchemy Type Implementations

### 3.1 Inventory

| Name | Kind | Location | `impl` / base | `cache_ok` |
|---|---|---|---|---|
| `UTCDateTime` | `TypeDecorator` | `app/core/database.py` | `DateTime(timezone=True)` | `True` |
| `JSONType` | type **instance** (a variant, not a class) | `app/core/database.py` | `JSON().with_variant(JSONB(), "postgresql")` | n/a |
| `EmbeddingType` | `TypeDecorator` (with `comparator_factory`) | `app/core/database.py` | `Text`; dialect impl is `pgvector.sqlalchemy.Vector(dim)` on PG | `True` |
| `EncryptedText` | `TypeDecorator` | `app/core/security.py` | `Text` | `True` |
| `EncryptedJSON` | `TypeDecorator` | `app/core/security.py` | `Text` | `True` |
| `pg_enum(enum_cls, name)` | factory that returns a `sqlalchemy.Enum` | `app/models/enums.py` | `Enum(..., values_callable=values, validate_strings=True)` | n/a |

There are no other `TypeDecorator`s in the backend.

### 3.2 `UTCDateTime`

- `impl = DateTime(timezone=True)`, so PG gets `TIMESTAMP WITH TIME ZONE` and SQLite gets `DATETIME`.
- `process_bind_param(value, dialect)`:
  - `None` → `None`.
  - A naive value is **assumed to be UTC** (`value.replace(tzinfo=UTC)`). An aware value is converted with `value.astimezone(UTC)`.
  - On SQLite (`dialect.name == "sqlite"`) the tzinfo is stripped and the value is stored as naive UTC. On other dialects the aware UTC datetime is passed through.
- `process_result_value(value, dialect)`: `None` → `None`. A naive result gets `tzinfo=UTC`. An aware result goes through `.astimezone(UTC)`. **Every datetime read from the DB is therefore timezone-aware UTC on both dialects.**
- Companion: `utcnow() -> datetime.now(UTC)`. It is the default and onupdate callable for all timestamp columns.

### 3.3 `JSONType`

- `JSONType = JSON().with_variant(JSONB(), "postgresql")`: `JSONB` on PostgreSQL and SQLAlchemy `JSON` (stored as text) on SQLite and other dialects.
- Serialization uses the dialect's default JSON serializer (`json.dumps`). No custom serializer is configured on the engine.
- It is not mutable-tracked; see 2.13.

### 3.4 `EmbeddingType(dim=1536)`

- `__init__(self, dim=1536, *args, **kwargs)` stores `self.dim`.
- `impl = Text`. `load_dialect_impl`: on `postgresql` it returns `dialect.type_descriptor(pgvector.sqlalchemy.Vector(self.dim))` (`pgvector` is imported lazily inside the method). Otherwise it returns `dialect.type_descriptor(Text())`.
- `process_bind_param`: `None` → `None`. Otherwise `values = [float(v) for v in value]`. On PG it passes the Python list to pgvector, which renders `'[...]'`. Elsewhere it returns `json.dumps(values)`, a JSON array string.
- `process_result_value`: `None` → `None`. A `str` that starts with `"["` is decoded with `json.loads` into a list of floats. Any other `str` → `None`. Anything else (for example the numpy array pgvector returns) → `[float(v) for v in value]`. **The result is always a `list[float]` or `None`.**
- `comparator_factory(TypeDecorator.Comparator)` adds `cosine_distance(other)`, which is `self.op("<=>", return_type=Float)(other)`, pgvector's cosine-distance operator (PG only).

### 3.5 Encryption scheme (`EncryptedText`, `EncryptedJSON`)

Module constants: `JWT_ALGORITHM = "HS256"`, `_ENC_PREFIX = "v1:"`.

**Key derivation (`_load_key()`, evaluated once at import time into the module global `_KEY`, so a key change needs a process restart):**
1. If `settings.ENCRYPTION_KEY` is set: strip it, pad it with `=` to a multiple of 4, and `base64.urlsafe_b64decode` it. If decoding fails, use `b""`. If the decoded key is **exactly 32 bytes**, use it directly.
2. If `ENCRYPTION_KEY` is set but is not a valid 32-byte urlsafe-b64 key (a passphrase), use `SHA-256(raw.encode("utf-8"))`.
3. If `ENCRYPTION_KEY` is unset (development fallback), use `SHA-256(("enc:" + settings.SECRET_KEY).encode("utf-8"))`. Encrypted data then depends on `SECRET_KEY`.

Key generator helper: `generate_encryption_key()` returns `base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")`.

**`encrypt_str(plaintext)`**: `None` → `None`. Otherwise `nonce = os.urandom(12)` (a **96-bit nonce**) and `ciphertext = AESGCM(_KEY).encrypt(nonce, plaintext.encode("utf-8"), None)`. That is AES-256-GCM with no associated data, and the ciphertext includes the 16-byte GCM tag. The function returns `"v1:" + base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")`.

**Stored format**: `v1:<urlsafe-base64( 12-byte nonce ‖ ciphertext ‖ 16-byte tag )>`, kept in a `TEXT` column.

**`decrypt_str(token)`**: `None` → `None`. A value **without** the `v1:` prefix is returned unchanged, as legacy plaintext passthrough. Otherwise the function base64-decodes the value, splits it into `blob[:12]` (the nonce) and `blob[12:]`, and runs AES-GCM decrypt, which raises on a wrong key or tampering. The result is UTF-8 decoded.

**`EncryptedText`** (`impl = Text`):
- bind: `encrypt_str(value)`. An empty string is encrypted too.
- result: `decrypt_str(value)`. **Any exception (wrong key, corrupt data) returns `None`** instead of raising.

**`EncryptedJSON`** (`impl = Text`):
- bind: `None` → `None`. Otherwise `encrypt_str(json.dumps(value, sort_keys=True))`.
- result: `None` → `None`. Otherwise it decrypts and returns `json.loads(decrypted)` if the decrypted text is non-empty, else `None`. **Any exception returns `None`.**

### 3.6 `pg_enum` (`app/models/enums.py`)

`SAEnum(enum_cls, name=name, values_callable=lambda members: [m.value for m in members], validate_strings=True)`. The DB stores the enum **values** (for example `full-time`), not the member names. A string bound to the column must be a valid value. On PG it is a named native ENUM type. On SQLite it is non-native `VARCHAR(len(longest value))` with no CHECK constraint. The seven shared instances are listed in 2.12.

### 3.7 Engine, sessions and helpers (`app/core/database.py`)

**`_build_engine(url)`**
- **SQLite** (`url.startswith("sqlite")`):
  - `connect_args={"check_same_thread": False, "timeout": 30}`. With the 30-second busy timeout, writers wait instead of failing fast.
  - In-memory URLs (`"sqlite://"` or `"sqlite:///:memory:"`) use `poolclass=StaticPool`.
  - A `connect` event listener runs `PRAGMA foreign_keys=ON` on every connection. For file databases (not in-memory) it also runs `PRAGMA journal_mode=WAL` and `PRAGMA synchronous=NORMAL`.
- **Everything else (PostgreSQL)**: `create_engine(url, pool_pre_ping=True, pool_size=settings.DB_POOL_SIZE, max_overflow=settings.DB_POOL_SIZE * 2, pool_recycle=1800)`. With the default `DB_POOL_SIZE` of 10, that is pool size 10, max overflow 20, and connections recycled after 30 minutes. `pool_timeout` is left at SQLAlchemy's default.
- Default `DATABASE_URL` is `postgresql+psycopg://hireflow:hireflow@localhost:5432/hireflow` (psycopg 3 driver). Local mode (`start.sh`) uses `sqlite:///<repo>/backend/data/hireflow.db`.

**Module globals**: `engine = _build_engine(settings.DATABASE_URL)`. `SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, class_=Session)`.

**`configure_engine(url)`**: rebuilds the global `engine` and calls `SessionLocal.configure(bind=engine)`. Tests and scripts use it, and it returns the engine.

**`get_db()`**: the FastAPI dependency, a generator. It yields `SessionLocal()`, then **commits** after the request handler returns, **rolls back** and re-raises on an exception, and always closes the session. Route code therefore usually does not call `commit()`; `flush()` is used where IDs are needed.

**`checkpoint(db)`**: `if db.in_transaction(): db.commit()`. It is used before long network or browser steps so that the SQLite write lock is not held throughout.

**`session_scope()`**: a `@contextmanager` with the same commit / rollback / close semantics as `get_db`. Workers and scripts use it.

**`wait_for_db(retries=None, delay=1.0)`**: `attempts = retries if retries is not None else settings.DB_CONNECT_RETRIES` (default **5**). Each attempt opens a connection and runs `SELECT 1`. On `OperationalError` it logs `"Database not ready (attempt %s/%s): %s"` and sleeps `delay` seconds; the last attempt re-raises. It is called in the FastAPI lifespan (via `asyncio.to_thread`) and by `scripts/migrate.py`.

**`create_all()`**: imports `app.models`. On PostgreSQL it runs `CREATE EXTENSION IF NOT EXISTS vector` and `CREATE EXTENSION IF NOT EXISTS pg_trgm` in one transaction. It then runs `Base.metadata.create_all(bind=engine)`, and on SQLite it also runs `_add_missing_sqlite_columns()`. The FastAPI lifespan calls it **only when `settings.is_sqlite`**, as does `scripts/migrate.py` for SQLite. PostgreSQL deployments use Alembic. `create_all()` does not create the 4 raw-SQL indexes or an `alembic_version` table.

**`_add_missing_sqlite_columns()`**: local SQLite databases have no Alembic history, so this function upgrades them in place. For each table in `Base.metadata.sorted_tables` it inspects the existing columns, and for each model column that is missing it executes `ALTER TABLE "<table>" ADD COLUMN "<col>" <type compiled for SQLite>`. If the column has a `server_default`, it appends `NOT NULL DEFAULT <compiled default>` when the column is non-nullable, or `DEFAULT <compiled default>` otherwise. `false()` compiles to `0`, so the result is for example `... BOOLEAN NOT NULL DEFAULT 0`. Columns without a server default are added as nullable. Each addition is logged as `"Added column %s.%s"`. The function does **not** add new indexes to existing tables.

**FastAPI lifespan order** (`app/main.py`):
1. `wait_for_db` (in a thread).
2. If SQLite, `create_all` (in a thread).
3. Bind the WebSocket manager loop and start the Redis subscriber.
4. Initialize the LLM and log `"HireFlow API ready (env=%s, llm=%s, db=%s)"`.
5. In production, log each `validate_for_production()` problem as `CONFIG: …`.
6. On shutdown, stop the subscriber.

---

---

## Section 4: Security Architecture

### 4.1 Secrets and production validation (`app/config.py`)

| Setting | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | `"change-me-in-production-please-use-a-long-random-string"` (`DEFAULT_SECRET`, unbranded) | JWT HS256 signing key; also the source of the fallback encryption key |
| `ENCRYPTION_KEY` | `None` | urlsafe-base64 32-byte AES-256-GCM key, or a passphrase (hashed with SHA-256) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60 * 24 * 7` = **10080** (7 days) | access-token and cookie lifetime |
| `EXTENSION_TOKEN_EXPIRE_DAYS` | **180** | browser-extension token lifetime |
| `COOKIE_NAME` | **`"hireflow_session"`** (source: `autoapply_session`) | session cookie name |
| `COOKIE_SECURE` | `False` | the cookie's `Secure` flag |
| `RATE_LIMIT_DEFAULT` | `"300/minute"` | SlowAPI default limit |
| `ALLOW_REGISTRATION` | `True` | gates `/auth/register` and Google sign-up |
| `CORS_ORIGINS` | `"http://localhost:3000,http://127.0.0.1:3000"` | comma-separated list, parsed by the `cors_origins` property |
| `SENTRY_DSN` | `None` | enables Sentry |
| `ENVIRONMENT` | `"development"` | `development` \| `test` \| `production` |

Settings are loaded with pydantic-settings from `<repo>/.env` and then `backend/.env` (`case_sensitive=True`, `extra="ignore"`). A `field_validator("*", mode="before")` turns string values that start with `#` (inline comments) into the field's default. It does the same for empty strings when the field's default is `None`.

`Settings.validate_for_production()` returns a list of problems:
1. `"SECRET_KEY must be set to a random string of at least 32 characters"` when `SECRET_KEY == DEFAULT_SECRET` or `len(SECRET_KEY) < 32`.
2. `"ENCRYPTION_KEY must be set (python -c \"import os,base64;print(base64.urlsafe_b64encode(os.urandom(32)).decode())\")"` when it is empty.
3. `"COOKIE_SECURE should be true when served over HTTPS"` when `COOKIE_SECURE` is false.

When `ENVIRONMENT == "production"`, each problem is logged as **a warning only** (`logger.warning("CONFIG: %s", problem)`), once in `get_settings()` and once at API startup in the lifespan. **The app is not prevented from starting.** The production compose file makes the values mandatory instead: `SECRET_KEY: ${SECRET_KEY:?set SECRET_KEY}`, `ENCRYPTION_KEY: ${ENCRYPTION_KEY:?set ENCRYPTION_KEY}`, `COOKIE_SECURE: "true"`, `ENVIRONMENT: production`.

### 4.2 Password hashing (`core/security.py`)

- `hash_password(pw)`: `digest = base64.b64encode(hashlib.sha256(pw.encode("utf-8")).digest())` is a 44-byte value that avoids bcrypt's 72-byte truncation. The function returns `bcrypt.hashpw(digest, bcrypt.gensalt(rounds=12)).decode("utf-8")`. The scheme is **bcrypt, cost 12, over base64(SHA-256(password))**.
- `verify_password(pw, hashed)`: returns `False` if `hashed` is falsy (Google-only accounts). Otherwise it recomputes the same digest and returns `bcrypt.checkpw(digest, hashed.encode())`. A `ValueError` (malformed hash) returns `False`.
- Input rules (`schemas/user.py`): `RegisterRequest.password` must be 8–256 characters, `PasswordChange.new_password` 8–256, `full_name` 1–255, and `email` must be an `EmailStr`. `LoginRequest.password` is unconstrained.
- `POST /auth/password`: if the user already has a password, `current_password` must verify, otherwise the endpoint returns 400 `"Current password is incorrect"`. Google-only users can set a password without the current one. **Existing JWTs are not revoked.**

### 4.3 JWT (`create_token` / `decode_token`)

- Library PyJWT, **algorithm `HS256`**, key `settings.SECRET_KEY`.
- `create_token(subject, scope="access", expires_delta=None, extra=None)` builds the payload `{"sub": subject, "scope": scope, "iat": int(now), "exp": int(now + (expires_delta or ACCESS_TOKEN_EXPIRE_MINUTES)), "jti": secrets.token_hex(8)}` and then applies `payload.update(extra)`. `jti` is 16 hex characters. There is no `aud`, `iss` or `nbf`.
- `decode_token(token, expected_scopes=("access",))` calls `jwt.decode(token, SECRET_KEY, algorithms=["HS256"])` with default verification (signature and `exp`, zero leeway):
  - `ExpiredSignatureError` → `TokenError("Token expired")`
  - any other `PyJWTError` → `TokenError("Invalid token")`
  - `payload["scope"] not in expected_scopes` → `TokenError("Token scope not allowed here")`
- There is no denylist or revocation. Logout only clears the cookie, and a bearer token stays valid until `exp`.

### 4.4 Token scopes

| Scope | Lifetime | Issued by | `sub` | Extra claims | Accepted by |
|---|---|---|---|---|---|
| `access` | `ACCESS_TOKEN_EXPIRE_MINUTES` = **10080 min (7 days)** | `POST /auth/register`, `POST /auth/login`, `GET /auth/google/callback` (via `_set_session`) | user UUID | — | every `CurrentUser` endpoint (`("access",)`), `ExtensionUser` endpoints, WebSocket `/ws` |
| `ws` | **5 minutes** (`timedelta(minutes=5)`) | `GET /auth/ws-token` returns `{"token": …}` (requires `access`) | user UUID | — | WebSocket `/ws` only (`expected_scopes=("ws", "access")`) |
| `extension` | `EXTENSION_TOKEN_EXPIRE_DAYS` = **180 days** | `POST /auth/extension-token` returns `{"token", "expires_in_days": 180, "api_url": PUBLIC_API_URL}` (requires `access`) | user UUID | — | only the `ExtensionUser` dependency (`("access", "extension")`), used by `POST /users/me/integrations/linkedin-cookie` and `POST /users/me/integrations/internshala-session` |
| `oauth_state` | **15 minutes** | `google_oauth.build_auth_url()` puts it in the Google OAuth `state` parameter | user UUID (connect mode) or the literal `"anonymous"` (login mode) | `mode`: `"login"` \| `"connect"`; `next`: post-login path (default `"/dashboard/settings"`, or `"/dashboard"` for login, or the caller's `next`) | `GET /auth/google/callback` via `parse_state` (`("oauth_state",)`) |

### 4.5 Session cookie

Set by `_set_session(response, user)` on register, login and Google callback:

```
response.set_cookie("hireflow_session", <access JWT>, httponly=True, secure=settings.COOKIE_SECURE,
                    samesite="lax", max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60, path="/")
```

| Attribute | Development (defaults / `.env.example`) | Production (`docker-compose.prod.yml`) |
|---|---|---|
| Name | `hireflow_session` | `hireflow_session` |
| HttpOnly | yes | yes |
| Secure | **no** (`COOKIE_SECURE=false`) | **yes** (`COOKIE_SECURE: "true"`) |
| SameSite | `Lax` | `Lax` |
| Domain | not set (host-only) | not set (host-only) |
| Path | `/` | `/` |
| Max-Age | `604800` s (7 days) | `604800` s |

- Register and login also return the token in the JSON body: `{"user": user_out(user), "access_token": token}`.
- `POST /auth/logout` and `DELETE /users/me` call `response.delete_cookie("hireflow_session", path="/")`.
- The cookie is first-party in every topology because the dashboard proxies `/api/v1/:path*` and `/docs` to the backend through Next.js rewrites, and in production Caddy routes `/api/v1/*`, `/docs*` and `/health*` to the API on the same origin.
- Renaming the cookie from `autoapply_session` to `hireflow_session` logs out any existing sessions. That is expected for the clone.

### 4.6 Request authentication (`api/deps.py`)

- `_extract_token(request)`: an `Authorization` header that starts with `bearer ` (case-insensitive) wins, and the token is `auth[7:].strip()`. Otherwise the token comes from the `hireflow_session` cookie. **A bearer token takes precedence over the cookie.**
- `_user_from_request(request, db, scopes)`: no token → 401 `"Not authenticated"`. A `TokenError`, `ValueError` (bad UUID) or `KeyError` → 401 with the exception text or `"Invalid token"`. It then loads `db.get(User, uuid)`; a missing or `is_active=False` user → 401 `"User not found or inactive"`.
- `get_current_user` accepts `("access",)` and is aliased `CurrentUser`. `get_current_user_or_extension` accepts `("access", "extension")` and is aliased `ExtensionUser`.
- `parse_uuid(value)`: an invalid UUID → **404** `"Not found"`. This avoids leaking whether an ID exists.
- Login: an unknown email or wrong password → 401 `"Invalid email or password"`; an inactive account → 403 `"Account disabled"`. Register: registration disabled → 403 `"Registration is disabled"`; email already exists (case-insensitive) → 409.

### 4.7 Token flows

- **WebSocket** (`/api/v1/ws`):
  1. The client gets a `ws` token from `GET /auth/ws-token` and connects with `?token=…`. Without the query parameter the server falls back to the `hireflow_session` cookie.
  2. The server runs `decode_token(raw or "", ("ws", "access"))`. Failure, or a missing or inactive user (checked in a short `SessionLocal()` block), ends with `websocket.close(code=4401)`.
  3. On success the server sends `{"type": "connected", "data": {"user_id": …}}` and answers the text message `ping` with `{"type": "pong", "data": {}}`.
  4. Events fan out over Redis pub/sub on channel `events:<user_id>`.
- **Browser extension**: the dashboard calls `POST /auth/extension-token`. The extension stores the 180-day `extension` token and sends it as `Authorization: Bearer`. This scope is accepted **only** on the two session-sync endpoints. `InternshalaSessionIn` validation:
  - cookies list: 1–60 items
  - domain must match `^\.?(?:[a-z0-9-]+\.)*internshala\.com$`, else 422
  - cookie name must match the RFC token regex `[A-Za-z0-9!#$%&'*+.^_\`|~-]+`
  - values with control characters, `;` or DEL are rejected
  - expired cookies are dropped
  - total name+value length above 32,000 → 413
  - a session cookie and a logged-in state are required (422 otherwise)
  - user agent: if it does not match `Mozilla/5\.0 [\x20-\x7e]{10,500}`, it is stored as `NULL`
  - `reason` other than `manual` after a dashboard disconnect → 409

  `LinkedInCookieIn.li_at` must be 10–4000 characters.
- **Google OAuth `oauth_state`**:
  - `GET /auth/google/login?next=` → 302 to Google with `prompt=select_account` and scopes `openid email profile`.
  - `GET /auth/google/connect` (requires `access`) → JSON `{"url": …}` with `prompt=consent`. Scopes are the login scopes plus `gmail.readonly`, `gmail.modify`, `gmail.labels`, `calendar.events` and `calendar.readonly`. Both modes use `access_type=offline` and `include_granted_scopes=true`.
  - Redirect URI: `GOOGLE_REDIRECT_URI`, or `{FRONTEND_URL}{API_PREFIX}/auth/google/callback`.
  - Callback errors (`error` set, missing `code` or `state`, a bad or expired state, a failed token exchange or userinfo call) redirect to `{FRONTEND_URL}/login?error=google_oauth_failed` (or `?error=<error>`).
  - `next` must start with `/`, otherwise it becomes `/dashboard`. This is the open-redirect guard.
  - **Connect mode**: loads the user with `sub` (missing user → `/login?error=session_expired`) and stores the encrypted tokens. It then tries to start the Gmail watch, enqueues `check_user_email`, and redirects to `next?google=connected`. It does **not** set a session cookie.
  - **Login mode**: finds or creates the user by lowercased Google email. Registration disabled → `/login?error=registration_disabled`. It sets the session cookie and redirects to `next`.
  - Without `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET`, the login and connect endpoints return **501**.

### 4.8 Encryption at rest

| Column | Type | Content |
|---|---|---|
| `users.google_access_token` | `EncryptedText` | Google OAuth access token |
| `users.google_refresh_token` | `EncryptedText` | Google OAuth refresh token |
| `users.linkedin_session_cookie` | `EncryptedText` | LinkedIn `li_at` cookie |
| `users.internshala_session` | `EncryptedJSON` | list of Internshala cookie dicts |
| `users.ats_credentials` | `EncryptedJSON` | `{key: secret}` per-ATS logins |

The scheme is AES-256-GCM with the `v1:` format (Section 3.5). `users.hashed_password` is a bcrypt hash and is not encrypted. `user_field_mappings.field_value` is **not** encrypted.

Blob storage: `S3Storage.save` adds `ServerSideEncryption="AES256"` when no `S3_ENDPOINT_URL` is set (AWS S3). R2 and MinIO are left to their own defaults.

The GDPR export (`GET /users/me/export`, file `hireflow-export-<YYYY-MM-DD>.json`) omits `SECRET_USER_FIELDS = {hashed_password, google_access_token, google_refresh_token, linkedin_session_cookie, internshala_session, ats_credentials}` and the embeddings. It masks any field-mapping value whose `field_name` contains `"password"` as `"********"`. `GET /users/me/integrations` returns only the **key names** of `ats_credentials`. `user_out` never returns tokens or hashes; it returns booleans such as `has_password`, `google_connected` and `linkedin_connected`.

### 4.9 Rate limiting (SlowAPI, `api/deps.py`)

```python
def _rate_key(request):
    token = request.cookies.get(settings.COOKIE_NAME) or request.headers.get("authorization", "")
    return f"{get_remote_address(request)}:{hash(token) if token else ''}"

limiter = Limiter(key_func=_rate_key, default_limits=[settings.RATE_LIMIT_DEFAULT],
                  storage_uri=settings.REDIS_URL if settings.REDIS_URL and not settings.is_sqlite else "memory://",
                  enabled=settings.ENVIRONMENT != "test")
```

- **Key**: client IP (`request.client.host`, as set by uvicorn's proxy-headers handling), a colon, and Python `hash()` of the session cookie or `Authorization` header (empty for anonymous requests). Python's `str` hash is salted per process, so with several uvicorn workers (`API_WORKERS`, default 2) and shared Redis, the same client gets a different key in each worker. Effective limits are per worker. HireFlow keeps this behaviour unless it is fixed on purpose.
- **Storage**: `REDIS_URL` when it is set and the DB is not SQLite, otherwise `memory://`. SlowAPI defaults apply: `headers_enabled=False` (no `X-RateLimit-*` headers), `swallow_errors=False`, no in-memory fallback, `key_style="url"` (limits are counted per route).
- **Enabled** unless `ENVIRONMENT == "test"`.
- **Wiring** (`main.py`): `app.state.limiter = limiter` and `app.add_middleware(SlowAPIMiddleware)`. The middleware applies the default **300/minute** to every HTTP route that has no `@limiter.limit` decorator. It skips decorated routes (slowapi `_should_exempt`: the route is in `_route_limits`), and the decorator enforces their own limit. WebSockets are not limited.
- **Per-route limits** (only these routes are decorated; each one gets its own limit **instead of** the default):

| Route | Limit |
|---|---|
| `POST /api/v1/auth/register` | `10/minute` |
| `POST /api/v1/auth/login` | `20/minute` |
| `POST /api/v1/users/me/integrations/llm/test` | `10/minute` |
| `POST /api/v1/users/me/integrations/ollama/pull` | `10/minute` |

- **Exceeded**: always HTTP **429**, but the body depends on which path caught the request:
  - **Decorated routes**: the decorator raises `RateLimitExceeded` inside the endpoint. FastAPI's registered handler `rate_limit_handler` then returns `{"detail": "Rate limit exceeded: <exc.detail>"}`, for example `"Rate limit exceeded: 10 per 1 minute"`.
  - **Default-limit routes**: the check runs in `SlowAPIMiddleware` through `sync_check_limits`. The registered handler is `async`, which that path cannot call, so slowapi falls back to its own `_rate_limit_exceeded_handler`, which returns `{"error": "Rate limit exceeded: 300 per 1 minute"}`.
  - Neither path sends rate-limit headers.
- Separate from HTTP limiting: `services/rate_limiter.py` holds per-platform outbound scraping and application limits backed by Redis with an in-memory fallback, for example LinkedIn 100 req/h, 25 applications/day and a 120–300 s cooldown, plus a 15-minute pause after an HTTP 429. Another section covers it.

### 4.10 Security headers

Backend `@app.middleware("http") security_headers` uses `response.headers.setdefault`, so it never overwrites a header a route already set:

| Header | Value |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `SAMEORIGIN` (resume PDFs preview in same-origin iframes) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |

The backend sends **no** CSP, HSTS, Permissions-Policy or COOP/COEP headers.

- **Frontend** (`next.config.js`, `source: "/:path*"`): the same three headers with the same values. `poweredByHeader: false`.
- **Caddy** (production): `Strict-Transport-Security "max-age=31536000; includeSubDomains"`. The `Server` header is removed (`-Server`), and responses are compressed with `encode zstd gzip`. TLS comes from Let's Encrypt automatically.
- `GET /files/{key}` adds `Cache-Control: private, max-age=300` for locally served files.

Middleware order: Starlette makes the last-added middleware the outermost, so from outside in the stack is `security_headers` → `CORSMiddleware` → `SlowAPIMiddleware` → routers.

### 4.11 CORS

`CORSMiddleware(allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])`. The default origins are `http://localhost:3000` and `http://127.0.0.1:3000`. Development compose uses `${CORS_ORIGINS:-http://localhost:3000}` and production uses `https://${DOMAIN}`. There is no `allow_origin_regex` and no `expose_headers`.

### 4.12 Trusted hosts and proxy headers

- The app has **no** `TrustedHostMiddleware`, `HTTPSRedirectMiddleware` or `ProxyHeadersMiddleware`.
- The container entrypoint (`backend/docker-entrypoint.sh`, role `api`) first runs `python scripts/migrate.py` and then `exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${API_WORKERS:-2}" --proxy-headers --forwarded-allow-ips="*"`. `X-Forwarded-For` and `X-Forwarded-Proto` are trusted from **any** peer. This matters for the rate-limit IP.
- In production only Caddy publishes ports (80 and 443), and the API listens only on the compose network. Development compose publishes `8000:8000` (and `5432`).
- The API's Swagger UI is always on at `/docs`, with OpenAPI at `/api/v1/openapi.json`. `GET /health` and `GET /health/ready` are unauthenticated; `/health/ready` returns the database error text when it fails, with 503.

### 4.13 Sentry (`core/logging_config.py`)

If `SENTRY_DSN` is set, `configure_logging()` calls `sentry_sdk.init(dsn=SENTRY_DSN, environment=settings.ENVIRONMENT, traces_sample_rate=0.1, send_default_pii=False)`. The dependency is `sentry-sdk[fastapi]>=2.5,<3`, and the FastAPI integration is automatic. Logging otherwise uses `basicConfig` at `LOG_LEVEL` with the format `"%(asctime)s %(levelname)s %(name)s: %(message)s"`. The `httpx`, `httpx2`, `httpcore`, `googleapiclient.discovery_cache`, `urllib3` and `anthropic` loggers are set to WARNING.

### 4.14 SSRF and URL validation

**There is no generic SSRF protection**: no private, loopback or link-local IP filtering and no outbound allowlist. The server fetches or posts to user-controlled URLs in these places:
- `preferences.sources.career_pages`, `workday_sites` and `internship_lists` (raw JSON URLs), and the board slugs, through the scrapers
- `preferences.discord_webhook_url` and `slack_webhook_url`, through the notifier POST
- application and job URLs, opened by Playwright

The preference keys are checked against `ALLOWED_PREF_KEYS`, and an unknown key returns 422 `"Unknown preference keys: [...]"`. The URL values themselves are not validated.

Targeted validations that do exist:
- OAuth `next` must start with `/`.
- The Internshala cookie domain, name, value and user-agent rules from 4.7.
- LinkedIn `profile_url` is used only if it contains `linkedin.com/in/`, and it is stored without its query string.
- The Ollama base URL comes only from env or settings, never from a user. `localhost` is rewritten to `host.docker.internal` inside containers.

### 4.15 File access authorization (`api/files.py`, `core/storage.py`)

- `GET /api/v1/files/{key:path}` requires `CurrentUser` (`access` scope, cookie or Bearer).
- The key is URL-decoded (`unquote`). If it does **not** start with `user_prefix(user.id) + "/"`, which is `users/<uuid>/`, or if it contains `..`, the endpoint returns **404** `"File not found"` (not 403).
- With **S3** storage it returns a 302 redirect to `presigned_url(key, expires=300)`, valid for 5 minutes.
- With **local** storage it calls `storage.read(key)`; `FileNotFoundError` or `OSError` → 404. It returns the bytes with `media_type = mimetypes.guess_type(key)[0] or "application/octet-stream"` and `Cache-Control: private, max-age=300`.
- Defence in depth: `_safe_key()` drops empty, `.` and `..` path segments and normalizes `\` to `/`. `LocalStorage._path()` resolves the path and raises `ValueError("Invalid storage key")` unless it lies under the storage root.
- Account deletion calls `delete_prefix(users/<uuid>)`.

### 4.16 Inbound webhook (Gmail Pub/Sub)

`POST /api/v1/webhooks/gmail?token=…` returns 204. If `GMAIL_PUBSUB_VERIFICATION_TOKEN` is set, a `token` query parameter that does not match (plain `!=`, not a constant-time compare) gets 403 `"Invalid token"`. **If the setting is unset, the endpoint is unauthenticated.** The handler decodes `message.data` as base64 JSON (malformed → 400 `"Malformed Pub/Sub message"`) and enqueues `handle_gmail_push(emailAddress, historyId)`.

### 4.17 Other security-relevant behaviour

- `ALLOW_REGISTRATION=false` blocks both `/auth/register` and Google sign-up for unknown emails.
- `DELETE /users/me` requires the body `{"confirm": "DELETE"}`, otherwise it returns 400 `"Type DELETE to confirm"`. It revokes the Google token, deletes the storage prefix, deletes the data (2.11) and clears the cookie.
- `GET /auth/config` is public. It returns `google_enabled`, `registration_enabled`, `llm_providers`, `llm_model` and `environment`.
- The FastAPI app is `title="HireFlow", version="1.0.0"`.

---

---

## Section 5: Complete Frontend Route Registry

All paths are relative to `frontend/`. Framework: Next.js `14.2.35` App Router, React 18, TypeScript (strict), Tailwind 3 + shadcn/ui ("new-york" style), SWR 2, Framer Motion, Recharts, sonner. Path alias `@/*` → `./src/*`.

Every API path below is relative to the API client base `"/api/v1"` (see Section 6, `lib/api-client.ts`) unless written as a full `/api/v1/...` browser link. "LIVE" = SWR options `{ refreshInterval: 15000, revalidateOnFocus: true }`.

There is **no** `middleware.ts`, `not-found.tsx`, `error.tsx`, `loading.tsx` or `route groups` in the app. Authentication is enforced client-side: any non-`/auth/*` API call returning 401 redirects to `/login?next=<current path+query>`.

### 5.0 Route file summary (22 route files)

| # | Route | File | Kind | Rendering |
|---|---|---|---|---|
| 1 | (root) | `src/app/layout.tsx` | Root layout | Server component |
| 2 | (root) | `src/app/template.tsx` | Root template | Server file wrapping client `RootFade` |
| 3 | `/` | `src/app/page.tsx` | Page (landing) | Server component (no `"use client"`) |
| 4 | `/login` | `src/app/login/page.tsx` | Page | Server; renders client `AuthForm` in `<Suspense>` |
| 5 | `/register` | `src/app/register/page.tsx` | Page | Server; renders client `AuthForm` in `<Suspense>` |
| 6 | `/api/health` | `src/app/api/health/route.ts` | Route handler (GET) | `dynamic = "force-dynamic"` |
| 7 | `/dashboard/*` | `src/app/dashboard/layout.tsx` | Layout | Server file wrapping client `DashboardShell` |
| 8 | `/dashboard/*` | `src/app/dashboard/template.tsx` | Template | Server file wrapping client `PageTransition` |
| 9 | `/dashboard` | `src/app/dashboard/page.tsx` | Page (Overview) | Client |
| 10 | `/dashboard/review` | `src/app/dashboard/review/page.tsx` | Page (Swipe Review) | Client |
| 11 | `/dashboard/top-companies` | `src/app/dashboard/top-companies/page.tsx` | Page (Top companies) | Client — **not in the expected list** |
| 12 | `/dashboard/submit` | `src/app/dashboard/submit/page.tsx` | Page (Ready to submit) | Client, inner component in `<Suspense>` |
| 13 | `/dashboard/applications` | `src/app/dashboard/applications/page.tsx` | Page | Client, `<Suspense>` |
| 14 | `/dashboard/applications/[id]` | `src/app/dashboard/applications/[id]/page.tsx` | Dynamic page | Client |
| 15 | `/dashboard/applied` | `src/app/dashboard/applied/page.tsx` | Page (I Applied) | Client |
| 16 | `/dashboard/jobs` | `src/app/dashboard/jobs/page.tsx` | Page (All jobs) | Client |
| 17 | `/dashboard/emails` | `src/app/dashboard/emails/page.tsx` | Page | Client, `<Suspense>` |
| 18 | `/dashboard/interviews` | `src/app/dashboard/interviews/page.tsx` | Page | Client, `<Suspense>` |
| 19 | `/dashboard/analytics` | `src/app/dashboard/analytics/page.tsx` | Page | Client |
| 20 | `/dashboard/logs` | `src/app/dashboard/logs/page.tsx` | Page | Client, `<Suspense>` |
| 21 | `/dashboard/resume` | `src/app/dashboard/resume/page.tsx` | Page (Resume Lab) | Client |
| 22 | `/dashboard/settings` | `src/app/dashboard/settings/page.tsx` | Page | Client, `<Suspense>` |

Proxied (non-file) routes provided by `next.config.js` rewrites: `/api/v1/:path*` and `/docs` (see 5.4).

Query parameters consumed by routes: `/login?next=&error=`, `/dashboard/applications?status=`, `/dashboard/submit?id=`, `/dashboard/emails?id=`, `/dashboard/interviews?id=`, `/dashboard/logs?run=`, `/dashboard/settings?tab=` and `?google=connected`. `/dashboard?welcome=1` is produced by registration but **not read** by any code.

---

### 5.1 Root layout — `src/app/layout.tsx`

- Fonts via `next/font/google` (all `subsets: ["latin"]`, `display: "swap"`):
  - `Dela_Gothic_One` `weight: "400"` → CSS var `--font-display`
  - `Space_Grotesk` → `--font-sans`
  - `JetBrains_Mono` → `--font-mono`
  - All three `.variable` classes are applied to `<html>`; `<body className="font-sans">`.
- `metadata`:
  - `title: { default: "HireFlow", template: "%s · HireFlow" }`
  - `description: "Swipe right on internships — your agent tailors, fills and applies."`
  - `manifest: "/manifest.webmanifest"`
  - `icons: { icon: [{ url: "/icon.svg", type: "image/svg+xml" }, { url: "/favicon.ico", sizes: "any" }], apple: "/apple-touch-icon.png" }`
- `viewport.themeColor`: `(prefers-color-scheme: light)` → `#f3eee9`; `(prefers-color-scheme: dark)` → `#1d1b1b`.
- `<html lang="en" suppressHydrationWarning>`.
- Provider tree (outer → inner): `ThemeProvider` (`attribute="class" defaultTheme="dark" enableSystem={false} storageKey="theme" disableTransitionOnChange`) → `TooltipProvider delayDuration={200}` → `ToastProvider` (renders sonner `<Toaster position="bottom-right" />` after children) → `MotionProvider` (`<MotionConfig reducedMotion="user">`) → `{children}`.
- Default theme is **ink (dark)**; theme stored in `localStorage["theme"]`; system theme is not followed.

### 5.2 Root template — `src/app/template.tsx`

`RootTemplate` wraps children in `RootFade` (re-mounted on every top-level navigation): `motion.div` `initial={{ opacity: 0 }}` → `animate={{ opacity: 1 }}`, `transition={{ duration: 0.35, ease: EASE_OUT }}` (`EASE_OUT = [0.22, 1, 0.36, 1]`); `initial={false}` when reduced motion is on.

### 5.3 Dashboard layout and template

- `src/app/dashboard/layout.tsx` → `<DashboardShell>{children}</DashboardShell>` (sidebar, header, WebSocket, service-worker registration — see Section 6 `dashboard-shell.tsx`).
- `src/app/dashboard/template.tsx` → `<PageTransition>{children}</PageTransition>`; re-mounted on every dashboard navigation: renders `RouteSweep` (a 3px signal-red bar, `fixed inset-x-0 top-0 z-[60]`, `scaleX: [0, 0.72, 1]`, `opacity: [1, 1, 0]`, `duration 0.75s`, `times [0, 0.55, 1]`, `ease "easeOut"`, `origin-left`; not rendered when reduced motion) plus a `motion.div` that fades/rises `initial {opacity: 0, y: 14}` → `{opacity: 1, y: 0}` in `0.42s` `EASE_OUT`.

### 5.4 `next.config.js`

| Setting | Value |
|---|---|
| `BACKEND_URL` | `process.env.BACKEND_URL \|\| "http://localhost:8000"` (compiled in at build time) |
| `reactStrictMode` | `true` |
| `output` | `"standalone"` |
| `poweredByHeader` | `false` |
| `experimental.proxyTimeout` | `15 * 60 * 1000` = 900 000 ms (15 min) — so slow local-LLM requests (resume parsing, Test AI) are not cut off by Next's default 30 s proxy timeout |
| `rewrites()` (BFF proxy) | `{ source: "/api/v1/:path*", destination: "${BACKEND_URL}/api/v1/:path*" }`, `{ source: "/docs", destination: "${BACKEND_URL}/docs" }` |
| `headers()` | for `source: "/:path*"`: `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `X-Frame-Options: SAMEORIGIN` |

Rationale (from comments): same-origin BFF so the httpOnly session cookie (`hireflow_session`) is first-party in every deployment topology. WebSockets are **not** proxied by these rewrites (see Section 7).

Related build/runtime files:
- `.env.example`: `BACKEND_URL=http://localhost:8000`; `NEXT_PUBLIC_WS_URL=ws://localhost:8000/api/v1/ws` (optional; falls back to polling).
- `Dockerfile` (HireFlow dashboard, Next.js standalone; built from repo root with `docker build -f frontend/Dockerfile --build-arg BACKEND_URL=http://api:8000 -t hireflow-frontend .`): three `node:20-alpine` stages (`deps` → `npm ci --no-audit --no-fund`; `build` with `ARG BACKEND_URL=http://api:8000`, `ARG NEXT_PUBLIC_WS_URL=`, `NEXT_TELEMETRY_DISABLED=1`, `npm run build`; `run` with `BACKEND_URL`, `NODE_ENV=production`, `PORT=3000`, `HOSTNAME=0.0.0.0`, non-root user `app`, copies `.next/standalone`, `.next/static`, `public`), `EXPOSE 3000`, `HEALTHCHECK --interval=30s --timeout=5s CMD wget -qO- http://127.0.0.1:3000/`, `CMD ["node", "server.js"]`.
- `postcss.config.js`: `{ plugins: { tailwindcss: {}, autoprefixer: {} } }`.
- `.eslintrc.json`: `{ "extends": ["next/core-web-vitals"] }`.
- `components.json` (shadcn): `style "new-york"`, `rsc true`, `tsx true`, tailwind config `tailwind.config.ts`, css `src/app/globals.css`, `baseColor "neutral"`, `cssVariables true`, aliases `@/components`, `@/lib/utils`, `@/components/ui`, `@/lib`, `@/hooks`, `iconLibrary "lucide"`.
- `tsconfig.json`: target `ES2020`, `strict`, `moduleResolution "bundler"`, `jsx "preserve"`, `paths { "@/*": ["./src/*"] }`, `allowJs false`.

### 5.5 `globals.css` design tokens

Header comment: "HireFlow design tokens — "ink" (dark, default) and "paper" (light). Charcoal surfaces, warm cream type, one signal red, hairline grid lines, square corners."

`@layer base` CSS variables (HSL triplets unless noted):

| Token | `:root` (paper / light) | `.dark` (ink / dark, default) |
|---|---|---|
| `--background` | `30 22% 94%` | `0 4% 11%` |
| `--foreground` | `0 6% 11%` | `0 22% 94%` |
| `--card` | `30 30% 97%` | `0 4% 12.5%` |
| `--card-foreground` | `0 6% 11%` | `0 22% 94%` |
| `--popover` | `30 30% 97%` | `0 4% 13%` |
| `--popover-foreground` | `0 6% 11%` | `0 22% 94%` |
| `--primary` | `356 75% 48%` | `356 75% 53%` |
| `--primary-foreground` | `0 100% 99%` | `0 100% 99%` |
| `--secondary` | `30 14% 88%` | `0 4% 17%` |
| `--secondary-foreground` | `0 6% 14%` | `0 18% 92%` |
| `--muted` | `30 14% 89%` | `0 4% 16%` |
| `--muted-foreground` | `0 4% 36%` | `0 6% 64%` |
| `--accent` | `30 16% 88%` | `0 4% 17%` |
| `--accent-foreground` | `0 6% 11%` | `0 22% 94%` |
| `--destructive` | `356 75% 46%` | `356 75% 53%` |
| `--destructive-foreground` | `0 0% 100%` | `0 0% 100%` |
| `--success` | `152 52% 30%` | `152 45% 52%` |
| `--success-foreground` | `0 0% 100%` | `0 5% 10%` |
| `--warning` | `30 90% 34%` | `38 92% 60%` |
| `--warning-foreground` | `0 0% 100%` | `0 5% 10%` |
| `--info` | `205 60% 38%` | `205 70% 66%` |
| `--info-foreground` | `0 0% 100%` | `0 5% 10%` |
| `--border` | `20 8% 78%` | `0 3% 26%` |
| `--line` | `0 5% 62%` | `0 5% 44%` |
| `--input` | `20 8% 70%` | `0 3% 32%` |
| `--ring` | `356 75% 48%` | `356 75% 53%` |
| `--radius` | `0rem` (square corners) | (inherits `0rem`) |
| `--noise-opacity` | `0.05` | `0.07` |
| `--series-1` (hex) | `#2b2727` | `#efe6e1` |
| `--series-2` | `#d52b37` | `#ee4450` |
| `--series-3` | `#3f8f74` | `#7fb8a4` |
| `--chart-grid` | `#ddd5cc` | `#2e2a2a` |
| `--chart-axis` | `#c3b9ae` | `#3d3838` |
| `--chart-muted` | `#6f6767` | `#9d9595` |

Base rules: `* { @apply border-border }`; `html { -webkit-tap-highlight-color: transparent }`; `body { @apply bg-background text-foreground antialiased; font-feature-settings: "ss01", "ss02" }`; `::selection { @apply bg-primary text-primary-foreground }`.

`@layer components`:
- `.noise::before` — film-grain overlay: `content ""`, `position: fixed; inset: 0; z-index: 0; pointer-events: none; opacity: var(--noise-opacity)`, background = inline SVG data URI (220×220, `feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='3' stitchTiles='stitch'`, `feColorMatrix values='0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 1.2 0'`). `.noise > * { position: relative; z-index: 1 }`. Used on landing `<main>`, auth `<main>`, dashboard shell root.
- `.label-caps` → `text-[11px] font-medium uppercase tracking-label` (0.16em).
- `.display` → `font-display uppercase leading-[0.95]`.
- `.brush` (relative, `isolation: isolate`) with `::before`/`::after` red strokes: `background: hsl(var(--primary)); transform: skewY(-9deg) rotate(-8deg); z-index: -1`; `::before { left: -3%; right: 2%; top: 36%; height: 24% }`; `::after { left: -12%; right: 34%; top: 84%; height: 21% }`.
- `.tag-pill` → `inline-flex items-center rounded-full border border-foreground/70 bg-background px-4 py-1.5 text-sm text-foreground`.

`@layer utilities`: `.scrollbar-thin { scrollbar-width: thin }`; `.prose-pre` → `whitespace-pre-wrap break-words text-sm leading-relaxed`; `.grid-lines` → `gap-px bg-border` with `.grid-lines > * { @apply bg-background }` (1px separators between grid cells).

### 5.6 `tailwind.config.ts`

- `darkMode: ["class"]`; `content: ["./src/**/*.{ts,tsx}"]`; `plugins: [tailwindcss-animate]`.
- `container: { center: true, padding: "1rem", screens: { "2xl": "1440px" } }`.
- `fontFamily`: `sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "Arial", "sans-serif"]`; `display: ["var(--font-display)", "var(--font-sans)", "ui-sans-serif", "system-ui", "sans-serif"]`; `mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"]`.
- `colors` (all `hsl(var(--x))`): `border`, `line`, `input`, `ring`, `background`, `foreground`, and `{DEFAULT, foreground}` pairs for `primary`, `secondary`, `destructive`, `success`, `warning`, `info`, `muted`, `accent`, `popover`, `card`.
- `borderRadius`: `lg: var(--radius)`, `md: calc(var(--radius) - 1px)`, `sm: calc(var(--radius) - 2px)`.
- `letterSpacing`: `label: "0.16em"`.
- `keyframes` / `animation`:

| Name | Keyframes | Animation |
|---|---|---|
| `fade-in` | from `{opacity 0, translateY(4px)}` to `{opacity 1, transform none}` | `fade-in 0.2s ease-out` (used by `TabsContent`) |
| `tunnel-drift` | `0%,100%: scale(1) rotate(0deg)`; `50%: scale(1.04) rotate(1.5deg)` | `tunnel-drift 14s ease-in-out infinite` (TunnelGrid) |
| `marquee` | `translateX(0)` → `translateX(-50%)` | `marquee 40s linear infinite` (landing source band) |
| `pulse-dot` | `0%,100%: opacity 1`; `50%: opacity 0.35` | `pulse-dot 1.6s ease-in-out infinite` (live dots) |
| `sheen` | `translateX(-100%)` → `translateX(400%)` | `sheen 1.8s ease-in-out infinite` (scan bar) |

Plus `tailwindcss-animate` utilities (`animate-in`, `fade-in-0`, `zoom-in-95`, `slide-in-from-*`) used by Radix overlays.

### 5.7 `public/` assets

| File | Content |
|---|---|
| `manifest.webmanifest` | `name "HireFlow"`, `short_name "HireFlow"`, `description "Swipe right on internships — your agent tailors, fills and applies."`, `start_url "/dashboard"`, `display "standalone"`, `background_color "#1d1b1b"`, `theme_color "#1d1b1b"`, icons: `/icon.svg` (`sizes "any"`, `image/svg+xml`, purpose `any`), `/icon-192.png` (`192x192`, `any`), `/icon-512.png` (`512x512`, `any`), `/icon-512.png` (`512x512`, `maskable`) |
| `sw.js` | Service worker (cache `hireflow-shell-v2`; see Section 7.7) |
| `icon.svg` | 512×512: `#1d1b1b` background, inset frame `#6f6767` (stroke-opacity 0.55, width 4), logo mark scaled 18×: cream bracket path `M2 1h7v4H6v10h3v4H2z` fill `#f2ecec` + red block `M11 7h3v6h-3z` fill `#e12d35` |
| `icon-192.png`, `icon-512.png`, `apple-touch-icon.png`, `favicon.ico` | Raster icons |

### 5.8 `package.json`

`name: "hireflow-dashboard"`, `version: "1.0.0"`, `private: true`.

Scripts: `dev: "next dev -p 3000"`, `build: "next build"`, `start: "next start -p 3000"`, `lint: "next lint"`, `typecheck: "tsc --noEmit"`.

Dependencies (30: 17 `@radix-ui/*` + 13 others):

| Package | Range | Package | Range |
|---|---|---|---|
| `@radix-ui/react-alert-dialog` | `^1.1.23` | `@radix-ui/react-tooltip` | `^1.2.16` |
| `@radix-ui/react-avatar` | `^1.2.6` | `class-variance-authority` | `^0.7.1` |
| `@radix-ui/react-checkbox` | `^1.3.11` | `clsx` | `^2.1.1` |
| `@radix-ui/react-dialog` | `^1.1.23` | `framer-motion` | `^13.4.6` |
| `@radix-ui/react-dropdown-menu` | `^2.1.24` | `lucide-react` | `^1.48.0` |
| `@radix-ui/react-label` | `^2.1.15` | `next` | `14.2.35` (exact) |
| `@radix-ui/react-popover` | `^1.1.23` | `next-themes` | `^0.4.6` |
| `@radix-ui/react-progress` | `^1.1.16` | `react` | `^18.3.1` |
| `@radix-ui/react-scroll-area` | `^1.2.18` | `react-dom` | `^18.3.1` |
| `@radix-ui/react-separator` | `^1.1.15` | `recharts` | `^2.15.4` |
| `@radix-ui/react-slider` | `^1.4.7` | `sonner` | `^2.0.8` |
| `@radix-ui/react-slot` | `^1.3.3` | `swr` | `^2.5.1` |
| `@radix-ui/react-switch` | `^1.3.7` | `tailwind-merge` | `^3.7.0` |
| `@radix-ui/react-tabs` | `^1.1.21` | `tailwindcss-animate` | `^1.0.7` |
| `@radix-ui/react-toggle` | `^1.1.18` | | |
| `@radix-ui/react-toggle-group` | `^1.1.19` | | |

DevDependencies (9): `@types/node ^20.19.43`, `@types/react ^18.3.31`, `@types/react-dom ^18.3.7`, `autoprefixer ^10.6.1`, `eslint ^8.57.1`, `eslint-config-next 14.2.35`, `postcss ^8.5.28`, `tailwindcss ^3.4.19`, `typescript ^5.9.3`.

---

### 5.9 `/` — Landing page (`src/app/page.tsx`)

Purpose: public marketing page. Server component; no API calls, no SWR. Wrapped `<main className="noise ...">` with a centered `max-w-[1440px]` bordered column.

Sections (in order):
1. **Header** — `Logo`; nav anchors `How it works` (`#how`), `Swipe` (`#swipe`), `Safety` (`#rules`) (md+), `Sign in` → `/login` (sm+), `ThemeToggle`, button link `Get started` → `/register`.
2. **Hero** — eyebrow with pulsing red dot (`animate-pulse-dot`) "Internship season is live"; `BrushHeadline lines={["Swipe right.", "We apply.", "Internships", "on autopilot"]}`; paragraph "HireFlow scans thousands of internships at startups and big tech, lets you keep or skip each one in a swipe, then tailors your resume, fills the form and applies — for every job you keep."; CTA `Start swiping` (size `xl`) → `/register`; round play button "See how it works" → `#how`; `TagPile` (md+, absolute bottom-right, `scale-[0.8]`, `xl:scale-100`); right column (lg+) `TunnelGrid` (animated).
3. **Stats row** (3 cells) — text logos `Greenhouse`, `Lever`, `Ashby`, `Workday`; overlapping avatar circles `GH`, `LV`, `AS`, `WD` + "4,000+" / "live internships, refreshed daily"; `Seal` + "Nothing is sent for a job you didn't keep — and eligibility is never guessed."
4. **Marquee band** (`bg-primary`) — `SOURCES` = `["Internshala", "Greenhouse", "Lever", "Ashby", "Workday", "LinkedIn", "Wellfound", "Indeed", "Simplify lists", "Career pages"]` rendered twice, separated by `✦`, `animate-marquee` (`motion-reduce:animate-none`).
5. **How it works** (`#how`) — heading "How it works", subtitle "Four steps, and only one of them needs you: the swipe."; four `STEPS`: `01 Scan`, `02 Swipe`, `03 Tailor & fill`, `04 Apply & track` (each with descriptive text).
6. **The loop** — eyebrow "The loop", heading "Always on. / Always tracking.", copy about Summer 2027 / Delhi NCR / "I Applied"; `PipelineMotion` motion graphic.
7. **Swipe preview** (`#swipe`) — eyebrow "Swipe Review", heading "Keep. Skip. / Repeat.", copy mentions arrow keys and "Keep 50 at once with one click"; checklist "Match score with strong and missing skills", "Visa sponsorship, location and term at a glance", "Undo any swipe until preparation starts"; static mock card stack (score `86`, "Ashby · Remote", "Software Engineer Intern", "Ramp · Summer 2027", tags `Python`, `React`, `SQL`, `Sponsors visas`, Skip/Keep buttons, `KEEP` stamp) over non-animated `TunnelGrid` (`opacity-40`).
8. **Rules** (`#rules`) — three cards with `ShieldCheck`: "You pick every job", "Never guesses eligibility", "Never invents experience".
9. **CTA** — "Your next internship is one swipe away" (internship in primary color) + `Create your agent` → `/register`.
10. **Footer** — `Logo`; "Self-hosted · your data stays on your server · MIT licensed".

Animations: CSS `animate-pulse-dot`, `animate-marquee`, `animate-tunnel-drift` (TunnelGrid), Framer Motion in `PipelineMotion`; hover transitions on step cells / play button.

### 5.10 `/login` and `/register` (`src/app/login/page.tsx`, `src/app/register/page.tsx`)

- `metadata.title`: `"Sign in"` (login) / `"Create account"` (register) → tab titles "Sign in · HireFlow" / "Create account · HireFlow".
- Each renders `<Suspense><AuthForm mode="login" | "register" /></Suspense>`.
- Behaviour (from `components/auth-form.tsx`):
  - SWR `GET /auth/config` → `{ google_enabled, registration_enabled }` (default SWR options).
  - Left panel (lg+): `TunnelGrid` (opacity 60), `Logo`, `BrushHeadline` — login: `["Welcome", "back.", "Your deck", "is waiting"]`; register: `["Build your", "agent.", "Then just", "swipe"]`; copy "Thousands of internships, one swipe each. Keep the ones you like — HireFlow tailors, fills and applies."; footer label "Nothing is sent for a job you didn't keep".
  - Right panel: header with `Logo` and switch link (`Create account` → `/register` or `Sign in` → `/login`); eyebrow "Sign in" / "Get started"; h1 "Welcome back" / "Create your account"; subtitle "Sign in to your HireFlow dashboard." / "Set up your internship agent in two minutes."
  - Form fields & client-side validation:
    - Register only: `Full name` (`id="name"`, `required`, `autoComplete="name"`).
    - `Email` (`type="email"`, `required`, `autoComplete="email"`).
    - `Password` (`type="password"`, `required`, `minLength={8}` on register only, `autoComplete` `current-password` / `new-password`).
  - Submit: login → `POST /auth/login {email, password}`; register → `POST /auth/register {email, password, full_name}`. Success: register → `router.replace("/dashboard?welcome=1")`; login → `router.replace(next)` where `next = ?next || "/dashboard"`. Error: `ApiError.message` or "Something went wrong" shown in `role="alert"` box.
  - `?error=` codes mapped: `google_oauth_failed` → "Google sign-in failed. Please try again."; `registration_disabled` → "Registration is disabled on this server."; `session_expired` → "Your session expired — sign in again."; other values shown verbatim.
  - If `google_enabled`: divider "or" + full-width link `Continue with Google` → `/api/v1/auth/google/login?next=<encoded next>` (plain browser navigation).
  - Footer: "No account? Create one" / "Already registered? Sign in".
  - Submit button label: "Sign in" / "Create account" with `ArrowUpRight`, `loading` spinner while submitting.

### 5.11 `/api/health` — BFF health route handler (`src/app/api/health/route.ts`)

- `export const dynamic = "force-dynamic"`; `GET()` only.
- Fetches `${process.env.BACKEND_URL || "http://localhost:8000"}/health/ready` with `cache: "no-store"` and `signal: AbortSignal.timeout(5000)` (5 s).
- Success path: `{ status: res.ok ? "ok" : "degraded", frontend: "ok", backend: <backend JSON> }` with HTTP `200` if backend ok else `503`.
- Exception path: `{ status: "degraded", frontend: "ok", backend: { error: String(err) } }` with `503`.
- Note: this is under `/api/health`, which the `/api/v1/:path*` rewrite does not match, so Next serves it.

### 5.12 Dashboard shell (applies to every `/dashboard/*` route)

See Section 6 `dashboard-shell.tsx` for full detail. Summary: sticky 248px sidebar (lg+) / 272px left `Sheet` on mobile with nav sections **Agent** (`Overview`, `Swipe Review` [badge = `to_review`], `Top companies`, `Ready to submit` [badge = `pending_approval`], `Applications`, `I Applied`, `All jobs`), **Inbox** (`Emails`, `Interviews`), **Insights** (`Analytics`, `Agent logs`), **Setup** (`Resume Lab`, `Settings`); footer "Applied today" meter + live indicator ("Live updates on" / "Polling for updates"); sticky header with breadcrumb `/ <label>`, `ScanIndicator`, "`{n}` to swipe" link, `NotificationBell`, `ThemeToggle`, account dropdown (`Settings`, `Resume Lab`, `Sign out`). SWR: `/auth/me`, `/agent/status`; WebSocket via `useWebSocket`; registers `/sw.js`. `<main className="flex-1 p-4 sm:p-6 lg:p-10">`.

### 5.13 `/dashboard` — Overview (`src/app/dashboard/page.tsx`)

Purpose: agent status at a glance, onboarding checklist, scan control, KPIs, approvals, interviews, activity.

Data / SWR keys:
| Hook / key | Options |
|---|---|
| `useAgentStatus()` → `/agent/status` | LIVE, but `refreshInterval` 1500 ms while a `scan` run is running |
| `useScan()` (→ `/agent/status`, `/agent/runs/{finishedId}`) | see Section 6 |
| `useOverview()` → `/analytics/overview` | LIVE |
| `useApplications({ status: "pending_approval", page_size: 5, sort: "match" })` → `/applications?status=pending_approval&page_size=5&sort=match` | LIVE |
| `useMe()` → `/auth/me` | default |
| Onboarding: `useIntegrations()` → `/users/me/integrations` | default |
| Onboarding: `useSWR("/users/me/field-mappings")` | default |

Mutations: `POST /agent/start-scan` (via `useScan().start`, body `{}`).

Sections:
1. `PageHeader` eyebrow "Dashboard", title "Overview", description `Last scan <timeAgo>` + ` · next <formatDateTime(next_scan_at)>` or "Your agent hasn't scanned yet."; action button: `Scan for jobs now` (icon `Radar`) or `Scanning {percent}%` while running; `loading` while starting/running; disabled when `!status.has_master_resume`.
2. `ScanProgressPanel` (live scan panel; hidden when idle).
3. `FocusStrip` ("Hunting for …") when `me` loaded.
4. **Onboarding card** "Get your agent ready" (hidden when all done) — description "`{completed} of 5 done — kept jobs only auto-submit once your eligibility answers are saved.`", big `%` and `Progress` bar; 5 numbered steps (links):
   - `01` "Upload your master resume" → `/dashboard/resume` (done: `status.has_master_resume`)
   - `02` "Set target roles & locations" → `/dashboard/settings?tab=preferences` (done: `target_roles.length > 0`)
   - `03` "Apply the Internships preset (mass apply)" → `/dashboard/settings?tab=mass-apply` (done: has any source/board-platform AND `sources.internship_lists` non-empty AND `platforms` includes `"internships"`)
   - `04` "Save work-authorization & visa answers" → `/dashboard/settings?tab=answers` (done: field mappings contain `work_authorization` and `requires_sponsorship`)
   - `05` "Connect Gmail & Calendar (optional)" → `/dashboard/settings?tab=integrations` (done: `integrations.google.connected`)
   Done steps show `CheckCircle2` + line-through.
5. **SwipeBand** — eyebrow "Swipe Review"; `count > 0`: red band "`{n} job is/jobs are` waiting for you" + `Start swiping` → `/dashboard/review`; else "Deck is empty. Go find more." + `Scan now` button (disabled without master resume). Background `TunnelGrid` (static, opacity 25).
6. **KPI grid** (5 `StatTile`s, `grid-lines`; skeletons while loading): "Awaiting your approval" (`totals.pending_approval`, hint link "Review now →" → `/dashboard/applications?status=pending_approval`), "Applications sent" (`totals.applied`, hint "`{applied_today} of {daily_limit ?? 25} today`"), "Response rate" (`{rates.response_rate}%`, hint "~N days to first reply" or "N responses"), "Interviews" (`totals.interviews`, hint "`{interview_rate}% of applications`"), "Offers" (`totals.offers`, hint "`{preparing + approved} more in the pipeline`").
7. **Card "Needs your approval"** (xl: 2 cols) — description "Filled out and paused — the agent needs an answer only you can give."; actions `Review & submit` → `/dashboard/submit?id=<first id>` (when items) and `View all` → `/dashboard/applications?status=pending_approval`; list of `ApplicationCard` each with action link `Review & submit` → `/dashboard/submit?id=<id>`; empty: `EmptyState` "Nothing waiting for review" (description mentions preparing count).
8. **Card "Upcoming interviews"** — "Synced to Google Calendar with prep notes"; items link `/dashboard/interviews?id=<id>`; empty "No interviews scheduled yet."
9. **Card "Activity — last 30 days"** — `TimelineChart` (overview.timeline) with chart/table toggle.
10. **Card "Recent agent runs"** — link `Logs` → `/dashboard/logs`; up to 6 runs linking `/dashboard/logs?run=<id>`; status dot (completed `bg-success`, failed `bg-primary`, else `animate-pulse-dot bg-warning`); scan runs show "`{jobs_discovered} new · {jobs_matched} scored`".

Animations: page template transition; `AnimatedNumber` count-ups in `StatTile`; `ScanProgressPanel` height/opacity; `FocusStrip` radar ring; `animate-pulse-dot`. Forms: none. Keyboard shortcuts: none.

### 5.14 `/dashboard/review` — Swipe Review (`src/app/dashboard/review/page.tsx`)

Purpose: Tinder-style deck of scored jobs; keep / skip / undo / "I Applied"; bulk keep; filters.

State: `filters = { jobType: "all", remote: false, q: "" }`; search input debounced **350 ms** into `filters.q`; `decided` set, `front` (cards restored by undo), `history` (last **50** swipes), `stats`, `busy`, `bulkScore` (default **60**), `bulkPreviewScore` (default 60, updated on slider commit).

SWR keys:
- `queueKey(filters)` = `/review/queue?limit=30[&job_type=<internship|full-time>][&remote=true][&q=<q>]` — `{ revalidateOnFocus: false }`. Deck keeps first-seen order (refetches append, never reshuffle); filters change resets order/front/decided. Auto top-up: when `deck.length < 5` and the last page returned ≥ 30 items → `mutate()`.
- Preview: `queueKey(filters, 1, bulkPreviewScore)` = `/review/queue?limit=1&...&min_score=<n>` — `{ revalidateOnFocus: false }`; `matching` is the bulk count.
- `useAgentStatus()` (for refresh), `useScan()`.

API calls:
| Action | Call |
|---|---|
| Keep / Skip a card | `POST /review/{application_id}` `{ decision: "keep" \| "skip" }` → `{ stats }`; on error card is restored and toast "Could not {decision} this job" |
| Undo | `POST /review/{application_id}/undo` → `{ card, stats }`; card re-inserted at front; error toast "Can't undo that one" |
| I Applied (top card) | `POST /applications/{application_id}/mark-applied`; card flies up; toast "Tracking {company}" / "Moved to Applied. You'll get updates on Gmail and here whenever they reply." |
| Bulk | `POST /review/bulk` `{ decision, min_score, job_type (omitted for "all"), remote (true or omitted), q (or omitted) }` → `{ count, stats }`; toast "Kept N jobs" (desc "They're being tailored, filled and submitted." if auto-submit else "They're being prepared for your review.") / "Skipped N jobs"; error "Bulk action failed" |
| Auto-submit switch | `PUT /users/me/preferences` `{ preferences: { auto_submit_kept: <bool> } }` then `mutate()` |
| Fetch full description | `POST /review/{application_id}/details` → fresh `ReviewCard`; replaces card in deck and in SWR cache (`mutate(..., false)`) |
| Scan | `useScan().start()` → `POST /agent/start-scan {}` |

UI sections:
1. `PageHeader` eyebrow "Mass apply", title "Swipe Review", description "Every job that passed your filters, best matches first. Keep it and the agent tailors, fills and applies. Skip it and it's gone. Nothing is skipped for you."; actions: outline `Scan for more` (or `Scanning {n}%`), ghost link `Applications` → `/dashboard/applications`.
2. `ScanProgressPanel`.
3. Stats strip (4 `StatCell`s with `AnimatedNumber`): "Left to swipe" (accent), "Kept today", "Skipped today", "Kept all time".
4. No-master-resume banner: "Upload your master resume before keeping jobs — every application is tailored from it." + `Upload resume` → `/dashboard/resume` (Keep is disabled while no master resume).
5. **Deck** (`h-[600px] sm:h-[640px]`, `max-w-[560px]`): skeleton while loading; empty → `EmptyState` "No jobs match these filters" / "You're all caught up" with `Scan now` and `Mass-apply settings` → `/dashboard/settings?tab=mass-apply`; else up to 2 `DeckShadowCard`s behind the draggable `SwipeCard`.
6. Controls: round `Undo` icon button (aria "Undo last swipe (Z)", disabled without history), `Skip` (outline, xl), `Keep` (primary, xl); ghost `I Applied to this myself`; hint line "Drag the card, or use ← skip · → keep · A I applied · Z undo".
7. Aside cards:
   - "When I keep a job" — `Switch` "Apply automatically" (bound to `settings.auto_submit_kept`, default `true`).
   - "Keep in bulk" — `Slider` "Minimum score" `min 0 max 100 step 5`; button `Keep {matching} jobs ≥ {bulkPreviewScore}` (disabled if 0 matching or no resume); outline `Skip everything filtered` (disabled if `remaining` is 0).
   - "Filter the deck" — search input (placeholder "Company, role or city"); `ToggleGroup type="single"` with items `All` (`all`), `Intern` (`internship`), `Full-time` (`full-time`); `Switch` "Remote only"; "`{matching}` jobs match these filters."

Keyboard shortcuts (window `keydown`, ignored when target is `INPUT`, `TEXTAREA` or contentEditable):
| Key | Action |
|---|---|
| `ArrowRight` | keep (fling right) |
| `ArrowLeft` | skip (fling left) |
| `z`, `Z`, `Backspace` | undo |
| `a`, `A` (without Meta/Ctrl) | I Applied |

Gestures/animations: `SwipeCard` horizontal drag (threshold 120 px or |velocity| > 700 → decide; fling 0.28 s; spring back stiffness 420 damping 32; KEEP/SKIP/APPLIED stamp opacity transforms; rotate ±12° over ±320 px; fly-up 0.42 s for I Applied); shadow cards `transition-transform duration-300`; `AnimatedNumber` stats.

### 5.15 `/dashboard/top-companies` — Top companies (`src/app/dashboard/top-companies/page.tsx`) — present in code, not in expected list

Purpose: internships at big tech / product / startups / AI companies with company-verification badges.

SWR: `/jobs/top-companies[?tier=<tier>][&q=<q>]` (key has no `?` when no params) — default options; `useScan()`.

API calls: `POST /agent/start-scan { platforms: ["top_companies"] }` (via `scan.start(["top_companies"])`); per-row Keep: `POST /review/{application_id} { decision: "keep" }` (toast "Kept: {company}" — verified: "The agent prepares and applies to it (verified company)." else "The agent prepares it; it waits in Ready to submit for your OK."; error "Couldn't keep it"); `CompanyBadge` → `POST /jobs/company-trust`.

UI:
1. `PageHeader` eyebrow "Mass apply", title "Top companies", description "Internships at big tech, product-based companies, renowned Indian and global startups and AI companies. Every company is checked: only verified ones are applied to automatically."; action `Scan top companies` (or "Scanning…"; disabled while scanning).
2. `ScanProgressPanel`.
3. Tier tabs (`role="tablist"`, buttons `role="tab"`): `All` (count `data.total`) followed by `data.tiers` (`{key, label, count}`; tier keys `big_tech`, `product`, `startup_india`, `startup_global`, `ai`); search input (placeholder "Company, role or city").
4. List of `JobRow`s: `JobMatchBadge sm`, company + `CompanyBadge` + `YearFitTag`, role (display font), location / "Remote" / "found {timeAgo}"; right: `StatusBadge`, `Keep` (only for statuses `discovered`, `matched`), `Open` → `/dashboard/applications/{id}` (other non-skipped statuses), `Posting` external link.
5. Empty state "Nothing here yet" / "No top-company internships yet" (with Scan button: "Scan {tracked || "100+"} renowned companies' own job boards (and LinkedIn for the ones with their own career sites).").
6. Catalog toggle "Show/Hide the {tracked} companies the agent tracks" (`aria-expanded`) → per-tier lists joined with " · ". If `!scan_top_companies`: note linking `Settings` ("Search top companies in every scan").

Animations: `ScanProgressPanel`; page transition. No keyboard shortcuts.

### 5.16 `/dashboard/submit` — Ready to submit (`src/app/dashboard/submit/page.tsx`)

Purpose: review sheet for filled-but-unsubmitted applications; confirm/fix each prefilled row, then submit with one click; or apply manually / via Internshala bot.

SWR: `useSubmitQueue()` → `/applications/review-queue?limit=100` `{ refreshInterval: 30000, revalidateOnFocus: false }`; `useAgentStatus()`.

Navigation state: starts at `?id=`; if the id isn't in the queue → toast "That application isn't waiting for you anymore" (desc "Showing the next one in the queue." when items exist; clears URL if empty). Current item id is kept in the URL via `window.history.replaceState(null, "", "/dashboard/submit?id=<id>")`. Counter "`{index+1}` of `{count}`".

Row model: `RowStatus = "pending" | "editing" | "confirmed"`; editable kinds `profile`, `question`, `cover_letter` (resume/file rows are informational). A row "needs you" when `flagged` or required+empty+editable. Per-application sheet state is kept per item id.

API calls:
| Action | Call |
|---|---|
| Submit | `POST /applications/{id}/submit` `{ rows: [{key, value}] (all rows except cover_letter), cover_letter: <value or undefined> }` → `DirectSubmitResponse` (`next_id`); toast "Submitting to {company}" / "The agent is filling the form with exactly what you checked and pressing Submit. The confirmation lands in Applications."; on 409 → `mutate()` |
| Apply with the bot | `POST /applications/{id}/bot-apply` → `DirectSubmitResponse`; toast "The bot is applying to {company}"; error "The bot couldn't start"; 409 → `mutate()` |
| I Applied (blocked items) | `IAppliedButton` → `POST /applications/{id}/mark-applied` |
After submit/apply the item is removed locally (`done` set), next item shown (server `next_id` preferred), `mutate()` queue and status.

UI:
1. `PageHeader` eyebrow "Mass apply", title "Ready to submit", description "The agent filled these forms and stopped short of Submit. Say yes or no to each prefilled item, fix anything that's wrong right here, then send it with one click."; action ghost link `Swipe Review`.
2. Empty: `EmptyState` "Nothing waiting" + `Go to Swipe Review`.
3. Attention counter "`{n}` item(s) need(s) you" (warning).
4. Card (`AnimatePresence mode="wait"`): header with "via {Internshala | platform label | "the company site"} · filled {timeAgo}", role, company, location, `CompanyBadge`, `Open posting` (apply_url), `Full details` → `/dashboard/applications/{id}`, big match score (primary ≥ 70), form screenshot thumbnail (click → zoom modal "Filled form").
5. Blocker banner (posting you must apply to yourself): "`{blocker}` Everything below is ready to copy over." + bot fix link (`BOT_FIX`: `bot_off` → "Turn on the bot", `not_synced` → "Sync your Internshala login", `expired` → "Sync your Internshala login again"; link `/dashboard/settings?tab=integrations`). Otherwise manual-review reason line.
6. Rows (`<ol aria-label="Prefilled items">`): label + required `*`, badges `profile`, `{NN}% sure` (flagged), `edited`; value (cover letter in serif, clamped), note in warning, "Uploaded by the agent. Shown for your information." for files. Buttons: `Correct` (title "Correct (Y)", disabled when required & empty) and `Fix` (title "Fix (N)") or `Open PDF`. Read-only mode (blocker): `Copy` button ("Copied" for 1600 ms; clipboard failure toast "Couldn't copy") or `Open PDF`. Confirmed rows collapse into a line with a green check, value / "N words" / "Left blank", `Undo`.
7. Row editor (`RowEditor`): `Select` when the row has options (adds current value option if not in list, placeholder "Select…"); `Textarea` for long text (cover letter `min-h-[320px] font-serif`, else `min-h-[120px]`; long = cover letter, `type === "textarea"`, or value > 120 chars); otherwise `Input` (`type="date"` when `row.type === "date"` and value empty or `YYYY-MM-DD`; `inputMode` email/tel/numeric). Buttons `Save`, `Cancel`; hint "Ctrl + Enter saves" (long text) or "Enter saves" · "Esc cancels".
   Validation: saving an empty required row sets error "This one is required." (`role="alert"`); confirming a required empty editable row opens the editor instead. Edited flag = value differs from prefilled.
8. Shortcut hint line (sm+): blocker → "J/K move · S skip [· B apply with the bot]"; normal → "Y correct · N fix · J/K move · A confirm all · Enter submit · S skip".
9. Sticky footer: blocker → `Skip for now`, `IAppliedButton` (lg, outline), `Apply on {siteName}` (external), and `Apply with the bot` (when bot ready) or bot fix link; normal → "Checked" progress bar (`{checked} of {total} checked`, green when all), `Confirm all` (disabled when all checked), `Skip for now`, `Submit application` (disabled until all checked and not editing; title "Submit application (Enter)" / "Check every item first").
10. `Confirm all` confirms all pending non-flagged rows; if some remain → toast "`N` items need you" / "Flagged and empty required items are never confirmed for you." and focuses the first.
11. `Skip` with a single item → toast "This is the only one waiting".

Keyboard shortcuts (window `keydown`; ignored when zoom modal open, any of Meta/Ctrl/Alt pressed, or focus in `INPUT`/`TEXTAREA`/`SELECT`/contentEditable):
| Key | Action |
|---|---|
| `j` or `ArrowDown` | focus next row |
| `k` or `ArrowUp` | focus previous row |
| `y` | confirm focused row (not on blocker items) |
| `n` | open Fix editor (not on blocker items) |
| `a` | confirm all (not on blocker items) |
| `s` | skip to next application |
| `b` (no repeat) | apply with the bot (when bot ready) |
| `Enter` (no repeat; not on BUTTON/A; all checked; not blocker) | submit |
Row editor: `Escape` cancels; `Enter` saves in `INPUT`/`SELECT`, `Ctrl/Cmd+Enter` saves in textarea.

Animations: card variants — `enter {opacity 0, y 18}`; `center {opacity 1, x 0, y 0}` 0.34 s `EASE_OUT`; exit "submit" `{opacity 0, y -56, scale 0.98}` 0.3 s ease `[0.4, 0, 1, 1]`; exit "skip" `{opacity 0, x -72}` 0.24 s; reduced motion: opacity only (0.12 s). Confirmed-row check pops `scale 0.4→1, opacity 0→1` in 0.22 s. Focus scrolls row into view (`smooth` unless reduced). Progress bar `transition-[width] duration-300`.

### 5.17 `/dashboard/applications` — Applications list (`src/app/dashboard/applications/page.tsx`)

SWR: `useApplications({ status, q, sort, page, page_size: 20 })` → `/applications?[status=<csv>&][q=<q>&]sort=<sort>&page=<n>&page_size=20` (LIVE).

UI:
- `PageHeader` title "Applications", description "Every application the agent has prepared, submitted or tracked. Applied somewhere yourself? Click “I Applied” on it and it's tracked too."; action link `I Applied[ · {self_applied_total}]` → `/dashboard/applied`.
- Filter pills (`aria-pressed`; selecting resets page and `router.replace("/dashboard/applications[?status=<key>]")`; initial from `?status=`), each with a count summed from `data.counts`:
  | Key | Label | Statuses |
  |---|---|---|
  | `all` | All active | (none) |
  | `pending_approval` | Needs approval | `pending_approval` |
  | `in_progress` | In progress | `preparing,approved` |
  | `applied` | Applied | `applied,acknowledged` |
  | `interviewing` | Interviewing | `screening,interview,assessment,final_round` |
  | `offers` | Offers | `offer,accepted` |
  | `closed` | Closed | `rejected,withdrawn,failed` |
- Search input "Search company or role…" (resets page). Sort `Select`: `updated` "Recently updated" (default), `match` "Best match", `created` "Newest", `company` "Company A–Z".
- List of `ApplicationCard` in `Stagger` (re-keyed `${filter}-${page}`); 5 skeletons while loading; empty "No applications here" / "Run a scan from the Overview page, or add a job by URL on the Jobs page."
- Pagination when `total > 20`: "{total} applications", `Previous` / `Next`.
Animations: `Stagger`/`StaggerItem` (0.05 s stagger, y 12 → 0, 0.38 s). Cards hover-lift.

### 5.18 `/dashboard/applications/[id]` — Application detail (`src/app/dashboard/applications/[id]/page.tsx`)

SWR: `useApplication(id)` → `/applications/{id}` (LIVE, 15 s). Local editable copies of `cover_letter` and `custom_answers` (synced from server while not dirty).

API calls:
| Action | Call | Success toast |
|---|---|---|
| Save edits | `PATCH /applications/{id}` `{ cover_letter, custom_answers }` | "Changes saved" |
| Approve (from `ApprovalModal`) | `POST /applications/{id}/approve` `{ cover_letter, custom_answers }` | "Approved — the agent is submitting your application" |
| Skip | `POST /applications/{id}/skip` | "Skipped" |
| Update status | `POST /applications/{id}/status` `{ status }` | "Status updated" |
| Re-fill form | `POST /applications/{id}/restage` | "Re-filling the form" |
| I Applied | `POST /applications/{id}/mark-applied` (IAppliedButton) | "Tracking {company}" |
Errors: toast "Action failed" + message. After each action `mutate()`.

Header: back link "Applications"; `JobMatchBadge size="lg"`; role (display), `StatusBadge`, `SelfAppliedTag` if self-applied; company, location (+ " · Remote"), salary, "via {platform}"; links `Job posting`, `Application form` (if different). Actions:
- `IAppliedButton` (size default) when status ∈ before-applied set.
- If `reviewable` (status ∈ `pending_approval`, `failed`, `matched`): `Save edits` (only when dirty), `Skip`, `Review & submit` → `/dashboard/submit?id=<id>` (only `pending_approval`), `Review & approve` (opens `ApprovalModal`).
- Else if status not `approved`/`preparing`: `Select` "Update status…" with `MANUAL_STATUSES` = `applied, acknowledged, screening, interview, assessment, final_round, offer, accepted, rejected, withdrawn` (labels from `STATUS_LABELS`).
Banners: `preparing` → spinner "The agent is tailoring your resume, writing the cover letter and filling out the form…"; `approved` → "Approved — submitting now. {notes}"; manual review (reviewable) → "Needs your attention" + reason + `Re-fill form` + `IAppliedButton`; `applied` with confirmation → "Submitted {datetime} · confirmation #{n}".

Tabs (`defaultValue="review"`, exact trigger labels):
| Value | Label | Content |
|---|---|---|
| `review` | **Filled form** | "Form screenshot" card (description "Filled {datetime} — not submitted" or "The form hasn't been filled yet"; image links to full size; optional "Confirmation page" image) + "Fields" card ("{n} filled · {m} need input"; per field icon filled/unmapped/blank, label, required `*`, value or "Needs your input" / "Left blank (optional)") |
| `resume` | **Tailored resume** | iframe of `tailored_resume_pdf_url` (h 720px) + `PDF` download; "What changed" list (non-`[guard]` entries) and "Truthfulness guard" box listing `[guard]` entries; fallback text "Your original resume file is sent unchanged (Settings › Mass apply › Resume to send)." / "No tailored resume yet." |
| `cover` | **Cover letter** | Editable `Textarea` (`min-h-[420px] font-serif`), disabled when not reviewable; word count in description |
| `answers` | **Answers** (with a warning dot when any answer `needs_user_review`) | Each question: badges `Review`, `{confidence}%`, `{source}`; `Select` when options exist else `Textarea`; editing clears `needs_user_review` and marks dirty |
| `match` | **Match analysis** | "Score breakdown" (method `llm` → "Evaluated by Claude" else "Heuristic evaluation"; "each criterion scored 0–20"; bars for `Skills`, `Experience`, `Industry`, `Location`, `Compensation`) + "Skills" (Strong matches / Missing / gaps) |
| `job` | **Job description** | job type · experience · posted · apply-by; description (`prose-pre`) |
| `activity` | **Activity** | `StatusTimeline` + "Emails & interviews" (links to `/dashboard/interviews?id=` and `/dashboard/emails?id=`) + "Last error" box |

Forms/validation: see `ApprovalModal` (Section 6) — approve disabled until the confirmation checkbox is ticked and no required answer is empty. Animations: `TabsContent` `animate-fade-in`; I Applied burst. No keyboard shortcuts.

### 5.19 `/dashboard/applied` — I Applied (`src/app/dashboard/applied/page.tsx`)

Purpose: jobs you applied to yourself; progress tracking; manual logging; progress e-mail.

SWR: `useApplications({ applied_by: "me", status, q, page, page_size: 20, sort: "updated" })` → `/applications?applied_by=me[&status=<csv>][&q=<q>]&page=<n>&page_size=20&sort=updated` (LIVE); `useMe()`.

API calls: `POST /users/me/progress-report` → `{ sent }` (toasts "Progress report sent" / "Check your Gmail (and Discord/Slack if connected)." or "Nothing to report yet" / "Mark a job with “I Applied” first."); `POST /applications/{id}/status` `{ status, notes: "Updated from I Applied" }` (toast "{company}: {label}"); `POST /applications/manual` (Log dialog). After changes: `mutate()` + `useRefreshTracking()`.

UI:
- `PageHeader` eyebrow "Tracked by you", title "I Applied"; description mentions Gmail, Discord/Slack and, unless `progress_digest` is `off`, "a {daily|weekly} progress e-mail at about 8 PM"; actions `Progress e-mail` (outline), `Log an application`.
- "Your progress" section: `TrackingLine` motion graphic (md+) and 4 `StageTile`s — `Applied` (total self-applied; "everything you applied to"), `Heard back` (statuses acknowledged, screening, assessment, interview, final_round, offer, accepted, rejected), `Interviewing` (screening, assessment, interview, final_round, offer, accepted), `Offer` (offer, accepted); each with "% of your applications" meter.
- Filter pills: `all` "All" (count = total), `waiting` "Waiting for a reply" (`applied,acknowledged`), `process` "In process" (`screening,assessment,interview,final_round`), `offers` "Offers" (`offer,accepted`), `closed` "Closed" (`rejected,withdrawn`).
- Search "Search company or role…".
- `TrackedCard` list (Stagger): role link, company, location, "applied {date} · {N days ago|today}"; `StatusBadge`; `Select` "Update status…" with `acknowledged, screening, assessment, interview, final_round, offer, accepted, rejected, withdrawn` minus current; `ProgressRail` (stages short labels `Applied`, `Replied`, `Interview`, `Offer`; closed statuses grey half-step); follow-up nudge when waiting ≥ **7** days: "No reply after {n} days — a short, polite follow-up often helps", else "Watching your inbox for replies"; links `Posting`, `Details`.
- Empty state "Nothing matches" / "Nothing here yet" (+ `Log an application`, `Browse jobs` → `/dashboard/jobs`).
- Pagination when `total > 20`.
- **Log dialog** (`Modal` "Log an application"): fields `Company` (placeholder "Zomato"), `Role` ("SDE Intern"), `Link to the posting (optional)` (`type="url"`), `Location` ("Gurugram, Haryana"), `Applied on` (`type="date"`, default today, `max=today`), `Type` select (`internship` default, `full-time`, `part-time`, `contract`), `Notes (optional)` textarea. Validation: `Track it` disabled until company and role are non-blank. Body: `POST /applications/manual { company_name, role_title, url: trimmed || null, location: trimmed || null, applied_on: value || null, job_type, notes: trimmed || null }`; toast "Tracking {company}" / "Added to I Applied. You'll get updates on Gmail and here."

Animations: `StageTile` meter `scaleX 0 → share` 0.9 s, delay `0.15 + index*0.08`, `EASE_OUT`; `AnimatedNumber`; `TrackingLine` pulse (`left: -10% → 100%`, 3.2 s, repeat ∞, easeInOut, repeatDelay 0.6); `ProgressRail` `scaleX` 0.8 s delay 0.2; `Stagger`; card hover-lift.

### 5.20 `/dashboard/jobs` — All jobs (`src/app/dashboard/jobs/page.tsx`)

SWR: `/jobs?sort=<sort>&page=<n>&page_size=25[&q=][&platform=][&remote=][&min_score=]` with `{ keepPreviousData: true }`; dialog: `/jobs/{jobId}` (default options).

API calls: `POST /jobs/{id}/prepare` (toast "Preparing application" / "Tailoring your resume and filling the form. You'll be notified when it's ready."), `POST /jobs/{id}/evaluate` (toast "Match re-evaluated"), `POST /jobs/import { url, prepare }` (toast "Imported: {role}" / "Match score {n}"; error "Import failed"), `IAppliedButton` mark-applied, `CompanyBadge` company-trust.

UI: `PageHeader` "Discovered jobs" / "Everything the agent found, scored against your master resume and preferences." + `Add job by URL`. Filters: search "Search title, company, location…"; `Source` select (`All sources` + `linkedin, indeed, glassdoor, wellfound, greenhouse, lever, ashby, workday, custom` with `PLATFORM_LABELS`); `Location` (`Any location`, `true` "Remote only", `false` "On-site / hybrid"); `Minimum match score` (`Any score`, `80` "80+", `60` "60+", `40` "40+"); `Sort jobs` (`match` "Best match" default, `recent` "Recently found", `posted` "Recently posted", `company` "Company A–Z"). Filter changes reset page to 1. List (`Stagger as="ul"`, re-keyed by sort/page/filters; dimmed while revalidating): `JobMatchBadge sm`, role, company, `CompanyTag`, location, salary, job type, platform/Easy Apply/Remote, posted/found date, `StatusBadge`, `IAppliedButton` (md+, before-applied statuses). Pagination when `total > 25`. Empty: "No jobs yet" + `Add job by URL`.
- **Job dialog** (`Modal`, `max-w-3xl`): score badge, `CompanyBadge`, status, reasoning ("Not evaluated yet."), up to 20 skill badges, description; footer `Posting`, `Re-evaluate`, `IAppliedButton`, `Prepare application` (statuses `discovered, matched, skipped, failed`) or `Open application`.
- **Import dialog** "Add a job by URL" ("Paste any Greenhouse, Lever, Ashby, Workday, LinkedIn or company careers-page link."): `Job posting URL` input; checkbox (default checked) "Tailor resume, write cover letter and fill the form right away (you still approve before submission)". Validation: `Import job` disabled unless URL starts with `"http"`.
Animations: `Stagger`. No shortcuts.

### 5.21 `/dashboard/emails` — Recruiter emails (`src/app/dashboard/emails/page.tsx`)

SWR: `/communications?page_size=50[&intent=<intent>][&action_required=true]` `{ refreshInterval: 30000 }`; detail `/communications/{id}` (default); `useIntegrations()`.

API calls: `POST /agent/check-email` (toast "Checking Gmail…" / "New recruiter e-mails will appear shortly."; `mutate()` after **5000 ms**); `POST /communications/{id}/draft { body }` ("Draft saved to Gmail"); `POST /communications/{id}/send { body }` after `window.confirm("Send this reply from your Gmail now?")` ("Reply sent"); `PATCH /communications/{id} { action_taken: !action_taken }` ("Marked as done" / "Marked as open").

UI: `PageHeader` "Recruiter emails" (description "Monitoring {email} · checked {timeAgo}" or "Connect Gmail in Settings to monitor recruiter replies."); `Check now` button when Gmail connected. Filters: intent `Select` (`All intents`, `interview_invite`, `offer`, `assessment`, `info_request`, `follow_up`, `rejection`, `acknowledgment`, `generic` — title-cased) and toggle button `Action required`. Two-column list/detail: list items show sender (bold when action required & open), time, subject, intent badge (tones: offer/interview_invite success, assessment primary, rejection danger, info_request warning, follow_up info, acknowledgment/generic muted), `Action` badge, snippet; selected item ring. Detail card (sticky): intent / urgency / confidence badges, subject, sender, linked application, extracted details grid, body, "Suggested reply" textarea (prefilled from `suggested_reply`, placeholder "No reply needed for this e-mail."), buttons `Save as Gmail draft`, `Send reply` (both disabled when reply blank), `Mark done` / `Reopen`; note "A draft reply is waiting in your Gmail drafts." Initial selection from `?id=`. Empty: "No recruiter e-mails yet".

### 5.22 `/dashboard/interviews` — Interviews (`src/app/dashboard/interviews/page.tsx`)

SWR: `/interviews?upcoming=true`, `/interviews?upcoming=false`, detail `/interviews/{id}` (all default options); Add dialog: `useApplications({ status: "applied,acknowledged,screening,interview,assessment,final_round", page_size: 100 })` (LIVE).

API calls: `POST /interviews { application_id, scheduled_at: ISO, duration_minutes, interview_type, meeting_link || null, physical_location || null, timezone: <browser IANA tz> }` (toast "Interview added" / "Prep notes generated and synced to your calendar."); `POST /interviews/{id}/prep` ("Prep notes regenerated"); `PATCH /interviews/{id} { outcome }` ("Outcome saved"); `PATCH /interviews/{id} { feedback }` ("Debrief saved").

UI: `PageHeader` "Interviews" / "Auto-created from recruiter e-mails, synced to Google Calendar with 24h and 1h reminders." + `Add interview`. Left list sections "Upcoming" ("None scheduled.") and "Past"; first upcoming auto-selected; `?id=` preselects. Detail card: type badge, outcome badge (passed success / failed danger / else muted), "{role} @ {company}", datetime · duration · timezone, `Join {platform}` (meeting link), location, `Calendar` link, `Regenerate prep`.
Detail tabs (`defaultValue="prep"`): **`Prep notes`** (`prep`), **`Likely questions`** (`questions`, numbered question + answer outline), **`Company`** (`company`, company research), **`Outcome`** (`outcome`: buttons `Pending`, `Passed`, `Failed`, `Rescheduled`, `Cancelled` from values `pending, passed, failed, rescheduled, cancelled`; feedback textarea "How did it go? What were you asked?"; `Save debrief`).
**Add interview** modal ("Creates a calendar event with AI prep notes."): `Application` select (`Select…` + "{company} — {role}"), `Date & time` (`datetime-local`), `Duration (min)` (number, `min=5`, default 60), `Type` (`phone_screen, video_call` (default), `technical, behavioral, panel, onsite, take_home, pair_programming, other`), `Meeting link` (placeholder "https://zoom.us/j/…"), `Location (on-site)`. Validation: `Add interview` disabled until application and date/time are set.

### 5.23 `/dashboard/analytics` — Analytics (`src/app/dashboard/analytics/page.tsx`)

SWR: `useOverview(range)` → `/analytics/overview` or `/analytics/overview?days=<7|30|90>` (LIVE).

UI: `PageHeader` "Analytics" / "How your search is performing — responses, interviews and what's working." Range pills (`aria-pressed`): `Last 7 days` (7), `Last 30 days` (30), `Last 90 days` (90), `All time` (undefined, default). Content dims (`opacity-60`) while reloading.
- 5 `StatTile`s: "Applications sent" (hint "{total} tracked in total"), "Response rate" (`%`, "{responses} responses"), "Interview rate" (`%`, "{interviews} reached interviews"), "Offer rate" (`%`, "{offers} offers from interviews"), "Time to first response" ("{n} days" or "—", hint "Average, submitted → first reply").
- "Daily activity" / "Last 30 days" — `TimelineChart height={300}`.
- "Match score distribution" — `MatchHistogram`.
- "Pipeline by status" — `StatusBreakdown`.
- "Platform effectiveness" table: Source, Found, Applied, Response, Interview.
- "Keywords that get callbacks" ("needs ≥ 2 applications each") table: Keyword, Applications, Callbacks, Rate.
Animations: `AnimatedNumber` in tiles; Recharts default animations.

### 5.24 `/dashboard/logs` — Agent logs (`src/app/dashboard/logs/page.tsx`)

SWR: `/agent/runs?page_size=50[&run_type=<scan|prepare|apply>]` `{ refreshInterval: 10000 }`; detail `/agent/runs/{id}` with `refreshInterval: d => d?.status === "running" ? 3000 : 0`.

UI: `PageHeader` "Agent logs" / "An audit trail of every scan, preparation and submission the agent performed."; `Select` "Run type": `All runs`, `scan` "Scans", `prepare` "Preparations", `apply` "Submissions". List buttons (status dot completed success / failed destructive / else warning, run type, status, timeAgo); `?run=` preselects. `RunDetail` card: "{Type} run", started · duration ("running") · "triggered by {trigger}", badges discovered / matched / prepared / submitted / errors; monospace log (`max-h-[560px]`) with local time, level (error destructive, warning warning), message; "No log entries." Empty: "No agent runs yet" / "Start a scan from the Overview page."; "Select a run to see its log".

### 5.25 `/dashboard/resume` — Resume Lab (`src/app/dashboard/resume/page.tsx`)

SWR: `/resumes/master` `{ shouldRetryOnError: false }`; `/resumes?tailored=true`; `useIntegrations()`.

API calls: upload `POST /resumes/upload` (multipart `FormData`: `file`, `is_master="true"`; toast "Resume imported" with "Parsed with Claude — please review the result." when `parse_method === "llm"` else "Parsed with the built-in parser — please review the result."); `POST /resumes/from-text { text, is_master: true }`; `PUT /resumes/{id} { parsed_content }` ("Master resume saved"); `POST /users/me/integrations/linkedin/sync` ("Syncing LinkedIn profile…", integrations refetched after **8000 ms**). Browser links: `/api/v1/resumes/{id}/pdf?template=<classic|modern>` (download + preview iframe, iframe keyed by version+template), tailored `r.pdf_url || /api/v1/resumes/{id}/pdf`.

UI:
- No master (error or missing): `PageHeader` "Resume Lab" / "Your master resume is the single source of truth — every tailored version is derived from it."; `EmptyState` "Upload your master resume" with `Upload file` and `Paste text`; paste modal "Paste your resume" (`Textarea` min-h 360px; `Import` disabled until **≥ 50** characters).
- With master: description "Master resume v{version} · updated {date}[ · from {filename}]"; actions `Replace` (file picker), template `Select` (`classic` "Classic" default, `modern` "Modern"), `PDF` link, `Save changes` (disabled until dirty).
- Hidden file input `accept=".pdf,.docx,.txt,.md"`.
- LinkedIn diff card "LinkedIn has updates" (when `profile_diff.has_changes`).
- `ResumeEditor` (2/3 width) — see Section 6.
- Side cards: "Preview" (iframe 520px), "LinkedIn sync" (`Sync`, disabled unless connected; else link to `/dashboard/settings?tab=integrations`), "Tailored versions" list.

### 5.26 `/dashboard/settings` — Settings (`src/app/dashboard/settings/page.tsx`)

Tabs are URL-controlled: value = `?tab=` (default **`mass-apply`**), change → `router.replace("/dashboard/settings?tab=<v>")`; `?google=connected` → `router.replace("/dashboard/settings?tab=integrations")`. `PageHeader` eyebrow "Setup", title "Settings", description "Tell the agent what you want, where to look, and how to answer."

| Tab value | Trigger label (exact) | Panel |
|---|---|---|
| `mass-apply` | **Mass apply** | `MassApplyPanel` |
| `preferences` | **Preferences** | `PreferencesForm` |
| `sources` | **Job sources** | `PreferencesForm sourcesOnly` |
| `answers` | **Saved answers** | `FieldMappingsForm` |
| `integrations` | **Integrations** | `IntegrationsPanel` |
| `profile` | **Profile** | `ProfileForm` |
| `privacy` | **Privacy** | `PrivacyPanel` |

Shared helpers: `Row` (label + hint grid; directly labels `Input`, `Select`, `Switch`, `TagInput` children, else `role="group"`); `useSaver()` (toast "Saved"/custom on success, "Could not save" + message on error); `pill(on)` toggle-pill class.

**Mass apply** (`useMe`):
- "One-click presets" (`POST /users/me/preferences/preset/{name}`; toast "Preset applied"): `ai-engineer` "AI engineer · Python" (spans 2 columns), `india-internships` "India · Summer 2027", `internships` "Internships", `startups` "Startups", `new-grad` "New grad"; each with `Apply preset`.
- "How jobs are picked" rows: `Review mode` pills `swipe` "Swipe Review (recommended)" / `auto` "Automatic threshold"; `Resume to send` pills `original` "Your original file" / `light` "Light tweaks" / `full` "Full AI tailoring"; `Apply automatically after I keep` (Switch `auto_submit_kept`); `Trust AI answers to open questions` (`trust_generated_answers`); `Keep automatically at score` (number 0–100, empty = `null`, placeholder "off"); `Search top companies in every scan` (`scan_top_companies`, default true); `Internshala postings per scan` (number, clamped 0–50, default 10); `Internshala share of each scan` (number, clamped 0–100, default 25, "%"); `Skip possible fraud` (`skip_suspicious_companies`, default true); `Skip jobs without visa sponsorship` (`exclude_no_sponsorship`); `Max applications per day` (1–200); `Jobs per source per scan` (10–1000, empty = `null`, placeholder "50"); `Curated internship lists` (TagInput `sources.internship_lists`, placeholder "simplify-internships").
- `Save mass-apply settings` → `PUT /users/me/preferences { preferences: { review_mode, resume_strategy, auto_submit_kept, trust_generated_answers, auto_keep_min_score, max_jobs_per_source, exclude_no_sponsorship, max_applications_per_day, internshala_share (?? 25), internshala_per_scan (?? 10), skip_suspicious_companies (?? true), scan_top_companies (?? true), sources: { internship_lists } } }`.

**Preferences**:
- "Internship focus" card (`FocusCard`; defaults `DEFAULT_FOCUS = { enabled: true, country: "India", prime_cities: ["Delhi", "New Delhi", "Delhi NCR", "Gurugram", "Noida"], country_share: 90 }`): `Internships only` (switch sets `job_types` to `["internship"]` and `experience_level` to `["internship"]`, or back to `["internship", "full-time"]`), `Season` (placeholder "Summer 2027", empty → null), `Focus on one country` (switch + country input disabled when off), `Share in {country}` (`Slider` 50–100 step 5, shows `%`), `Prime cities` (TagInput). `Save internship focus` (saves the whole preference object).
- "Search preferences" card: `Target roles`, `Tech focus` (`focus_skills`), `Skip these technologies` (`avoid_skills`), `Target locations` (TagInputs); `Work arrangement` select (`any` "Any", `remote` "Remote only", `hybrid` "Hybrid / remote OK", `onsite` "On-site"); `Internships only` (`internships_only`, default true) → when on shows `Year of study` (select `""` "Any year (don't check)", 1–5 "1st…5th year") and `Graduating in` (number 2000–2100, placeholder = estimated year from `GET /users/me/student` or "e.g. 2029", with source note " (from your resume)" / " (estimated)"); when off shows `Job types` pills (`full-time, part-time, internship, contract, freelance`); `Salary range` (min, max numbers; currency input uppercased); `Companies to avoid`, `Companies to target`, `Exclude titles containing` (TagInputs); `Match threshold` (native range 0–100 bound to **`auto_apply_threshold`**); `Max applications per day` (1–200); `Posted within (days)` (1–90); `Automatic scans` (switch `scan_enabled` + "every" `scan_interval_hours` 1–168 "hours"); `Cover letters` (`cover_letter_enabled`); `Resume PDF template` (`classic`/`modern`); `Timezone` (placeholder = browser tz). `Save preferences` → `PUT /users/me/preferences { preferences: <entire prefs object> }`.

**Job sources** (`sourcesOnly`): `Platforms to scan` pills over `ALL_PLATFORMS = ["internshala", "internships", "greenhouse", "lever", "ashby", "workday", "linkedin", "indeed", "glassdoor", "wellfound", "generic"]`; TagInputs `Greenhouse boards`, `Lever companies`, `Ashby boards`, `Workday career sites`, `Company careers pages`, `Internshala searches` (`sources.internshala_urls`). `Save sources` → same full `PUT /users/me/preferences`.

**Saved answers** (SWR `/users/me/field-mappings` → `{ mappings, standard_fields }`): one `Row` per standard field (`Select` with "— not set —" when options, else `Input` of type password/number/text; password placeholder "Used when an ATS requires an account"); custom mappings rows with delete (`DELETE /users/me/field-mappings/{field_name}`, toast "Deleted"); "Add a custom answer" (question + answer; `Add` disabled until both; key = question lower-cased with whitespace → `_`). `Save answers` → `PUT /users/me/field-mappings { mappings: [{ field_name, field_value }] }` (skips empty values and the mask `"********"`).

**Integrations** (`useIntegrations`, `useMe`):
- **AI model** card: facts Provider (`anthropic` "Claude (Anthropic)", `openai` "OpenAI", `ollama` "Ollama", null "None"), Model ("built-in heuristics" when null), Fallback; heuristics warning when no provider; Ollama status (Reachable/Not reachable, Cloud, Model downloaded / not downloaded), `Download model` → `POST /users/me/integrations/ollama/pull`, progress polled via `GET /users/me/integrations/ollama/pull` every **1500 ms** while `status === "pulling"` (toasts "Downloaded {model}" / "Download failed"); `Test AI` → `POST /users/me/integrations/llm/test` (result box "Answered in {s} s" or "The AI didn't answer", sample, error, hint "Fix"); setup guide pills `This computer (Mac)` / `Your server (Docker)` / `Ollama Cloud` with steps and copyable `.env` blocks (Mac: `LLM_PROVIDER=ollama`, `OLLAMA_MODEL=qwen3.5:4b`, `OLLAMA_BASE_URL=http://localhost:11434`; Server: `COMPOSE_PROFILES=ollama`, `LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL=http://ollama:11434`, `OLLAMA_MODEL=qwen3.5:4b`, setup script `curl -fsSL https://raw.githubusercontent.com/saksham-eng560/HireFlow/main/scripts/server-setup.sh | WITH_OLLAMA=1 bash`, path `~/hireflow/.env`; Cloud: `LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL=https://ollama.com`, `OLLAMA_MODEL=gpt-oss:120b`, `OLLAMA_API_KEY=`). Mac step text: "Add these lines to `.env` in the HireFlow folder."
- **Google — Gmail & Calendar**: not configured note (GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET); connected → "Connected as {email}", badges Gmail / Calendar / Push notifications, "Inbox checked …", `Disconnect` → `POST /auth/google/disconnect`; else `Connect Google account` → `GET /auth/google/connect` → `window.location.href = url`.
- **LinkedIn — Chrome extension**: session status; 3 setup steps; `Generate extension token` → `POST /auth/extension-token` (shows dashboard URL `window.location.origin`, read-only token input + copy; "This token can only sync your LinkedIn and Internshala sessions. It expires in 180 days."); `Disconnect` → `DELETE /users/me/integrations/linkedin`.
- **Internshala — apply bot** (`InternshalaCard`): status; `Check session` → `POST /users/me/integrations/internshala/check` → `{ session_valid }`; `Disconnect` → `DELETE /users/me/integrations/internshala`; rows `Let the agent apply on Internshala` (turning on opens warning modal "Let the agent apply on Internshala?" with button "I understand, turn it on"), `Submit automatically` (disabled unless bot on), `Daily limit` (1–25, default 15; clamped on save). `Save Internshala settings` → `PUT /users/me/preferences { preferences: { internshala_bot_enabled, internshala_auto_submit: bot && auto, internshala_daily_limit } }`.
- **Notifications**: `Channels` pills `dashboard, email, discord, slack`; `Pop-ups` switch (`notification_popups`); `Browser notifications` → `Notification.requestPermission()` (toasts "Browser notifications enabled" / "Permission not granted" / "Not supported in this browser"); `Application updates everywhere` (`progress_updates_everywhere`); `Progress e-mail` select (`daily` "Daily", `weekly` "Weekly (Sundays)", `off` "Off"); `Discord webhook URL`, `Slack webhook URL`. `Save notifications` → `PUT /users/me/preferences { preferences: { notification_channels, discord_webhook_url || null, slack_webhook_url || null, progress_updates_everywhere, progress_digest, notification_popups } }` then refetch `/auth/me` and integrations.
- **Agent capabilities** (read-only): AI model, Embeddings, Residential proxies, CAPTCHA solver, Auto-fill forms, Dry-run mode.

**Profile**: `Full name`, `Phone`, `Location`, `LinkedIn URL` → `PATCH /users/me { full_name, phone, location, linkedin_url }` (`Save profile`).

**Privacy**: "Export your data" → link `/api/v1/users/me/export` (`Download export`); "Delete my account" → modal "Delete your account?" / "Type DELETE to confirm."; `Delete permanently` disabled until the input equals exactly `DELETE`; calls `DELETE /users/me { confirm: "DELETE" }` then `router.replace("/")`.

Animations: `TabsContent` `animate-fade-in`; `Progress` transitions; Radix modal/sheet animations. Keyboard: TagInput Enter/comma/Backspace (Section 6).

### 5.27 Consolidated API call inventory (frontend → backend, all under `/api/v1`)

| Method | Path | Caller(s) |
|---|---|---|
| GET | `/auth/me` | `useMe` (shell, overview, applied, settings, use-popups) |
| GET | `/auth/config` | `AuthForm` |
| GET | `/auth/ws-token` | `useWebSocket` |
| GET | `/auth/google/connect` | Settings › Integrations |
| POST | `/auth/login`, `/auth/register` | `AuthForm` |
| POST | `/auth/logout` | `DashboardShell` |
| POST | `/auth/extension-token` | Settings › Integrations |
| POST | `/auth/google/disconnect` | Settings › Integrations |
| GET | `/agent/status` | `useAgentStatus` |
| GET | `/agent/runs?page_size=50[&run_type=]` | Logs |
| GET | `/agent/runs/{id}` | `useScan` (finished run), Logs `RunDetail` |
| POST | `/agent/start-scan` (`{}` or `{platforms}`) | `useScan.start` |
| POST | `/agent/runs/{id}/cancel` | `useScan.stop` |
| POST | `/agent/check-email` | Emails |
| GET | `/analytics/overview[?days=]` | `useOverview` |
| GET | `/applications?…` | `useApplications` |
| GET | `/applications/{id}` | `useApplication` |
| GET | `/applications/review-queue?limit=100` | `useSubmitQueue` |
| PATCH | `/applications/{id}` | Application detail |
| POST | `/applications/{id}/approve`, `/skip`, `/status`, `/restage` | Application detail (`/status` also I Applied) |
| POST | `/applications/{id}/mark-applied` | `IAppliedButton`, Swipe Review |
| POST | `/applications/{id}/submit`, `/bot-apply` | Ready to submit |
| POST | `/applications/manual` | I Applied log dialog |
| GET | `/review/queue?…` | Swipe Review |
| POST | `/review/{id}` | Swipe Review, Top companies |
| POST | `/review/{id}/undo`, `/review/{id}/details`, `/review/bulk` | Swipe Review |
| GET | `/jobs?…`, `/jobs/{id}`, `/jobs/top-companies[?…]` | Jobs, Top companies |
| POST | `/jobs/{id}/prepare`, `/jobs/{id}/evaluate`, `/jobs/import` | Jobs |
| POST | `/jobs/company-trust` | `CompanyBadge` |
| GET | `/notifications?limit=30` | `useNotifications` |
| POST | `/notifications/read-all`, `/notifications/{id}/read` | `NotificationBell` |
| GET | `/communications?…`, `/communications/{id}` | Emails |
| POST | `/communications/{id}/draft`, `/communications/{id}/send` | Emails |
| PATCH | `/communications/{id}` | Emails |
| GET | `/interviews?upcoming=true\|false`, `/interviews/{id}` | Interviews |
| POST | `/interviews`, `/interviews/{id}/prep` | Interviews |
| PATCH | `/interviews/{id}` | Interviews |
| GET | `/resumes/master`, `/resumes?tailored=true` | Resume Lab |
| POST | `/resumes/upload` (multipart), `/resumes/from-text` | Resume Lab |
| PUT | `/resumes/{id}` | Resume Lab |
| GET | `/users/me/integrations` | `useIntegrations` |
| GET | `/users/me/field-mappings` | Overview onboarding, Settings |
| PUT | `/users/me/field-mappings` | Settings |
| DELETE | `/users/me/field-mappings/{field_name}` | Settings |
| GET | `/users/me/student` | Settings › Preferences |
| PUT | `/users/me/preferences` | Settings (5 forms), Swipe Review, `usePopups` |
| POST | `/users/me/preferences/preset/{name}` | Settings › Mass apply |
| PATCH | `/users/me` | Settings › Profile |
| DELETE | `/users/me` (`{confirm: "DELETE"}`) | Settings › Privacy |
| POST | `/users/me/progress-report` | I Applied |
| POST | `/users/me/integrations/linkedin/sync` | Resume Lab |
| DELETE | `/users/me/integrations/linkedin` | Settings |
| GET/POST | `/users/me/integrations/ollama/pull` | Settings › AI model |
| POST | `/users/me/integrations/llm/test` | Settings › AI model |
| POST | `/users/me/integrations/internshala/check` | Settings |
| DELETE | `/users/me/integrations/internshala` | Settings |

Direct browser navigations (not via `api()`): `/api/v1/auth/google/login?next=…`, `/api/v1/resumes/{id}/pdf[?template=]`, `/api/v1/users/me/export`, plus server-provided screenshot / PDF URLs; WebSocket `/api/v1/ws` (Section 7).

---

---

## Section 6: Frontend Component Inventory

Paths relative to `frontend/src/`. `EASE_OUT = [0.22, 1, 0.36, 1]`. All Framer Motion usage honours reduced motion (`MotionConfig reducedMotion="user"` at the root plus `useReducedMotion()` checks noted below).

### 6.1 Top-level components (`src/components/*.tsx`, 24 files)

| # | File | Exports |
|---|---|---|
| 1 | `analytics-charts.tsx` | `TimelineChart`, `MatchHistogram`, `StatusBreakdown`, `StatTile` |
| 2 | `application-card.tsx` | `ApplicationCard` |
| 3 | `approval-modal.tsx` | `ApprovalModal` |
| 4 | `auth-form.tsx` | `AuthForm` |
| 5 | `brand.tsx` | `LogoMark`, `Logo`, `TunnelGrid`, `TagPile`, `Seal`, `BrushHeadline` |
| 6 | `company-badge.tsx` | `CompanyBadge`, `CompanyTag`, `YearFitTag` |
| 7 | `dashboard-shell.tsx` | `DashboardShell` |
| 8 | `empty-state.tsx` | `EmptyState` |
| 9 | `i-applied-button.tsx` | `canSelfApply`, `useRefreshTracking`, `IAppliedButton`, `SelfAppliedTag` |
| 10 | `job-match-badge.tsx` | `scoreTone`, `JobMatchBadge` |
| 11 | `modal.tsx` | `Modal` |
| 12 | `motion-graphics.tsx` | `PipelineMotion`, `FocusStrip` |
| 13 | `motion-provider.tsx` | `MotionProvider`, `RootFade` |
| 14 | `motion.tsx` | `EASE_OUT`, `PageTransition`, `RouteSweep`, `Stagger`, `StaggerItem`, `AnimatedNumber`, `MaybeAnimatedNumber` |
| 15 | `notification-bell.tsx` | `NotificationBell` |
| 16 | `page-header.tsx` | `PageHeader` |
| 17 | `resume-editor.tsx` | `ResumeEditor` |
| 18 | `scan-progress.tsx` | `ScanBar`, `ScanProgressPanel`, `ScanIndicator` |
| 19 | `status-badge.tsx` | `StatusBadge` |
| 20 | `status-timeline.tsx` | `StatusTimeline` |
| 21 | `swipe-card.tsx` | types `Decision`, `SwipeCardHandle`; `SwipeCard` (forwardRef), `DeckShadowCard` |
| 22 | `tag-input.tsx` | `TagInput` |
| 23 | `theme-provider.tsx` | `ThemeProvider` |
| 24 | `theme-toggle.tsx` | `ThemeToggle` |

#### 6.1.1 `analytics-charts.tsx` (client; Recharts)
- Constants: `AXIS = { stroke: "var(--chart-axis)", tick: { fill: "var(--chart-muted)", fontSize: 12 }, tickLine: false }`; `SERIES = [{discovered, "Discovered", var(--series-1)}, {applied, "Applied", var(--series-2)}, {responses, "Responses", var(--series-3)}]`; `shortDate(v)` → `toLocaleDateString(undefined, {month: "short", day: "numeric"})` of `${v}T00:00:00`.
- `TimelineChart({ data: Overview["timeline"], height = 260 })` — legend (short colored lines) + ghost toggle button `"Show table"` / `"Show chart"`. Chart: `ResponsiveContainer` → `LineChart` (margin `{top 8, right 12, left -18, bottom 0}`), `CartesianGrid stroke var(--chart-grid) vertical={false}`, XAxis `date` with `shortDate` and `minTickGap={24}`, YAxis `allowDecimals={false} width={48}`, custom tooltip (date + 3 series values), 3 `Line type="linear" strokeWidth={2} dot={false}` with `activeDot r=4`. Table mode: `max-h-[260px]` scroll, rows reversed (newest first), columns Date / Discovered / Applied / Responses.
- `MatchHistogram({ data: Overview["match_distribution"], height = 220 })` — `BarChart barCategoryGap={4}`, XAxis `range` `interval={0}` fontSize 11, `Bar dataKey="count" fill var(--series-1) maxBarSize={24}`, tooltip "`{n}` jobs scored `{range}`".
- `StatusBreakdown({ byStatus: Record<string, number> })` — horizontal single-hue bar list in fixed order `matched, preparing, pending_approval, approved, applied, acknowledged, screening, assessment, interview, final_round, offer, accepted, rejected, withdrawn, failed, skipped` (zero rows hidden; bar width `count/max*85%`, min 4px); empty → "No applications yet."
- `StatTile({ label: string; value: ReactNode; hint?: ReactNode; className?: string; icon?: ReactNode })` — bordered card; value via `MaybeAnimatedNumber` (`font-display text-4xl`).
- API calls: none.

#### 6.1.2 `application-card.tsx` (server-compatible)
- `ApplicationCard({ app: ApplicationSummary; showIApplied?: boolean = true; action?: ReactNode })` — row card with stretched link to `/dashboard/applications/{id}`: `JobMatchBadge`, role, warning icon when `needs_manual_review` ("Needs review"), company, location (+ " · Remote" if remote and location lacks "remote"), platform label, "updated {timeAgo}"; right side (z-10, clickable): `SelfAppliedTag` (md+) when `self_applied`, `IAppliedButton` (sm+) when `showIApplied && canSelfApply(status)`, `action`, `StatusBadge`; `ArrowUpRight` icon.
- Animation: CSS hover `-translate-y-0.5` + border color (`duration-200`, disabled with `motion-reduce`).

#### 6.1.3 `approval-modal.tsx` (client)
- `ApprovalModal({ app: ApplicationDetail; open: boolean; onOpenChange: (open: boolean) => void; onApprove: () => Promise<void>; answers: CustomAnswer[]; coverLetter: string })`.
- `Modal` title "Approve & submit application", description "{role} at {company}". Checklist (CheckCircle2 success / AlertTriangle warning):
  1. "Tailored resume PDF attached" (ok when `tailored_resume_pdf_url`)
  2. "Cover letter (N words)" / "No cover letter" (ok when letter non-empty or no job)
  3. "All answers reviewed" / "N answer(s) were flagged for review — make sure you checked them"
  4. "Required answers filled" / "N required answer(s) are empty — fill them in before approving" (+ list of those questions)
  5. "Form fields filled" / "N required form field(s) could not be filled automatically" (required `unmapped` form fields)
- Manual-review reason box; explanatory text; checkbox "I reviewed the resume, cover letter and answers, and everything is accurate."
- Footer: `Cancel`; `Approve & submit` (ShieldCheck) — disabled until checkbox checked **and** no empty required answers; shows loading while `onApprove()` runs, then closes.
- API: none directly (caller posts `/applications/{id}/approve`).

#### 6.1.4 `auth-form.tsx` (client)
- `AuthForm({ mode: "login" | "register" })` — documented in Section 5.10 (SWR `/auth/config`; `POST /auth/login`, `POST /auth/register`; Google link; `ERRORS` map; validation). Uses `TunnelGrid`, `Logo`, `BrushHeadline`.

#### 6.1.5 `brand.tsx` (server-compatible, pure SVG)
- `LogoMark({ className? })` — 16×20 SVG: bracket path `M2 1h7v4H6v10h3v4H2z` (`currentColor`) + block `M11 7h3v6h-3z` (`hsl(var(--primary))`).
- `Logo({ href = "/", className? })` — `Link` with `LogoMark` and wordmark `<span className="font-bold">Hire</span>Flow` (19px, tight tracking).
- `TunnelGrid({ className?, animated = true })` — wire-frame "tunnel" SVG generated at module load: `RINGS = 17`, `RAILS = 44`, viewBox `600×900`, squircle exponent `n = 3.4`, ring scale `1/(1 + 0.21*i)`, radii `420*s × 610*s`, 96 points per ring, dots at every joint (`r = max(0.8, 3.2*s)`, opacity `min(1, 0.35 + s)`), radial fade `tunnel-fade` to background. When `animated`: group has `animate-tunnel-drift` (`motion-reduce:animate-none`, `transformBox: fill-box`). `preserveAspectRatio="xMidYMid slice"`.
- `TagPile({ className? })` — absolutely positioned `.tag-pill`s (640×118 box): Internships (0,52,-58°), Greenhouse (50,12,-14°), Resume (64,70,0°), Cover letters (170,64,178°), Lever (212,18,31°), Ashby (296,4,12°), Startups (330,60,-12°), Workday (452,66,2°), Swipe right (450,-6,-24°), Gmail (560,34,58°).
- `Seal({ className? })` — 24-point star polygon (radii 31/26) in primary + foreground center dot.
- `BrushHeadline({ lines: string[]; className? })` — `h1.display`, first two lines inside `.brush` span (red strokes), remaining lines below; default size `text-[clamp(2.3rem,5.1vw,4.6rem)]`.

#### 6.1.6 `company-badge.tsx` (client)
- `LOOK` per verdict: `verified` → ShieldCheck, label "Verified", success tone, "The company check passed: the agent may apply here by itself."; `unverified` → ShieldQuestion, "Unverified", muted, "Nothing wrong found, nothing proven either: the agent never applies here by itself. Check it, then submit it yourself or mark it legit."; `suspicious` → ShieldAlert, "Possible fraud", primary tone, "This posting shows scam signs, so it's skipped and nothing is sent to it."
- `CompanyBadge({ company: string; check?: CompanyCheck | null; className?: string; showTier?: boolean = true })` — optional tier label chip; verdict button opens a `Popover` (align start, width `min(22rem, 100vw-2rem)`) with explanation, reasons list (entries starting with `⚠` in primary), and actions: `Undo “legit”` (when `method === "you"`, sends `trusted: null`), `Mark legit` (when not verified, `trusted: true`), `Not legit` (`trusted: false`). Calls `POST /jobs/company-trust { company, trusted }` → `{ applications_updated }`; toast "{company} marked legit" / "{company} marked not legit" / "Back to the agent's check for {company}" with counts; then `mutate(() => true)` (revalidates every SWR key). Error toast "Couldn't save that". Trigger and content stop `pointerdown` propagation so they never start a swipe.
- `CompanyTag({ check?, className? })` — non-interactive tiny tier + verdict tag, `title` = reasons joined by newline.
- `YearFitTag({ label?: string | null; className? })` — success chip with GraduationCap; renders nothing when no label.

#### 6.1.7 `dashboard-shell.tsx` (client) — `DashboardShell({ children })`
- Constants: `BURST_MS = 10_000`, `BURST_AT = 3`. `NAV` sections/items (href, label, lucide icon, badge):
  - **Agent**: `/dashboard` "Overview" (LayoutDashboard); `/dashboard/review` "Swipe Review" (Layers, badge `review`); `/dashboard/top-companies` "Top companies" (Crown); `/dashboard/submit` "Ready to submit" (ListChecks, badge `pending`); `/dashboard/applications` "Applications" (Send); `/dashboard/applied` "I Applied" (CheckCheck); `/dashboard/jobs` "All jobs" (Briefcase).
  - **Inbox**: `/dashboard/emails` "Emails" (Inbox); `/dashboard/interviews` "Interviews" (CalendarDays).
  - **Insights**: `/dashboard/analytics` "Analytics" (BarChart3); `/dashboard/logs` "Agent logs" (ScrollText).
  - **Setup**: `/dashboard/resume` "Resume Lab" (FileText); `/dashboard/settings` "Settings" (Settings).
- Active item: exact match for `/dashboard`, `startsWith` otherwise. Badges: `review` = `status.to_review` (filled primary pill), `pending` = `status.pending_approval` (warning outline); hidden when 0; capped "999+".
- Data: `useMe()`, `useAgentStatus()`, `useSWRConfig().mutate`, `useToast()`; registers service worker `navigator.serviceWorker.register("/sw.js")` on mount; `useWebSocket(handler)` → `live` flag (handler documented in Section 7.6).
- Logout: `POST /auth/logout` then `router.replace("/login")`.
- Layout: root `div.noise flex min-h-screen`; desktop `aside` (lg+, sticky, `w-[248px]`, logo bar h-16, nav, footer); mobile `Sheet side="left"` (`w-[272px]`, `SheetTitle` with Logo, sr-only description "Dashboard navigation"), opened by header `Menu` button (aria "Open menu"), closes on nav click. Footer: "Applied today" `{applied_today} / {daily_limit ?? "—"}` with primary progress bar (`min(100, applied/max(1,limit)*100)%`, `transition-all`); live dot (`animate-pulse-dot bg-success` + "Live updates on" or grey + "Polling for updates").
- Header (sticky, h-16, `bg-background/90 backdrop-blur`): breadcrumb `/ {current label || "Dashboard"}` (sm+); spacer; `ScanIndicator run={running scan or null}`; "`{to_review}` to swipe" link → `/dashboard/review` (md+, hidden on review route); `NotificationBell`; `ThemeToggle`; account `DropdownMenu` (trigger shows name/email (sm+) and square `Avatar` with initials of first two name parts, `bg-primary`): label (name, email), `Settings` → `/dashboard/settings`, `Resume Lab` → `/dashboard/resume`, separator, `Sign out` (primary).
- Animations: nav highlight `motion.span layoutId="nav-active"` inside `LayoutGroup id="desktop-nav" | "mobile-nav"`, spring `{ stiffness: 520, damping: 42 }` (red block slides between items); icon hover `translate-x-0.5`.

#### 6.1.8 `empty-state.tsx`
- `EmptyState({ icon: LucideIcon; title: string; description?: ReactNode; action?: ReactNode })` — dashed bordered centered block, round icon frame, `label-caps` title (13px bold).

#### 6.1.9 `i-applied-button.tsx` (client)
- `canSelfApply(status)` → true for `discovered, matched, skipped, preparing, pending_approval, approved, failed, withdrawn`.
- `useRefreshTracking()` → function that `mutate`s every string key starting with `/applications`, `/jobs`, `/review`, `/agent`, `/analytics`, `/notifications`.
- `IAppliedButton({ applicationId: string; onApplied?: (app: ApplicationDetail) => void; size?: ButtonProps["size"] = "sm"; variant?: ButtonProps["variant"] = "outline"; className?: string; label?: string = "I Applied" })` — state `idle | busy | done` (reset to idle when `applicationId` changes). Click (preventDefault + stopPropagation) → `POST /applications/{id}/mark-applied` → toast "Tracking {company ?? "this application"}" / "Moved to Applied. You'll get updates on Gmail and here whenever they reply."; after **650 ms** (0 with reduced motion) calls `onApplied(app)` and the refresh function. Error → idle + toast "Could not mark as applied". Done state: variant `success`, label "Applied", title "I applied to this job on my own — track it", `aria-live="polite"`.
- Animations: check-mark `motion.path d="M4 12.5l5 5L20 6.5"` `pathLength 0 → 1` in 0.35 s easeOut; burst of 6 rays (`BURST = [0, 60, 120, 180, 240, 300]` degrees) in `AnimatePresence`: `x [0, 14]`, `opacity [1, 0]`, `scaleX [0.4, 1]`, 0.5 s easeOut (skipped when reduced).
- `SelfAppliedTag({ className? })` — link to `/dashboard/applied` "You applied" (CheckCheck), success outline; stops click propagation.

#### 6.1.10 `job-match-badge.tsx`
- `scoreTone(score)`: null → `border-border text-muted-foreground`; ≥ 80 → filled primary; ≥ 60 → `border-foreground text-foreground`; ≥ 40 → `border-foreground/50 text-foreground/80`; else muted.
- `JobMatchBadge({ score: number | null | undefined; size?: "sm" | "md" | "lg" = "md" })` — square display-font block (`sm` h-8 w-8 text-xs, `md` h-11 w-11 text-sm, `lg` h-16 w-16 text-2xl); shows `score ?? "—"`; title "Match score N/100" / "Not evaluated yet"; aria "Match score N" / "Not scored".

#### 6.1.11 `modal.tsx` (client)
- `Modal({ open: boolean; onOpenChange: (open) => void; title: ReactNode; description?: ReactNode; children?: ReactNode; footer?: ReactNode; className?: string })` — wraps `Dialog`/`DialogContent` (`flex max-h-[90vh] max-w-lg flex-col p-0`), header with title + description (sr-only description = title when none), scrollable body (`p-5 scrollbar-thin`), optional footer bar (right-aligned). Remembers `document.activeElement` on open and restores focus to it on close (prevents Radix default) for keyboard users.

#### 6.1.12 `motion-graphics.tsx` (client)
- `PipelineMotion({ className? })` — landing loop. `STATIONS = ["Scan", "Swipe", "Tailor & fill", "Apply", "Track"]`, `CHIPS = [{SDE Intern, Gurugram}, {ML Intern, Noida}, {Data Intern, New Delhi}]` (subtitle "{place} · Summer 2027"), `LOOP = 7.5` s, `gap = LOOP / 3`. `role="img"` with aria-label "Scan, swipe, tailor and fill, apply, track: the agent's pipeline". Animations: rail pulse `left: 4% → 82%`, `duration LOOP/2`, repeat ∞, easeInOut, `repeatDelay 0.4`; each station flash `opacity [0, 1, 0]`, 0.9 s, repeat ∞, `repeatDelay gap - 0.9`, `delay (i/4) * LOOP * 0.86`; chips `left ["-22%", "4%", "84%", "104%"]`, `opacity [0, 1, 1, 0]`, `times [0, 0.1, 0.9, 1]`, `duration LOOP`, linear, repeat ∞, `delay i * gap`. Reduced motion: static chips at `6 + i*32%`, last station lit.
- `FocusStrip({ prefs: Preferences })` — "Hunting for" strip: parts = job types ("Internships only" when exactly `["internship"]`, else joined with " + "), `internship_season`, "~{country_share}% {country}" (when focus enabled), "{prime} first" (prime = "Delhi NCR" when first city matches /delhi/ and any city matches /ncr/, else first city); separators are small red squares; link "Change" → `/dashboard/settings?tab=preferences`. Animation: radar ring around Crosshair `scale 0.6 → 1.8`, `opacity 0.9 → 0`, 1.8 s, repeat ∞, easeOut.

#### 6.1.13 `motion-provider.tsx` (client)
- `MotionProvider({ children })` → `<MotionConfig reducedMotion="user">`.
- `RootFade({ children })` → opacity 0 → 1, 0.35 s `EASE_OUT` (see 5.2).

#### 6.1.14 `motion.tsx` (client)
- `EASE_OUT = [0.22, 1, 0.36, 1] as const`.
- `PageTransition({ children, className? })` — `RouteSweep` + fade-rise `{opacity 0, y 14}` → `{1, 0}`, 0.42 s.
- `RouteSweep()` — red 3px top bar: `scaleX [0, 0.72, 1]`, `opacity [1, 1, 0]`, 0.75 s, `times [0, 0.55, 1]`, easeOut; null when reduced.
- `Stagger({ children, className?, delay?: number = 0, as?: "div" | "ul" | "ol" | "section" = "div" })` — variants `hidden {}` / `show` → `staggerChildren: 0.05, delayChildren: delay`; `initial="hidden"` (false when reduced) `animate="show"`.
- `StaggerItem({ children, className?, as?: "div" | "li" | "article" = "div" })` — `hidden {opacity 0, y 12}` → `show {opacity 1, y 0}` 0.38 s `EASE_OUT`.
- `AnimatedNumber({ value: number; format?: (n) => string = n.toLocaleString(); className?: string; duration?: number = 0.9 })` — counts from the previous value (initially 0) to `value` with `animate()` when in view (`useInView once, margin "-40px"`), rounding each frame; reduced motion sets the value immediately.
- `MaybeAnimatedNumber({ value: ReactNode; className? })` — numbers animate; strings matching `/^(\d+)(%?)$/` animate preserving `%`; everything else rendered as is.

#### 6.1.15 `notification-bell.tsx` (client)
- `NotificationBell()` — `useNotifications()` (`/notifications?limit=30`, 30 s), `usePopups()`. Trigger: ghost icon button, `Bell` (or `BellOff` when pop-ups muted), unread count bubble (capped "9+"); aria-label "Notifications ({n} unread)[, pop-ups muted]"; title when muted "Pop-ups muted: notifications still collect here".
- Popover (align end, `w-[min(24rem,calc(100vw-2rem))]`): header "Notifications" with toggle `Mute pop-ups` / `Unmute` (`aria-pressed={!enabled}`, loading while saving, disabled until `/auth/me` loaded) and `Mark all read` → `POST /notifications/read-all` then `mutate()`. Muted banner: "Pop-ups are muted. New notifications still land here and in your other channels." List (`max-h-96`): each item is a `Link` to `n.link || "#"`; unread items tinted with a red dot; clicking closes the popover and, if unread, `POST /notifications/{id}/read` then `mutate()`; shows title, body (2-line clamp), `timeAgo(created_at)`. Empty: "You're all caught up."

#### 6.1.16 `page-header.tsx`
- `PageHeader({ title: string; description?: ReactNode; actions?: ReactNode; eyebrow?: string })` — bottom-bordered header; eyebrow `label-caps text-primary`; `h1.display text-3xl sm:text-4xl`; description `max-w-2xl`; actions right-aligned (wrap).

#### 6.1.17 `resume-editor.tsx` (client)
- `ResumeEditor({ value: ResumeContent; onChange: (next: ResumeContent) => void })` — fully controlled structured editor. Sections (internal `Section` with optional `+ Add` button): **Contact** (`name, email, phone, location, linkedin, github, portfolio` inputs labelled by capitalized key), **Summary** (textarea), **Experience** (Title, Company, Start "Jan 2022", End "Present", Location, "Achievements (one per line)" textarea → bullets; Remove), **Education** (Institution, Degree, Field, GPA, Start, End; Remove), **Projects** (Name, URL, Description textarea, Technologies TagInput; Remove), **Skills** (TagInputs `Technical`, `Tools`, `Languages`, `Soft skills`), **Certifications** (Name, Issuer, Date, trash icon "Remove certification"), **Awards** (TagInput). `linesToList` splits by newline, strips leading `•`, `-`, `*` bullets, trims, drops blanks. TagInput placeholders "Type and press Enter".

#### 6.1.18 `scan-progress.tsx` (client)
- Types: `Scan = ReturnType<typeof useScan>`. `STEPS`: `Search` (discovering), `Save` (saving), `Score` (scoring), `Done` (finishing, done).
- Helpers: `useNow(active)` re-renders every 1000 ms; `clock(s)` → "`Xm YYs`" or "`Ns`"; `etaText(eta)` → `< 60` s: "about {max(5, round(eta/5)*5)}s left", else "about {round(eta/60)} min left".
- `ScanBar({ percent: number; active: boolean; className? })` — `role="progressbar"` (aria-label "Scan progress"); fill width `max(2, min(100, percent))%` animated with spring `{ stiffness: 90, damping: 22 }` (instant when reduced); white sheen (`animate-sheen`) while active.
- `SourceChip` (internal): icon/detail per status — `pending` Clock "Waiting"; `running` spinning Loader2 "`done / total`" or "Searching" (+ hairline progress); `done` Check "`{found} found`"; `failed` AlertTriangle "Couldn't load"; `timeout` CircleSlash "Too slow, skipped"; `title` = error.
- `Running` (internal): "Scanning · {elapsed clock}[ · {eta}]" with pulsing dot; big `AnimatedNumber` percent (0.6 s) + message (`aria-live`, default "Starting the scan…"); `Stop` button (`scan.stop`, "Stopping" while stopping, disabled unless run status `running`); `ScanBar`; numbered steps `01 Search … 04 Done` (past steps checked, current in primary); source chips grid; counters "Postings found", "New for you", "Scored" (`/ to_score`) with `AnimatedNumber` 0.5 s.
- `Finished` (internal): status block — `completed` → "Scan finished" + message or "{jobs_discovered} new jobs"; `cancelled` → "Scan stopped" + "Jobs already scored are waiting in Swipe Review."; else "Scan failed" + message or "See the activity log for details."; duration; issues line linking `/dashboard/logs`; action `Start swiping` → `/dashboard/review` (ok/stopped) or `Activity log` → `/dashboard/logs`; `Dismiss` (X).
- `ScanProgressPanel({ scan: Scan; className? })` — `AnimatePresence initial={false}`; visible when `scan.running || scan.finished`; `motion.section` `{opacity 0, height 0}` ↔ `{opacity 1, height "auto"}`, 0.35 s `EASE_OUT`.
- `ScanIndicator({ run: AgentRun | null })` — header widget inside `AnimatePresence`: hairline bar along header bottom (spring width), and pill link to `/dashboard` (fade/slide `y -4 ↔ 0`) with `Radar` icon spinning (`[animation-duration:2.4s]`), "Scanning" (sm+), `{percent}%`.
- API: none directly (uses `useScan` passed in).

#### 6.1.19 `status-badge.tsx`
- `StatusBadge({ status: ApplicationStatus })` → `<Badge tone={STATUS_TONE[status] || "default"}>{STATUS_LABELS[status] || status}</Badge>`.

#### 6.1.20 `status-timeline.tsx`
- `StatusTimeline({ history: HistoryEntry[] })` — left-ruled ordered list; square primary markers; label from `STATUS_LABELS`, "{datetime} · by {titleCase(changed_by)}", notes. Empty: "No status changes yet."

#### 6.1.21 `swipe-card.tsx` (client)
- Types: `Decision = "keep" | "skip"`; `SwipeCardHandle = { fling: (decision: Decision) => Promise<void>; flyUp: () => Promise<void> }`.
- `SwipeCard` (forwardRef) props `{ card: ReviewCard; onDecide: (decision: Decision) => void; onLoadDetails?: () => Promise<void>; disabled?: boolean }`.
  - Gesture: `drag="x"` (false when disabled), `dragMomentum={false}`, `whileDrag={{ cursor: "grabbing" }}`, `touch-pan-y`. `onDragEnd`: `offset.x > 120 || velocity.x > 700` → keep; `offset.x < -120 || velocity.x < -700` → skip; else spring back `animate(x, 0, { type: "spring", stiffness: 420, damping: 32 })`.
  - Motion values: `rotate = useTransform(x, [-320, 320], [-12, 12])`; stamp opacities: KEEP `x [30, 120] → [0, 1]` (left, primary, `-rotate-12`), SKIP `x [-120, -30] → [1, 0]` (right, foreground, `rotate-12`), APPLIED `y [-140, -20] → [1, 0]` (center, success).
  - `fling(decision)`: `animate(x, ±window.innerWidth, { duration: 0.28, ease: [0.4, 0, 1, 1] })` then `onDecide`. `flyUp()`: `animate(y, -window.innerHeight, { duration: 0.42, ease: [0.4, 0, 1, 1] })`.
  - Content: header (platform label, " · curated list" when `listing_source`, " · posted {timeAgo}"), role, company, location, Remote, `CompanyBadge`, `YearFitTag`, big match score (primary when ≥ 70, label "match"); badges: focus badges (`location_tier` 0 "Prime location", 1 country, 3 "Outside {country}"; `season === "match"` season label, `"immediate"` "Starts immediately"), job type, terms, salary, sponsorship (tone success if contains "offers", danger if "not"/"citizen", hidden when "Other"); heads-up warning box (joined " · "); 5 criteria bars (`skills_match` Skills/Skills, `experience_match` Experience/Exp., `industry_match` Domain, `location_match` Location/Place, `compensation_match` Pay; each out of 20); "You have" (≤ 8 strong matches, primary badges) / "They want" (≤ 8 missing, muted); reasoning; "About the role" description; `Fetch full description` button when description < 400 chars and has `listing_source` and `onLoadDetails` provided; footer "Found {timeAgo}" + "Open posting" (`application_url || source_url`, new tab).
- `DeckShadowCard({ card: ReviewCard; depth: number })` — static card behind the top card: `translateY(depth*24px) scale(1 - depth*0.035)`, `zIndex -depth`, `opacity 1 - depth*0.3`, `transition-transform duration-300`; shows company + role.

#### 6.1.22 `tag-input.tsx` (client)
- `TagInput({ value: string[]; onChange: (value: string[]) => void; placeholder?: string; className?: string; id?: string; "aria-label"?: string })` — chips with remove buttons ("Remove {tag}") + inline input. Keyboard: `Enter` or `,` adds the draft (split on commas, trimmed, blanks and duplicates dropped); `Backspace` on empty draft removes the last tag; blur adds a pending draft. Placeholder shown only when no tags.

#### 6.1.23 `theme-provider.tsx` (client)
- `ThemeProvider(props: ComponentProps<typeof NextThemesProvider>)` → passes through to `next-themes`.

#### 6.1.24 `theme-toggle.tsx` (client)
- `ThemeToggle()` — ghost icon button; mounted guard (treat as dark before mount); in dark shows `Sun` (aria "Switch to paper (light) theme"), in light shows `Moon` (aria "Switch to ink (dark) theme"); `setTheme("light" | "dark")`.

### 6.2 shadcn/ui primitives (`src/components/ui/*.tsx`, 26 files)

| File | Exports | Wraps (package) | Notes / customisations |
|---|---|---|---|
| `alert-dialog.tsx` | `AlertDialog`, `AlertDialogPortal`, `AlertDialogOverlay`, `AlertDialogTrigger`, `AlertDialogContent`, `AlertDialogHeader`, `AlertDialogFooter`, `AlertDialogTitle`, `AlertDialogDescription`, `AlertDialogAction`, `AlertDialogCancel` | `@radix-ui/react-alert-dialog` | Overlay `bg-black/80`; action/cancel use `buttonVariants` (cancel `outline`). Not imported by any page/component. |
| `avatar.tsx` | `Avatar`, `AvatarImage`, `AvatarFallback` | `@radix-ui/react-avatar` | Used in shell (overridden `rounded-none`). |
| `badge.tsx` | `Badge`, `badgeVariants`, type `BadgeProps` | none (cva) | Rounded-full outlined pill, `text-[11px]`; `tone`: `default`, `primary`, `info`, `success`, `warning`, `danger`, `muted`, `outline` (default `default`). |
| `button.tsx` | `Button`, `buttonVariants`, type `ButtonProps` | `@radix-ui/react-slot` (`asChild`) | Square, uppercase, `tracking-[0.08em]`, `active:translate-y-px`; variants `default`, `destructive`, `success`, `outline`, `secondary`, `ghost`, `link`; sizes `default` (h-10 px-5), `sm` (h-8 px-3 text-[11px]), `lg` (h-12 px-7), `xl` (h-14 px-10 text-[15px]), `icon` (h-9 w-9); extra prop `loading` → disabled + `aria-busy` + spinning ring before children. |
| `card.tsx` | `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter` | none | Square bordered `bg-card`; title `text-sm font-bold uppercase tracking-[0.12em]`; padding p-5. |
| `checkbox.tsx` | `Checkbox` | `@radix-ui/react-checkbox` | Square primary border. Not imported by any page/component (native checkboxes are used). |
| `dialog.tsx` | `Dialog`, `DialogPortal`, `DialogOverlay`, `DialogTrigger`, `DialogClose`, `DialogContent`, `DialogHeader`, `DialogFooter`, `DialogTitle`, `DialogDescription` | `@radix-ui/react-dialog` | Overlay `bg-black/70 backdrop-blur-[2px]`; content `border-line shadow-2xl` with fade/zoom/slide animations and close X (sr "Close"); title `font-display uppercase`. |
| `dropdown-menu.tsx` | `DropdownMenu`, `DropdownMenuTrigger`, `DropdownMenuContent`, `DropdownMenuItem`, `DropdownMenuCheckboxItem`, `DropdownMenuRadioItem`, `DropdownMenuLabel`, `DropdownMenuSeparator`, `DropdownMenuShortcut`, `DropdownMenuGroup`, `DropdownMenuPortal`, `DropdownMenuSub`, `DropdownMenuSubContent`, `DropdownMenuSubTrigger`, `DropdownMenuRadioGroup` | `@radix-ui/react-dropdown-menu` | Content `sideOffset=4`, square; items support `inset`. |
| `input.tsx` | `Input` | none (native `<input>`) | h-10 square, focus `border-primary ring-1 ring-primary`, hover `border-foreground/50`. |
| `label.tsx` | `Label` | `@radix-ui/react-label` | cva base `text-sm font-medium leading-none`. |
| `popover.tsx` | `Popover`, `PopoverTrigger`, `PopoverContent`, `PopoverAnchor` | `@radix-ui/react-popover` | Content defaults `align="center"`, `sideOffset=4`, `collisionPadding=12`, `w-72 p-4`, portal. |
| `progress.tsx` | `Progress` | `@radix-ui/react-progress` | Track `h-1.5 bg-foreground/10`, indicator `bg-primary transition-all` via `translateX(-(100 - value)%)`. |
| `scroll-area.tsx` | `ScrollArea`, `ScrollBar` | `@radix-ui/react-scroll-area` | Not imported by any page/component. |
| `select.tsx` | `Select` | none — **native `<select>`** styled like inputs | Wrapper div gets `className`; `ChevronDown` icon; `appearance-none`. |
| `separator.tsx` | `Separator` | `@radix-ui/react-separator` | Default horizontal, decorative. Not imported by any page/component. |
| `sheet.tsx` | `Sheet`, `SheetPortal`, `SheetOverlay`, `SheetTrigger`, `SheetClose`, `SheetContent`, `SheetHeader`, `SheetFooter`, `SheetTitle`, `SheetDescription` | `@radix-ui/react-dialog` | cva `side`: `top`, `bottom`, `left`, `right` (default `right`); open 500 ms / close 300 ms slide. |
| `skeleton.tsx` | `Skeleton` | none | `animate-pulse bg-muted`. |
| `slider.tsx` | `Slider` | `@radix-ui/react-slider` | Single thumb; moves `aria-label` onto the Thumb; track `h-1 bg-foreground/15`, range primary, round thumb `border-2 border-primary`. |
| `sonner.tsx` | `Toaster` | `sonner` (+ `next-themes` `useTheme`) | Theme from `resolvedTheme` (default "dark"); square toast, `border-line bg-popover shadow-2xl`; success icon `text-success`, error icon `text-primary`. |
| `switch.tsx` | `Switch` | `@radix-ui/react-switch` | Extra prop `label` → `aria-label`; h-6 w-11, checked `bg-primary border-primary`, thumb translates 5. |
| `tabs.tsx` | `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent` | `@radix-ui/react-tabs` | Underline tabs: list `h-11 border-b overflow-x-auto`; trigger uppercase 12px `tracking-[0.12em]`, active `border-primary text-foreground`; content `mt-5 animate-fade-in`. |
| `textarea.tsx` | `Textarea` | none (native) | `min-h-[80px]`, same focus styling as Input. |
| `toast.tsx` | `ToastProvider`, `dismissToasts`, `useToast` | `sonner` (`toast`) + `./sonner` `Toaster` | `ToastProvider` renders children + `<Toaster position="bottom-right" />`. `useToast()` returns `show({ title: string; description?: string; tone?: "success" \| "error" \| "info"; id?: string })` → `sonner.error` / `sonner.success` / `sonner.message`(info/default) with `{ description, id }` (same `id` updates in place). `dismissToasts()` → `sonner.dismiss()`. |
| `toggle-group.tsx` | `ToggleGroup`, `ToggleGroupItem` | `@radix-ui/react-toggle-group` | Shares `variant`/`size` through context; uses `toggleVariants`. |
| `toggle.tsx` | `Toggle`, `toggleVariants` | `@radix-ui/react-toggle` | Variants `default`/`outline`; sizes `default` h-9, `sm` h-8, `lg` h-10. |
| `tooltip.tsx` | `Tooltip`, `TooltipTrigger`, `TooltipContent`, `TooltipProvider` | `@radix-ui/react-tooltip` | Content `bg-primary text-primary-foreground text-xs`; only `TooltipProvider` is used (root layout, `delayDuration=200`). |

### 6.3 Hooks (`src/hooks/*.ts`, 4 files, all `"use client"`)

#### `use-applications.ts`
`const LIVE = { refreshInterval: 15000, revalidateOnFocus: true }`. Helper `scanning(status)` = any `running_runs` with `run_type === "scan"`.

| Export | SWR key | Options | Returns |
|---|---|---|---|
| `useMe()` | `"/auth/me"` | SWR defaults | `SWRResponse<User>` |
| `useAgentStatus()` | `"/agent/status"` | `{ ...LIVE, refreshInterval: (status) => scanning(status) ? 1500 : 15000 }` | `SWRResponse<AgentStatus>` |
| `useOverview(days?: number)` | `` `/analytics/overview${days ? `?days=${days}` : ""}` `` | LIVE | `SWRResponse<Overview>` |
| `useApplications(params: Record<string, string \| number \| boolean \| undefined>)` | `` `/applications?${query}` `` (insertion order; `undefined` and `""` skipped) | LIVE | `SWRResponse<Paginated<ApplicationSummary>>` |
| `useApplication(id?: string)` | `` `/applications/${id}` `` or `null` | LIVE | `SWRResponse<ApplicationDetail>` |
| `useSubmitQueue()` | `"/applications/review-queue?limit=100"` | `{ refreshInterval: 30000, revalidateOnFocus: false }` (returning from another tab must not reshuffle the sheet) | `SWRResponse<SubmitQueue>` |
| `useNotifications()` | `"/notifications?limit=30"` | `{ refreshInterval: 30000 }` | `SWRResponse<{ items: NotificationItem[]; unread: number }>` |
| `useIntegrations()` | `"/users/me/integrations"` | SWR defaults | `SWRResponse<Integrations>` |

All use `fetcher` (GET via `api()`).

#### `use-popups.ts`
- `usePopups()` → `{ enabled, setEnabled, saving, ready }`. `enabled = me?.preferences.notification_popups !== false` (default on). `ready = !!me`.
- `setEnabled(on)`: no-op without `me`; when turning **off** calls `dismissToasts()` immediately; sets `saving`; optimistic `mutate` of `/auth/me` with `optimisticData` (preferences.notification_popups = on), `rollbackOnError: true`, `revalidate: true`, performing `PUT /users/me/preferences { preferences: { notification_popups: on } }`. Saved to the account so every device follows it; muted notifications still collect in the bell.

#### `use-scan.ts`
- `applyScanProgress(status: AgentStatus | undefined, runId: string, progress: ScanProgress)` → returns a new status with `progress` merged into the matching `running_runs` entry, or the **same object** when the run isn't present (used to detect unknown runs).
- `useScan()` returns `{ status, running, progress, finished, dismissFinished, start, stop, starting, stopping, busy }`:
  - `running` = first `running_runs` entry with `run_type === "scan"` or null; `progress = running?.progress ?? null`; `busy = starting || !!running`.
  - Transition running → not running: remember `finishedId`, reset `stopping`, and `mutate` every string key starting with `/review`, `/applications`, `/jobs`, `/analytics`. SWR `/agent/runs/{finishedId}` (default options) provides `finished` (only while not running and id matches). `dismissFinished()` clears it.
  - `start(platforms?: unknown)`: `POST /agent/start-scan` with `{ platforms }` only when an array (a click event is ignored) else `{}`; toasts: success "Scan started" / "Watch the progress bar; jobs land in Swipe Review as they're scored."; 409 → info "A scan is already running" / "Its progress is shown below."; other → error "Could not start scan"; finally `refreshStatus()`.
  - `stop()`: `POST /agent/runs/{running.id}/cancel`; toast info "Stopping the scan" / "Jobs already scored stay in Swipe Review."; error → "Could not stop the scan".

#### `use-websocket.ts`
- `interface ServerEvent { type: string; data: Record<string, unknown> }`.
- `wsUrl()` and `useWebSocket(onEvent: (event: ServerEvent) => void): boolean` (returns `connected`). Full behaviour in Section 7.

### 6.4 Library modules (`src/lib/*.ts`)

#### `api-client.ts` — "Typed client for the HireFlow API"
| Export | Signature | Behaviour |
|---|---|---|
| `API_BASE` | `"/api/v1"` | Same-origin base (proxied to FastAPI by `next.config.js`). |
| `ApiError` | `class ApiError extends Error { status: number; detail: unknown; constructor(status, message, detail?) }` | Thrown for every non-2xx response; `detail` = parsed JSON body (or null). |
| `api<T>` | `(path: string, init?: RequestInit & { json?: unknown }) => Promise<T>` | URL = `path` if it starts with `"http"`, else `API_BASE + path`. Always `credentials: "include"`. When `json` given: sets `Content-Type: application/json` and `body = JSON.stringify(json)`; else uses `init.body`. Parses JSON only when response `content-type` includes `application/json` (parse errors → null); otherwise body = null. On `!ok`: if `status === 401` and running in a browser and `path` does **not** start with `"/auth/"` → `window.location.href = "/login?next=" + encodeURIComponent(pathname + search)`; then throws `ApiError(status, errorMessage(body, "Request failed (<status>)"), body)`. Returns body as `T`. |
| `fetcher` | `<T>(path: string) => api<T>(path)` | SWR fetcher (GET). |
| `post` | `<T>(path, json?) => api<T>(path, { method: "POST", json: json ?? {} })` | Always sends a JSON body (`{}` when omitted). |
| `put` | `<T>(path, json) => api<T>(path, { method: "PUT", json })` | |
| `patch` | `<T>(path, json) => api<T>(path, { method: "PATCH", json })` | |
| `del` | `<T>(path, json?) => api<T>(path, { method: "DELETE", json })` | JSON body only when provided. |
| `upload` | `async <T>(path, form: FormData) => api<T>(path, { method: "POST", body: form })` | No Content-Type set (browser adds multipart boundary). |
| (internal) `errorMessage(body, fallback)` | | `detail` string → returned; `detail` array → each `"<loc[1:] joined by '.'>: <msg>"` joined with `"; "`; else fallback. |

Timeout: the client sets **no** timeout/AbortController; requests are bounded only by the Next.js proxy (`experimental.proxyTimeout` = 15 min). The `/api/health` route uses its own 5 s timeout.

#### `types.ts` — exported types and interfaces (all fields)
- `type ApplicationStatus = "discovered" | "matched" | "skipped" | "preparing" | "pending_approval" | "approved" | "applied" | "acknowledged" | "screening" | "interview" | "assessment" | "final_round" | "offer" | "accepted" | "rejected" | "withdrawn" | "failed"` (17 values).
- `interface Preferences`: `target_roles: string[]`; `target_locations: string[]`; `remote_preference: "remote" | "hybrid" | "onsite" | "any"`; `salary_min: number | null`; `salary_max: number | null`; `salary_currency: string`; `experience_level: string[]`; `industries: string[]`; `company_size_preference: string[]`; `companies_to_avoid: string[]`; `companies_to_target: string[]`; `max_applications_per_day: number`; `auto_apply_threshold: number`; `job_types: string[]`; `notification_channels: string[]`; `keywords_exclude: string[]`; `posted_within_days: number`; `scan_enabled: boolean`; `scan_interval_hours: number`; `platforms: string[]`; `sources: { greenhouse_boards: string[]; lever_companies: string[]; ashby_boards: string[]; workday_sites: string[]; career_pages: string[]; internship_lists?: string[]; internshala_urls?: string[] }`; `location_focus?: LocationFocus`; `internship_season?: string | null`; `progress_updates_everywhere?: boolean`; `progress_digest?: "daily" | "weekly" | "off"`; `notification_popups?: boolean`; `internshala_share?: number` (default 25); `internshala_per_scan?: number` (default 10); `internships_only?: boolean`; `year_of_study?: number | null` (1–5); `graduation_year?: number | null`; `focus_skills?: string[]`; `avoid_skills?: string[]`; `skip_suspicious_companies?: boolean`; `trusted_companies?: string[]`; `scan_top_companies?: boolean`; `review_mode: "swipe" | "auto"`; `auto_submit_kept: boolean`; `trust_generated_answers: boolean`; `resume_strategy: "original" | "light" | "full"`; `auto_keep_min_score: number | null`; `max_jobs_per_source: number | null`; `exclude_no_sponsorship: boolean`; `internshala_bot_enabled?: boolean`; `internshala_auto_submit?: boolean`; `internshala_daily_limit?: number` (1–25); `discord_webhook_url: string | null`; `slack_webhook_url: string | null`; `timezone: string`; `cover_letter_enabled: boolean`; `resume_template?: string`; `auto_draft_replies?: boolean`.
- `interface LocationFocus`: `enabled?: boolean`; `country: string`; `prime_cities: string[]`; `country_share: number`.
- `interface User`: `id`; `email`; `full_name`; `phone: string | null`; `location: string | null`; `linkedin_url: string | null`; `has_password: boolean`; `google_connected: boolean`; `google_email: string | null`; `linkedin_connected: boolean`; `linkedin_session_valid: boolean`; `preferences: Preferences`; `last_scan_at: string | null`; `created_at: string`.
- `interface JobApplicationRef`: `id`; `status: ApplicationStatus`; `match_score: number | null`; `match_reasoning: string | null`; `similarity_score: number | null`.
- `interface Job`: `id`; `company_name`; `company_logo_url: string | null`; `role_title`; `location: string | null`; `is_remote: boolean`; `job_type: string | null`; `experience_level: string | null`; `salary_min: number | null`; `salary_max: number | null`; `salary_currency: string | null`; `source_url: string`; `source_platform: string`; `application_url: string | null`; `easy_apply: boolean`; `extracted_skills: string[]`; `posted_date: string | null`; `deadline_date: string | null`; `discovered_at: string`; `is_active: boolean`; `description?: string`; `application?: JobApplicationRef`; `company?: CompanyCheck`; `year_fit?: string | null`.
- `interface StudentInfo`: `internships_only: boolean`; `year_of_study: number | null`; `graduation_year: number | null`; `graduation_year_source: "you" | "resume" | "estimate" | ""`.
- `type CompanyVerdict = "verified" | "unverified" | "suspicious"`; `type CompanyTier = "big_tech" | "product" | "startup_india" | "startup_global" | "ai"`.
- `interface CompanyCheck`: `verdict: CompanyVerdict | null`; `score: number | null`; `reasons: string[]`; `method: string | null` (rules · ai · you); `tier: CompanyTier | null`; `tier_label: string | null`.
- `interface TopCompanies`: `tiers: { key: CompanyTier; label: string; count: number }[]`; `total: number`; `items: Job[]`; `catalog: Record<CompanyTier, string[]>`; `scan_top_companies: boolean`.
- `interface CustomAnswer`: `question: string`; `answer: string`; `field_type?`; `confidence?: number | null`; `needs_user_review?: boolean | null`; `options?: string[] | null`; `required?: boolean | null`; `source?: string | null`; `field_id?: string | null`.
- `interface FormFieldReport`: `label`; `kind`; `type`; `value`; `required: boolean`; `status: "filled" | "skipped" | "unmapped"`; `options?: string[]`; `confidence?: number`; `needs_user_review?: boolean`.
- `interface HistoryEntry`: `id`; `old_status: ApplicationStatus | null`; `new_status: ApplicationStatus`; `changed_by: string`; `notes: string | null`; `created_at: string`.
- `interface ResumeContent`: `personal_info: { name; email; phone; location; linkedin; github; portfolio }` (strings); `summary: string`; `education: { institution; degree; field; gpa; start_date; end_date; highlights: string[] }[]`; `experience: { company; title; start_date; end_date; location; bullets: string[] }[]`; `projects: { name; description; technologies: string[]; url }[]`; `skills: { technical: string[]; languages: string[]; tools: string[]; soft_skills: string[] }`; `certifications: { name; issuer; date }[]`; `awards: string[]`.
- `interface Resume`: `id`; `label: string | null`; `original_filename: string | null`; `is_master: boolean`; `version: number`; `parent_resume_id: string | null`; `tailored_for_job_id: string | null`; `changes_made: string[]`; `pdf_url: string | null`; `original_file_url: string | null`; `created_at`; `updated_at`; `parsed_content?: ResumeContent`; `parse_method?: string`.
- `interface ApplicationSummary`: `id`; `status: ApplicationStatus`; `match_score: number | null`; `match_reasoning: string | null`; `ats_platform: string | null`; `needs_manual_review: boolean`; `manual_review_reason: string | null`; `created_at`; `updated_at`; `submitted_at: string | null`; `job: Job | null`; `self_applied?: boolean`.
- `interface Communication`: `id`; `application_id: string | null`; `direction: "inbound" | "outbound"`; `sender_email: string | null`; `sender_name: string | null`; `subject: string | null`; `detected_intent: string | null`; `intent_confidence: number | null`; `urgency: string | null`; `is_action_required: boolean`; `action_taken: boolean`; `received_at: string | null`; `snippet: string`; `body_text?: string | null`; `extracted_details?: Record<string, string | number> | null`; `suggested_reply?: string | null`; `gmail_thread_id?: string | null`; `gmail_draft_id?: string | null`; `application?: { id; company_name; role_title; status: ApplicationStatus } | null`.
- `interface Interview`: `id`; `application_id`; `company_name: string | null`; `role_title: string | null`; `interview_type: string | null`; `scheduled_at: string`; `duration_minutes: number`; `timezone: string`; `meeting_link: string | null`; `meeting_platform: string | null`; `physical_location: string | null`; `interviewer_names: string[]`; `outcome: string | null`; `google_event_id: string | null`; `google_event_link: string | null`; `prep_notes?: string | null`; `company_research?: string | null`; `likely_questions?: { question: string; answer_outline: string }[]`; `feedback?: string | null`.
- `interface ApplicationDetail extends ApplicationSummary`: `job: Job | null`; `match_details: Record<string, unknown> | null`; `similarity_score: number | null`; `cover_letter: string | null`; `custom_answers: CustomAnswer[]`; `field_overrides?: Record<string, string>`; `form_fields: FormFieldReport[]`; `tailored_resume: Resume | null`; `tailored_resume_pdf_url: string | null`; `form_screenshot_url: string | null`; `confirmation_screenshot_url: string | null`; `confirmation_number: string | null`; `staged_at: string | null`; `approved_at: string | null`; `rejection_reason: string | null`; `offer_details: Record<string, unknown> | null`; `error_log: string | null`; `retry_count: number`; `notes: string | null`; `history: HistoryEntry[]`; `communications: Communication[]`; `interviews: Interview[]`.
- `interface ReviewRow`: `key: string` (profile key, `"label:<form label>"`, `"cover_letter"`, `"resume"` or `"file:<label>"`); `label`; `kind: "profile" | "question" | "cover_letter" | "resume" | "file"`; `value`; `type: string`; `options: string[]`; `required: boolean`; `filled: boolean`; `flagged: boolean`; `source: string`; `confidence: number | null`; `note: string | null`; `url: string | null`.
- `interface SubmitQueueItem extends ApplicationSummary`: `form_screenshot_url: string | null`; `tailored_resume_pdf_url: string | null`; `staged_at: string | null`; `blocker: string | null`; `bot: { site: string; missing: BotMissing | null } | null`; `apply_url: string | null`; `rows: ReviewRow[]`; `attention: number`.
- `type BotMissing = "bot_off" | "not_synced" | "expired"`.
- `interface SubmitQueue`: `items: SubmitQueueItem[]`; `total: number`.
- `interface DirectSubmitResponse extends ApplicationDetail`: `next_id: string | null`.
- `interface AgentRun`: `id`; `run_type: string`; `status: string`; `trigger: string | null`; `jobs_discovered`; `jobs_matched`; `applications_prepared`; `applications_submitted`; `errors_count` (numbers); `started_at: string`; `completed_at: string | null`; `duration_seconds: number | null`; `progress?: ScanProgress | null`; `log?: { ts: string; level: string; message: string; data?: Record<string, unknown> }[]`.
- `type ScanPhase = "discovering" | "saving" | "scoring" | "finishing" | "done" | "cancelled" | "failed"`.
- `interface ScanSourceProgress`: `name: string`; `status: "pending" | "running" | "done" | "failed" | "timeout"`; `found: number`; `done: number`; `total: number`; `error?: string`.
- `interface ScanProgress`: `phase: ScanPhase`; `percent: number`; `message: string`; `sources: ScanSourceProgress[]`; `found`; `new`; `scored`; `to_score` (numbers); `eta_seconds: number | null`; `updated_at: string`.
- `interface AgentStatus`: `has_master_resume: boolean`; `pending_approval`; `preparing`; `approved`; `applied_today`; `daily_limit` (numbers); `running_runs: AgentRun[]`; `last_scan_at: string | null`; `next_scan_at: string | null`; `scan_enabled: boolean`; `google_connected: boolean`; `linkedin_connected: boolean`; `to_review: number`; `review_mode: "swipe" | "auto"`.
- `interface ReviewCard`: `application_id`; `status: ApplicationStatus`; `match_score: number | null`; `match_reasoning: string | null`; `strong_matches: string[]`; `missing_skills: string[]`; `heads_up: string[]`; `scores: Partial<Record<"skills_match" | "experience_match" | "industry_match" | "location_match" | "compensation_match", number>>`; `job: Job & { description: string; sponsorship: string | null; terms: string[]; listing_source: string | null }`; `discovered_at: string | null`; `focus?: { location_tier: number | null; season: string | null; season_label: string | null; country: string | null }` (tier 0 prime city, 1 rest of country, 2 remote/unknown, 3 abroad).
- `interface ReviewStats`: `remaining`; `kept_today`; `skipped_today`; `kept_total` (numbers).
- `interface ReviewQueue`: `items: ReviewCard[]`; `matching: number`; `stats: ReviewStats`; `settings: { auto_submit_kept: boolean; review_mode: "swipe" | "auto" }`; `has_master_resume: boolean`.
- `interface Overview`: `totals: Record<string, number>`; `by_status: Record<string, number>`; `rates: { response_rate; interview_rate; offer_rate: number; avg_days_to_response: number | null }`; `timeline: { date; discovered; applied; responses }[]`; `match_distribution: { range: string; count: number }[]`; `platforms: { platform; discovered; applied; responses; interviews; response_rate; interview_rate }[]`; `top_keywords: { keyword; applications; callbacks; callback_rate; lift }[]`; `upcoming_interviews: { id; company; role; scheduled_at; type: string | null }[]`; `recent_runs: { id; run_type; status; started_at; jobs_discovered; jobs_matched; errors_count }[]`.
- `interface NotificationItem`: `id`; `event_type`; `title`; `body: string | null`; `link: string | null`; `data: Record<string, unknown>`; `is_read: boolean`; `created_at: string`.
- `interface Integrations`: `google: { configured; connected; email: string | null; gmail; calendar; last_polled_at: string | null; push_enabled }`; `linkedin: { connected; session_valid; updated_at: string | null; profile_diff: { has_changes: boolean; changes: { section; change; linkedin_value }[]; summary: string } | null; synced_at: string | null }`; `internshala: { connected; session_valid; updated_at: string | null; bot_enabled; auto_submit; daily_limit: number }`; `llm: { provider: string | null; providers: string[]; model: string | null; embedding_provider: string; ollama: OllamaStatus }`; `automation: { proxies: number; captcha: boolean; dry_run: boolean; auto_stage: boolean }`; `notifications: { smtp; discord; slack: boolean }`; `ats_credentials: string[]`.
- `interface OllamaPullProgress`: `status: "idle" | "pulling" | "success" | "error"`; `model: string | null`; `detail: string | null`; `completed: number`; `total: number`; `percent: number`; `error: string | null`.
- `interface OllamaStatus`: `configured: boolean`; `base_url: string`; `cloud: boolean`; `model: string | null`; `reachable: boolean`; `version: string | null`; `model_pulled: boolean | null`; `models: string[]`; `error: string | null`; `pull: OllamaPullProgress | null`.
- `interface LLMTestResult`: `ok: boolean`; `provider: string | null`; `model: string | null`; `latency_ms: number`; `sample?: string`; `error?: string`; `hint?: string`.
- `interface FieldMapping`: `field_name`; `field_value`; `field_type: string | null`; `is_secret: boolean`.
- `interface StandardField`: `label: string`; `type: string`; `options?: string[]`.
- `interface Paginated<T>`: `items: T[]`; `total: number`; `page: number`; `page_size?: number`; `counts?: Record<string, number>`; `self_applied_total?: number`.

(Total: 42 exports — 5 type aliases (`ApplicationStatus`, `CompanyVerdict`, `CompanyTier`, `BotMissing`, `ScanPhase`) and 37 interfaces (including generic `Paginated<T>`).)

#### `utils.ts`
| Export | Behaviour |
|---|---|
| `cn(...inputs: ClassValue[])` | `twMerge(clsx(inputs))` |
| `formatDate(value, opts = { dateStyle: "medium" })` | `"—"` for empty/invalid; else `toLocaleString(undefined, opts)` |
| `formatDateTime(value)` | `formatDate(value, { dateStyle: "medium", timeStyle: "short" })` |
| `timeAgo(value)` | `"—"` for empty; `Intl.RelativeTimeFormat(undefined, { numeric: "auto" })`; < 60 s in seconds, then minute (<3600), hour (<86400), day (<604800), week (<2629800), month (<31557600), else years |
| `formatSalary(min, max, currency)` | null when neither; `Intl.NumberFormat` currency (`currency \|\| "USD"`, `maximumFractionDigits 0`, `notation "compact"`); "min – max" or single value |
| `STATUS_LABELS` | discovered "Discovered", matched "Matched", skipped "Skipped", preparing "Preparing", pending_approval "Needs approval", approved "Submitting", applied "Applied", acknowledged "Acknowledged", screening "Screening", interview "Interview", assessment "Assessment", final_round "Final round", offer "Offer", accepted "Accepted", rejected "Rejected", withdrawn "Withdrawn", failed "Failed" |
| `STATUS_TONE` | discovered muted, matched info, skipped muted, preparing info, pending_approval warning, approved primary, applied primary, acknowledged info, screening/interview/assessment/final_round/offer/accepted success, rejected danger, withdrawn muted, failed danger |
| `PLATFORM_LABELS` | top_companies "Top companies", internshala "Internshala", internships "Internship lists", linkedin "LinkedIn", indeed "Indeed", glassdoor "Glassdoor", wellfound "Wellfound", greenhouse "Greenhouse", lever "Lever", workday "Workday", ashby "Ashby", generic "Career pages", custom "Company site", unknown "Unknown" |
| `titleCase(value)` | `""` for empty; replaces `_`/`-` with spaces and capitalises each word |

---

---

## Section 7: Real-Time Architecture

Sources: `backend/app/core/websocket.py`, `backend/app/core/redis.py`, `backend/app/services/notifier.py`, `backend/app/main.py` (lifespan), `backend/app/api/files.py` (the `/ws` route lives here, mounted under `API_PREFIX`), `backend/app/api/auth.py` (`/auth/ws-token`), `frontend/src/hooks/use-websocket.ts`, `frontend/src/hooks/use-popups.ts`, `frontend/src/components/dashboard-shell.tsx`, `frontend/public/sw.js`.

### 7.1 Topology

```
Celery worker / API request handler
   └─ notifier.notify(...) / notifier.push_update(...)  ──►  core.websocket.publish_event(user_id, type, data)
          │  Redis available:  PUBLISH events:<user_id>  {"type": ..., "data": {...}}
          │  Redis unavailable: manager.deliver_local(...)  (only reaches sockets in the SAME process)
          ▼
Every API process: ConnectionManager._redis_listener  (PSUBSCRIBE events:*)
          ▼
manager.send_to_user(user_id, payload)  ──►  each open WebSocket of that user: ws.send_json(payload)
          ▼
Browser: useWebSocket (DashboardShell) ──► SWR mutate / toasts / service-worker OS notification
```

- Endpoint: `WS /api/v1/ws` (`@router.websocket("/ws")` in `api/files.py`, router included with prefix `settings.API_PREFIX = "/api/v1"`).
- The Next.js rewrites do **not** carry WebSockets. The browser connects directly: in production Caddy routes `/api/v1/*` (HTTP and WS) to `api:8000` on the same origin; in local dev the client derives `ws://<host>:8000/api/v1/ws` when the dashboard runs on port 3000; `NEXT_PUBLIC_WS_URL` overrides both.
- Lifespan (`main.py`): on startup `manager.bind_loop(asyncio.get_running_loop())` then `await manager.start_subscriber()`; logs "HireFlow API ready (env=…, llm=…, db=…)"; on shutdown `await manager.stop_subscriber()` (cancels the listener task).

### 7.2 Authentication (ws-token ticket + cookie fallback)

1. Before each (re)connect the client calls `GET /api/v1/auth/ws-token` through the BFF (session cookie `hireflow_session` is sent first-party). Backend: `create_token(str(user.id), scope="ws", expires_delta=timedelta(minutes=5))` → `{ "token": "<JWT>" }` (HS256, payload `sub`, `scope`, `iat`, `exp`, `jti`). Because the path starts with `/auth/`, a 401 here does **not** trigger the client's login redirect; the hook just schedules a retry.
2. Client opens `new WebSocket(`${wsUrl()}?token=${encodeURIComponent(token)}`)`.
3. Server: `raw = token query param or websocket.cookies["hireflow_session"]`; `decode_token(raw, expected_scopes=("ws", "access"))` (so a valid session cookie also authenticates); `user_id = str(uuid.UUID(payload["sub"]))`. On `TokenError`/`ValueError`/`KeyError` → `websocket.close(code=4401)`. Then loads the user in a new DB session; missing or `is_active == false` → `close(code=4401)`.
4. On success: `manager.connect(user_id, ws)` (accept + add to `_connections[user_id]` set), then immediately sends `{"type": "connected", "data": {"user_id": "<id>"}}`.

### 7.3 Heartbeat

| Side | Behaviour |
|---|---|
| Client | After `onopen`, `setInterval` every **25 000 ms** sends the text frame `"ping"` when `readyState === OPEN`; interval cleared on close/unmount. |
| Server | Loops on `receive_text()`; on exactly `"ping"` replies `{"type": "pong", "data": {}}`; other text is ignored. No server-initiated ping/timeout; dead sockets are pruned when a `send_json` fails (`send_to_user` collects failures and calls `disconnect`). `WebSocketDisconnect` → `finally: manager.disconnect(user_id, ws)` (removes the user entry when its set becomes empty). |
| Redis listener | Polls `pubsub.get_message(timeout=1.0)` in a worker thread (`asyncio.to_thread`) — ~1 s poll cadence. |

The client ignores `connected` and `pong` messages (no handler matches them).

### 7.4 Reconnection / backoff (client, `use-websocket.ts`)

- `connect()`: fetch ws-token → open socket. Any failure fetching the token → `schedule()`.
- `onopen`: `attempt = 0`, `setConnected(true)`, start ping interval.
- `onerror`: `socket.close()`; `onclose`: `setConnected(false)`, clear ping, `schedule()`.
- `schedule()`: `attempt += 1`; `setTimeout(connect, Math.min(30000, 1000 * 2 ** Math.min(attempt, 5)))` → delays **2 s, 4 s, 8 s, 16 s, 30 s, 30 s, …** (2^5 s = 32 s capped at 30 s).
- Unmount: `closed = true`, clear timer and ping, `socket.close()`; no reconnect after unmount.
- Malformed frames (JSON parse errors) are silently ignored. The latest `onEvent` handler is kept in a ref, so the effect runs once.
- `wsUrl()`: `process.env.NEXT_PUBLIC_WS_URL` if set; else scheme `wss` when page is `https:` else `ws`; host `${hostname}:8000` when `window.location.port === "3000"`, else `window.location.host`; path `/api/v1/ws`.
- Return value `connected` drives the sidebar indicator: green pulsing dot "Live updates on" vs grey "Polling for updates". SWR polling continues regardless (WebSocket is an accelerator, polling is the fallback).

### 7.5 Redis Pub/Sub

- Channel per user: **`events:<user_id>`** (`CHANNEL_PREFIX = "events:"`; no product prefix, so it is identical under HireFlow naming). Subscriber pattern: `PSUBSCRIBE events:*`; user id = channel name minus the prefix.
- Message format: `json.dumps({"type": <event_type>, "data": <dict or {}>}, default=str)`.
- `publish_event(user_id, event_type, data=None)`: if `get_redis()` returns a client → `client.publish(...)` and return; on publish exception logs warning "Failed to publish event via Redis: …" and falls back; fallback `manager.deliver_local(user_id, payload)` → `asyncio.run_coroutine_threadsafe(send_to_user(...), bound_loop)` (no-op if no loop bound / loop closed). Events published from a Celery worker without Redis are therefore lost (polling covers them).
- `get_redis()` (`core/redis.py`): returns `None` when `settings.REDIS_URL` is empty (default `"redis://localhost:6379/0"`); lazily creates `redis.Redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=5)` and `ping()`s it (thread-locked); on `RedisError` logs "Redis unavailable (…); falling back to in-process state" and does not retry for **30 s** (`_RETRY_AFTER_SECONDS = 30.0`). `reset_redis()` clears the cache. `/health/ready` reports `redis: "ok"` or `"unavailable (in-process fallback)"`.
- Listener is started only if Redis is reachable at startup (`start_subscriber` checks `get_redis() is not None`); listener crash is logged ("Redis event listener crashed") and the pubsub closed.

### 7.6 Event catalogue

WebSocket message envelope is always `{"type": string, "data": object}`.

#### 7.6.1 Wire-level event types

| `type` | Emitted by (file → function) | `data` payload | Frontend reaction (`DashboardShell` handler unless noted) |
|---|---|---|---|
| `connected` | `api/files.py` → `websocket_endpoint` (direct `send_json`, not Pub/Sub) | `{ user_id }` | ignored |
| `pong` | `api/files.py` → reply to `"ping"` | `{}` | ignored |
| `notification` | `services/notifier.py` → `notify()` whenever the event's channel set includes `"dashboard"` (after inserting a `Notification` row and `flush()`) | `{ id, event_type, title, body, link, data, created_at (ISO or null) }` | see 7.6.3 |
| `scan_progress` | `services/scan_progress.py` → `ScanProgress.flush()` via `push_update` (throttled: at most every `FLUSH_INTERVAL = 0.8` s unless forced) | `{ run_id, progress: { phase, percent, message, sources: [{name, status, found, done, total, error?}], found, new, scored, to_score, eta_seconds, updated_at } }` | `mutate("/agent/status", current => applyScanProgress(current, run_id, progress), { revalidate: false })`; if the run was not in the cached status (`next === current`) → `mutate("/agent/status")` (refetch). No toast. (`ScanProgress.finish()` stores the final snapshot on the run but does not push; the follow-up `agent_run_updated` triggers the refetch.) |
| `agent_run_updated` | `services/agent_orchestrator.py` → `RunLog.finish(status)` (every agent run: scan, prepare, apply…) | `{ id, status }` (`completed` / `failed` / `cancelled` …) | `mutate` every string key starting with `/applications`, `/agent`, `/analytics`, `/jobs`, `/review` |
| `agent_run_updated` | `api/agent.py` → `cancel_run` (`POST /agent/runs/{id}/cancel` on a running run) | `{ id, status: "cancelled" }` | same as above |
| `application_updated` | `services/application_service.py` → `set_status()` (every successful status change; also called by agent and API flows) | `{ id, status, old_status (or null) }` | same prefix-mutate as `agent_run_updated` |

`push_update(user_id, event_type, data)` in `notifier.py` is the "lightweight real-time UI refresh (no persisted notification)" wrapper around `publish_event`.

#### 7.6.2 Notification `event_type`s (carried inside `type: "notification"`)

Channel matrix `EVENT_CHANNELS` (`ALL = {"dashboard", "email", "chat"}`; unknown types default to `{"dashboard"}`). `PROGRESS_EVENTS = {application_submitted, self_applied, recruiter_email, status_changed, interview_scheduled, offer_received}` are upgraded to `ALL` when the user preference `progress_updates_everywhere` is true (default). Only types whose final channel set includes `dashboard` create a `Notification` row and a WebSocket `notification` event. E-mail goes out only if `"email"` is also in the user's `notification_channels` (default `["dashboard", "email"]`), subject prefixed `"[HireFlow]"` (`NOTIFICATION_SUBJECT_PREFIX`, ignored by the Gmail monitor), via SMTP or the user's Gmail. Chat goes to Discord/Slack webhooks (per-user URL or server default).

| `event_type` | Channels | Emitted in (file → context) | Title (exact template) | `link` | `data` |
|---|---|---|---|---|---|
| `scan_completed` | dashboard | `services/agent_orchestrator.py` → scan, swipe mode | "Job scan finished" (body "`{n} new jobs — {waiting} waiting for your swipe.`") | `/dashboard/review` | `{ run_id }` |
| `scan_completed` | dashboard | `services/agent_orchestrator.py` → scan, auto mode | "Job scan finished" (body "`{n} new jobs, {m} matches.`") | `/dashboard/jobs` | `{ run_id }` |
| `agent_error` | all | `services/agent_orchestrator.py` → scan failure | "Job scan failed" (body = error ≤ 300 chars) | `/dashboard/logs` | `{}` |
| `agent_error` | all | `services/agent_orchestrator.py` → preparation failure | "Could not prepare `{company}` application" | `/dashboard/applications/{id}` | `{}` |
| `session_expired` | all | `services/agent_orchestrator.py` → `_internshala_session_expired` (once per synced login) | "Internshala session expired" | `/dashboard/settings?tab=integrations` | `{}` |
| `session_expired` | all | `services/agent_orchestrator.py` → staging and submission with expired LinkedIn session (2 sites) | "LinkedIn session expired" | `/dashboard/settings` | `{}` |
| `session_expired` | all | `services/linkedin_sync.py` → profile sync | "LinkedIn session expired" (body "Open LinkedIn in Chrome and click 'Sync session' in the HireFlow extension.") | `/dashboard/settings` | `{}` |
| `session_expired` | all | `worker/tasks_email.py` → `check_user_email` on `GoogleAuthError` | "Google access expired" | `/dashboard/settings` | `{}` |
| `application_submitted` | dashboard + chat (→ all) | `services/agent_orchestrator.py` → successful submit; Internshala "already applied" by agent | "✅ Applied: `{role}` @ `{company}`" | `/dashboard/applications/{id}` | `{}` |
| `application_ready` | all | `services/agent_orchestrator.py` → `_mark_ready` (status → pending_approval) | "Review application: `{role}` @ `{company}`" | `/dashboard/applications/{id}` | `{ application_id, match_score }` |
| `self_applied` | all | `services/agent_orchestrator.py` → `mark_self_applied` (I Applied / manual log) | "📌 Tracking: `{role}` @ `{company}`" (body "You applied on your own. HireFlow now watches your inbox for replies from {company} …") | `/dashboard/applications/{id}` | `{ application_id, company, role }` |
| `application_failed` | all | `services/agent_orchestrator.py` → final submission failure | "Could not submit `{company}` application" | `/dashboard/applications/{id}` | `{}` |
| `linkedin_profile_changed` | dashboard + email | `services/linkedin_sync.py` → diff has changes | "Your LinkedIn profile has updates" | `/dashboard/resume` | `{ changes: [≤ 10 items] }` |
| `progress_digest` | dashboard + email + chat | `services/progress.py` → `send_due_digests` (~20:00 local, daily or Sunday weekly) and `send_now` (`POST /users/me/progress-report`) | digest title from `build_digest` | `/dashboard/applied` | `{}` |
| `interview_scheduled` | all | `services/gmail_service.py` → interview invite parsed from e-mail | "Interview scheduled: `{role}` @ `{company}`" | `/dashboard/interviews?id={interview_id}` | `{ interview_id, application_id }` |
| `offer_received` | all | `services/gmail_service.py` → e-mail intent `offer` | "🎉 Offer from `{company}`" | `/dashboard/emails?id={communication_id}` | `{ communication_id, intent }` |
| `recruiter_email` | dashboard + chat (→ all) | `services/gmail_service.py` → any other processed recruiter e-mail | "Recruiter e-mail from `{company}`" (body "`{Intent}: {subject}`" + optional status-change line) | `/dashboard/emails?id={communication_id}` | `{ communication_id, intent }` |
| `interview_reminder_1h` | dashboard + email | `worker/tasks_calendar.py` → reminder task (≤ 1h05m before) | "⏰ Interview in 1 hour: `{company}`" | `/dashboard/interviews?id={id}` | `{}` |
| `interview_reminder_24h` | all | `worker/tasks_calendar.py` → reminder task (≤ 24h05m before) | "📅 Interview tomorrow: `{company}`" | `/dashboard/interviews?id={id}` | `{}` |
| `weekly_summary` | email + chat only | `worker/tasks_calendar.py` → `weekly_summary` | "Your weekly HireFlow summary" | `/dashboard/analytics` | — (no dashboard channel ⇒ **no Notification row and no WebSocket event**) |
| `status_changed` | dashboard (→ all) | declared in `EVENT_CHANNELS`/`PROGRESS_EVENTS` but **never emitted** anywhere in the backend | — | — | — |

#### 7.6.3 Frontend handling of `notification` (`DashboardShell`)

1. Always: `mutate(key => typeof key === "string" && (key.startsWith("/notifications") || key.startsWith("/agent")))` (bell list/unread count and agent status refresh).
2. Mute switch: if `me.preferences.notification_popups === false` → stop here (the item still appears in the bell).
3. Burst detection: keep timestamps from the last `BURST_MS = 10_000` ms; `burst = count >= BURST_AT (3)`.
   - Burst: `toast({ id: "notification-burst", title: "{count} new notifications", description: "They're all in the bell (top right). Mute pop-ups there if you'd rather not see them.", tone: "info" })` — same id, so the toast updates in place and counts up instead of stacking.
   - Single: `toast({ title: d.title || "Update", description: d.body, tone: event_type includes "error" or "failed" ? "error" : "info" })`.
4. OS notification: only when `document.hidden` **and** `"Notification" in window` **and** `Notification.permission === "granted"` → `navigator.serviceWorker.controller.postMessage({ type: "notify", title, body, link: burst ? "/dashboard" : d.link, tag: burst ? "burst" : undefined })`.

Other reactions:
- `useScan` (Overview, Swipe Review, Top companies): when the running scan disappears from `/agent/status`, it `mutate`s keys starting with `/review`, `/applications`, `/jobs`, `/analytics` and fetches `/agent/runs/{id}` for the "Scan finished" panel.
- Polling fallbacks (always active): `/agent/status` 15 s (1.5 s while a scan runs), `/applications*` and `/analytics/overview*` 15 s, `/notifications?limit=30` 30 s, `/applications/review-queue?limit=100` 30 s, `/communications?…` 30 s, `/agent/runs?…` 10 s, `/agent/runs/{id}` 3 s while running.

#### 7.6.4 Mute switch (`use-popups.ts`)

- Preference `notification_popups` (stored on the account; default enabled when absent). Toggled from the bell (`Mute pop-ups` / `Unmute`) or Settings › Integrations › Notifications › `Pop-ups`.
- Muting calls `dismissToasts()` immediately and saves `PUT /users/me/preferences { preferences: { notification_popups: false } }` with optimistic SWR update of `/auth/me` (rollback on error).
- Muted: no toasts and no OS notifications; the bell icon switches to `BellOff`, a banner explains "Pop-ups are muted. New notifications still land here and in your other channels."; e-mail/chat channels are unaffected.
- Browser permission is requested only from Settings › Integrations › `Enable browser notifications` (`Notification.requestPermission()`).

### 7.7 Service worker (`public/sw.js`)

Registered by `DashboardShell` on mount: `navigator.serviceWorker.register("/sw.js")` (errors swallowed) — i.e. only once a `/dashboard/*` page has loaded.

| Event | Behaviour |
|---|---|
| constants | `CACHE = "hireflow-shell-v2"`; `SHELL = ["/dashboard", "/icon.svg", "/icon-192.png", "/manifest.webmanifest"]` |
| `install` | `caches.open(CACHE).then(cache => cache.addAll(SHELL))` (failures ignored); `self.skipWaiting()` |
| `activate` | delete every cache whose key ≠ `CACHE`; `self.clients.claim()` |
| `fetch` | Ignore (no `respondWith`) when method ≠ `GET` or URL pathname starts with `/api/` (API never cached). For `request.mode === "navigate"`: network-first `fetch(request).catch(() => caches.match("/dashboard"))` (offline shell fallback). All other GETs pass through untouched (no runtime caching). |
| `message` | If `data.type === "notify"` and `registration.showNotification` exists → `showNotification(data.title \|\| "HireFlow", { body: data.body \|\| "", icon: "/icon-192.png", badge: "/icon-192.png", data: { link: data.link \|\| "/dashboard" }, ...(data.tag ? { tag: data.tag } : {}) })`. The `"burst"` tag makes a burst summary replace the previous one instead of stacking. |
| `notificationclick` | `notification.close()`; `link = notification.data.link \|\| "/dashboard"`; `clients.matchAll({ type: "window", includeUncontrolled: true })` → for the first client supporting `focus`: `client.navigate(link)` and `client.focus()`; if none → `clients.openWindow(link)`. |

The PWA manifest (`start_url "/dashboard"`, `display "standalone"`) plus this worker make the dashboard installable with an offline shell.

---

## Section 8: Background Task Registry (Celery)

Source files: `backend/app/worker/__init__.py` (empty), `celery_app.py`, `dispatch.py`, `tasks_scan.py`,
`tasks_apply.py`, `tasks_sync.py`, `tasks_email.py`, `tasks_calendar.py`, plus `scripts/local_scheduler.py`.

### 8.1 Celery application (`backend/app/worker/celery_app.py`)

`configure_logging()` (from `app.core.logging_config`) runs at import time, before the app is built.

| Setting | Value |
|---|---|
| App name (main) | `"hireflow"` |
| Broker | `settings.celery_broker` = `CELERY_BROKER_URL` or `REDIS_URL` or `"memory://"` |
| Result backend | `settings.celery_backend` = `CELERY_RESULT_BACKEND` or `REDIS_URL` (may be `None`) |
| `include` | `app.worker.tasks_scan`, `app.worker.tasks_apply`, `app.worker.tasks_email`, `app.worker.tasks_sync`, `app.worker.tasks_calendar` |
| `task_serializer` / `result_serializer` | `"json"` / `"json"` |
| `accept_content` | `["json"]` |
| `timezone` / `enable_utc` | `"UTC"` / `True` |
| `task_acks_late` | `True` |
| `worker_prefetch_multiplier` | `1` |
| `task_reject_on_worker_lost` | `True` |
| `result_expires` | `3600` (seconds) |
| `broker_connection_retry_on_startup` | `True` |
| `task_default_queue` | `"default"` |
| `task_routes` | `hireflow.prepare_application`, `hireflow.stage_application`, `hireflow.submit_application`, `hireflow.linkedin_sync_user` → queue `"browser"`; everything else → `default` |
| Global time limits | none set (no `task_time_limit` / `task_soft_time_limit` in conf); per-task `soft_time_limit` only (table 8.2); no task has a hard `time_limit` |
| Queues declared | none explicitly (`task_queues` unset); workers consume `-Q default,browser` (entrypoint, Makefile, `start.sh`) |
| Eager mode | if `settings.CELERY_TASK_ALWAYS_EAGER`: `task_always_eager = True`, `task_eager_propagates = False` |

### 8.2 Task inventory (16 Celery tasks)

Each task is a thin Celery wrapper (`@celery_app.task(name="hireflow.<name>")`) around a plain function that
is also registered in the dispatch registry with `@register("<name>")` (same name, without the
`hireflow.` prefix). Every plain function opens its own `session_scope()`.

| # | Celery name | File | Registered fn → wrapper | Args | Soft limit | Hard limit | Queue | What it does |
|---|---|---|---|---|---|---|---|---|
| 1 | `hireflow.scan_user` | `tasks_scan.py` | `scan_user` → `scan_user_task` | `user_id: str, trigger: str = "user", platforms: list[str] \| None = None, run_id: str \| None = None` → `str \| None` | — | — | default | Loads user (returns `None` if missing / inactive); reuses an existing `AgentRun` when `run_id` given; builds `orch.RunLog(db, user, "scan", trigger, existing=...)` and calls `agent_orchestrator.run_scan(...)`; returns run id. |
| 2 | `hireflow.scan_due_users` | `tasks_scan.py` | `scan_due_users` → `scan_due_users_task` | none → `int` | — | — | default | Hourly: for every active user with `prefs.scan_enabled` (default True) whose `last_scan_at` is older than `prefs.scan_interval_hours` (default 6) and who has no `AgentRun(run_type="scan", status="running")` started within the last 2 h → `enqueue("scan_user", user_id, "schedule")`. Returns count enqueued. |
| 3 | `hireflow.prepare_application` | `tasks_apply.py` | `prepare_application` → `prepare_application_task` | `application_id: str` | **900 s** | — | **browser** | `agent_orchestrator.prepare_application(db, id)` (enrich JD, tailor/choose resume, cover letter, pre-answer Greenhouse questions, then stage or mark ready). |
| 4 | `hireflow.stage_application` | `tasks_apply.py` | `stage_application` → `stage_application_task` | `application_id: str` | **600 s** | — | **browser** | `agent_orchestrator.stage_application(db, id)` — fill the form in a browser without submitting, screenshot, then ready-or-submit. |
| 5 | `hireflow.submit_application` | `tasks_apply.py` | `submit_application` → `submit_application_task` | `application_id: str` | **600 s** | — | **browser** | `agent_orchestrator.submit_application(db, id)` — only acts on `APPROVED` applications. |
| 6 | `hireflow.linkedin_sync_user` | `tasks_sync.py` | `linkedin_sync_user` → `linkedin_sync_user_task` | `user_id: str` → `dict` | **300 s** | — | **browser** | `linkedin_sync.sync_linkedin_profile(db, user)`; drops `"diff"` from the result; returns `{"status": "missing"}` when user not found. |
| 7 | `hireflow.linkedin_sync_all` | `tasks_sync.py` | `linkedin_sync_all` → `linkedin_sync_all_task` | none → `int` | — | — | default | Enqueues `linkedin_sync_user` for every active user with a non-null `linkedin_session_cookie`. |
| 8 | `hireflow.check_user_email` | `tasks_email.py` | `check_user_email` → `check_user_email_task` | `user_id: str` → `dict[str,int]` | — | — | default | If user exists and `google_connected`: `gmail_service.sync_user_inbox(db, user)`. On `GoogleAuthError` → `notify(..., "session_expired", "Google access expired", "Reconnect Google in Settings to keep monitoring recruiter e-mails. (<exc>)", link="/dashboard/settings")` and return `{}`. |
| 9 | `hireflow.check_all_emails` | `tasks_email.py` | `check_all_emails` → `check_all_emails_task` | none → `int` | — | — | default | Enqueues `check_user_email` for every active user with a `google_refresh_token`. |
| 10 | `hireflow.handle_gmail_push` | `tasks_email.py` | `handle_gmail_push` → `handle_gmail_push_task` | `email_address: str, history_id: str \| None = None` | — | — | default | Gmail Pub/Sub push: finds user by `lower(google_email)` then `lower(email)`; enqueues `check_user_email`. (`history_id` unused.) Dispatched from `api/files.py` Gmail webhook. |
| 11 | `hireflow.renew_gmail_watches` | `tasks_email.py` | `renew_gmail_watches` → `renew_gmail_watches_task` | none → `int` | — | — | default | For users with refresh token where `watch_needs_renewal(user)` (only when `GMAIL_PUBSUB_TOPIC` set and expiry < 2 days away) → `start_watch(db, user)`; failures logged as warnings. Returns renewed count. |
| 12 | `hireflow.send_interview_reminders` | `tasks_calendar.py` | `send_interview_reminders` → `send_interview_reminders_task` | none → `int` | — | — | default | Interviews with `scheduled_at` in (now, now+25 h) and outcome `pending`/NULL: if ≤ 1 h 05 m away and `reminder_1h_sent` false → notify `interview_reminder_1h` ("⏰ Interview in 1 hour: <company>", body `"<role> — <meeting_link or physical_location or 'see calendar'>"`), sets both `reminder_1h_sent` and `reminder_24h_sent`; elif ≤ 24 h 05 m and `reminder_24h_sent` false → notify `interview_reminder_24h` ("📅 Interview tomorrow: <company>"). Link `/dashboard/interviews?id=<id>`. |
| 13 | `hireflow.progress_digest` | `tasks_calendar.py` | `progress_digest` → `progress_digest_task` | none → `int` | — | — | default | `progress.send_due_digests()` — hourly check; each user gets the digest at `DIGEST_HOUR = 20` in their own `prefs.timezone`. |
| 14 | `hireflow.weekly_summary` | `tasks_calendar.py` | `weekly_summary` → `weekly_summary_task` | none → `int` | — | — | default | For each active user: `analytics.compute_overview(db, user, days=7)`; notify `weekly_summary`, title **"Your weekly HireFlow summary"**, body "Last 7 days: N applications submitted, N awaiting your review, N interviews, N offers. Response rate N%.", link `/dashboard/analytics`. |
| 15 | `hireflow.retention_cleanup` | `tasks_calendar.py` | `retention_cleanup` → `retention_cleanup_task` | none → `int` | — | — | default | Deletes applications with `updated_at < now − DATA_RETENTION_DAYS` (default 730) and status in {REJECTED, WITHDRAWN, SKIPPED, ACCEPTED, FAILED}; deletes their storage objects (`form_screenshot_url`, `confirmation_screenshot_url`, `tailored_resume_pdf_url`, errors ignored); also deletes `Notification` rows older than 90 days. Returns deleted application count. |
| 16 | `hireflow.expire_stale_jobs` | `tasks_calendar.py` | `expire_stale_jobs` → `expire_stale_jobs_task` | none → `int` | — | — | default | Sets `Job.is_active = False` for active jobs whose `last_checked` is older than 45 days. |

Where tasks are dispatched from (`enqueue("<name>", ...)` call sites):

| Task | Dispatched from |
|---|---|
| `scan_user` | `api/agent.py` (`"user"`, platforms, run id, `after_commit=db`); `tasks_scan.scan_due_users` (`"schedule"`) |
| `prepare_application` | `api/applications.py`, `api/jobs.py`, `agent_orchestrator.queue_preparations`, `agent_orchestrator.keep_application` |
| `stage_application` | `api/applications.py`, `agent_orchestrator.bot_apply`, `agent_orchestrator.restage_internshala_waiting` |
| `submit_application` | `agent_orchestrator._ready_or_submit`, `approve_application`, `submit_application` (re-queue with `countdown=wait` when rate-limited; `countdown=30` for the single retry) |
| `check_user_email` | `api/agent.py`, `api/auth.py`, `tasks_email.check_all_emails`, `tasks_email.handle_gmail_push` |
| `handle_gmail_push` | `api/files.py` (Gmail Pub/Sub webhook: `data["emailAddress"]`, `historyId`) |
| `linkedin_sync_user` | `api/users.py`, `tasks_sync.linkedin_sync_all` |

### 8.3 Celery Beat schedule (9 entries)

| Beat entry name | Task | Schedule (exact) | Effective cadence |
|---|---|---|---|
| `scan-due-users` | `hireflow.scan_due_users` | `crontab(minute=7)` | hourly at :07 UTC |
| `check-all-emails` | `hireflow.check_all_emails` | `max(60, settings.EMAIL_POLL_MINUTES * 60)` (seconds, float interval) | every 300 s by default |
| `renew-gmail-watches` | `hireflow.renew_gmail_watches` | `crontab(hour=3, minute=17)` | daily 03:17 UTC |
| `interview-reminders` | `hireflow.send_interview_reminders` | `600.0` (seconds) | every 10 min |
| `linkedin-sync` | `hireflow.linkedin_sync_all` | `crontab(hour=6, minute=23)` | daily 06:23 UTC |
| `weekly-summary` | `hireflow.weekly_summary` | `crontab(day_of_week="mon", hour=8, minute=41)` | Mondays 08:41 UTC |
| `progress-digest` | `hireflow.progress_digest` | `crontab(minute=43)` | hourly at :43 (comment: "hourly; ~20:00 local") |
| `retention-cleanup` | `hireflow.retention_cleanup` | `crontab(hour=4, minute=11)` | daily 04:11 UTC |
| `expire-stale-jobs` | `hireflow.expire_stale_jobs` | `crontab(hour=5, minute=3)` | daily 05:03 UTC |

Not on the beat schedule (on-demand only): `scan_user`, `prepare_application`, `stage_application`,
`submit_application`, `linkedin_sync_user`, `check_user_email`, `handle_gmail_push`.

Beat runs as `celery -A app.worker.celery_app beat --loglevel ${LOG_LEVEL:-INFO} -s /data/celerybeat-schedule`
in Docker (entrypoint role `beat`), and with `--schedule backend/data/celerybeat-schedule` from `start.sh`.

### 8.4 Dispatch layer (`backend/app/worker/dispatch.py`)

Purpose: task dispatch that works with or without a Celery worker.

| Item | Behaviour |
|---|---|
| `_executor` | `ThreadPoolExecutor(max_workers=4, thread_name_prefix="hireflow-task")` |
| `_registry: dict[str, Callable]` | filled by `@register(name)` decorators in the 5 task modules |
| `_inline = {"enabled": False}` | toggled by `run_inline` |
| `register(name)` | decorator storing the plain function under `name` |
| `_load_registry()` | if registry empty, imports `tasks_apply, tasks_calendar, tasks_email, tasks_scan, tasks_sync` |
| `use_local_execution()` | `settings.CELERY_TASK_ALWAYS_EAGER or get_redis() is None` (no Redis configured or Redis unreachable; `get_redis` retries a failed connection only after 30 s, connect timeout 2 s, socket timeout 5 s) |
| `class run_inline` | context manager (used by tests / scripts): while active, dispatched tasks run synchronously in the calling thread |
| `_run_local(name, args, countdown)` | inline mode: runs `fn(*args)` immediately **only when no countdown** (delayed retries are dropped); otherwise submits a job to the thread pool that `time.sleep(countdown)` first, then runs `fn(*args)`; exceptions logged as `"Local task %s failed"` |
| `_send(name, args, countdown)` | inline or local execution → `_run_local`; else `celery_app.send_task(f"hireflow.{name}", args=list(args), countdown=countdown)` |
| `enqueue(name, *args, countdown=None, after_commit: Session \| None = None)` | if `after_commit` is given and the session is in a transaction: registers a one-shot SQLAlchemy `"after_commit"` listener that calls `_send` (so the worker always sees the committed rows); otherwise `_send` immediately |

### 8.5 Local scheduler (`scripts/local_scheduler.py`)

"Celery-Beat stand-in for local mode (no Redis)". Started by `./start.sh` when no Redis is found
(`run_bg scheduler "$ROOT" "$PY" scripts/local_scheduler.py`). Adds `backend/` (or the repo root inside the
Docker image) to `sys.path`; logging format `"%(asctime)s [scheduler] %(levelname)s %(message)s"` at
`settings.LOG_LEVEL`; logger name `scheduler`.

| Task name (registry) | Interval (s) | Runs at start-up |
|---|---|---|
| `scan_due_users` | 3600 | yes (first run 20 s after start) |
| `check_all_emails` | `max(60, EMAIL_POLL_MINUTES * 60)` | no |
| `send_interview_reminders` | 600 | no |
| `renew_gmail_watches` | 86400 | no |
| `linkedin_sync_all` | 86400 | no |
| `expire_stale_jobs` | 86400 | no |
| `retention_cleanup` | 86400 | no |
| `weekly_summary` | 604800 (7 days) | no |
| `progress_digest` | 3600 ("sends at ~20:00 in your time zone") | no |

Loop: `signal` handlers for SIGTERM/SIGINT set `_running = False`; calls `dispatch._load_registry()`;
first run time = `now + 20` for start-up tasks else `now + interval`; every 5 s checks due tasks, calls
`dispatch._registry[name]()` directly, logs `"<name> -> <result>"`, logs and swallows exceptions. Tasks
these jobs enqueue (prepare / submit …) run in the same process's dispatch thread pool. Logs
`"Local scheduler started: <names>"` / `"Local scheduler stopped"`.

---

---

## Section 9: Scraper Registry

Source: `backend/app/scrapers/` — 15 modules: `__init__.py`, `base.py`, `ats_detect.py`,
`browser_scraper.py`, `ashby.py`, `generic.py`, `glassdoor.py`, `greenhouse.py`, `indeed.py`,
`internshala.py`, `internships.py`, `lever.py`, `linkedin.py`, `top_companies.py`, `wellfound.py`,
`workday.py` (16 files incl. `__init__`). **12 registered scrapers.**

### 9.1 Registry and dispatch (`scrapers/__init__.py`)

`SCRAPERS: dict[str, type[BaseScraper]]` (insertion order = default scan order):

| Key | Class | Module |
|---|---|---|
| `top_companies` | `TopCompaniesScraper` | `top_companies.py` |
| `internshala` | `InternshalaScraper` | `internshala.py` |
| `internships` | `InternshipListScraper` | `internships.py` |
| `greenhouse` | `GreenhouseScraper` | `greenhouse.py` |
| `lever` | `LeverScraper` | `lever.py` |
| `ashby` | `AshbyScraper` | `ashby.py` |
| `workday` | `WorkdayScraper` | `workday.py` |
| `linkedin` | `LinkedInScraper` | `linkedin.py` |
| `indeed` | `IndeedScraper` | `indeed.py` |
| `glassdoor` | `GlassdoorScraper` | `glassdoor.py` |
| `wellfound` | `WellfoundScraper` | `wellfound.py` |
| `generic` | `GenericScraper` | `generic.py` |

`PLATFORM_TO_SCRAPER`: GREENHOUSE→`greenhouse`, LEVER→`lever`, ASHBY→`ashby`, WORKDAY→`workday`, LINKEDIN→`linkedin`.

- `get_scraper(name) -> BaseScraper` — instantiates `SCRAPERS[name]()`.
- `fetch_job_from_url(url) -> ScrapedJob | None` — "Add job by URL": detect platform → scraper (default
  `generic`); any URL containing `internshala.com/` → `internshala`; if the platform scraper returns `None`
  (and isn't generic), retries with `generic`.
- `__all__`: `SCRAPERS, BaseScraper, RateLimited, ScrapedJob, ScraperError, SearchQuery, detect_ats_platform, fetch_job_from_url, get_scraper, parse_ats_url`.

### 9.2 Base layer (`scrapers/base.py`)

- Exceptions: `ScraperError(Exception)`, `RateLimited(ScraperError)`.
- `@dataclass SearchQuery`: `keywords` (target roles), `locations`, `remote`, `job_types`,
  `posted_within_days=14`, `limit=50`, `sources: dict` (per-platform lists), `search_terms` (typed into a
  site's search box when different from keywords), `focus: LocationFocus | None`, `internships_only=False`,
  `known_urls: frozenset` (skip re-downloading detail pages), `progress(done,total)` callback, `deadline`
  (monotonic time to wrap up). Methods: `time_up()`, `report()`, `is_known(url)`,
  `from_preferences(prefs, limit=50)` (with a location focus and no target locations it searches
  `"<prime city>, <country>"` and `<country>`; internships-only forces `job_types=["internship"]`),
  `matches_title(title)` (uses `job_matcher._role_matches`, ≥ 67 % token match), `matches_location()`
  (always True with a focus; remote always passes; first comma part of a target location substring, or "remote").
- `@dataclass ScrapedJob`: `company_name, role_title, description, source_url, source_platform,
  application_url, location, is_remote, job_type, experience_level, salary_min, salary_max,
  salary_currency, posted_date, deadline_date, external_id, easy_apply, company_logo_url, company_domain,
  requirements, raw`. `finalize()`: HTML→text description, `detect_remote`, `infer_job_type`,
  `infer_experience_level`, `parse_salary` fallback, title/company/location trimmed to 255 chars
  (company defaults `"Unknown"`). `to_dict()`.
- Helpers: `detect_remote(location, description)`, `infer_job_type(title, text)` (intern/co-op/summer
  analyst → INTERNSHIP; contract/temp → CONTRACT; freelance; part-time; else FULL_TIME),
  `infer_experience_level(title, description)` (intern→INTERNSHIP; vp/chief/head of/director→EXECUTIVE;
  lead/principal/staff/manager/architect→LEAD; senior/sr/iii/iv→SENIOR; junior/entry/graduate/new
  grad/associate/i→ENTRY; else MID), `parse_salary(text)` (currencies `$ € £ ₹ C$ A$`, `k` suffix,
  ranges; rejects hourly and values < 10 000), `parse_date(value)` (epoch ms/s, ISO, "today",
  "yesterday", "N days/weeks/months", "Nh", dateutil fallback).
- `class BaseScraper(ABC)`: attributes `platform = ATSPlatform.UNKNOWN`, `rate_key = "unknown"`,
  `requires_browser = False`. HTTP client: `httpx.Client(timeout=25, follow_redirects=True,
  headers={"User-Agent": random choice of automation.browser.USER_AGENTS, "Accept-Language": "en-US,en;q=0.9"})`.
  - `request(method, url)`: first checks `rate_limiter.allow_request(rate_key)` (else `RateLimited`);
    network timeouts / transport errors retried with delays **2 s, 4 s, 8 s** (then `ScraperError`); HTTP
    5xx retried with the same delays; **HTTP 429 → `rate_limiter.pause_platform(rate_key)` (15 min) and
    `RateLimited`**.
  - `get_json(url)`: 404 → `ScraperError("Not found")`, else `raise_for_status()` + `.json()`.
  - `map_sources(items, fetch, query, label)`: fetches boards/pages in a `ThreadPoolExecutor` of
    `min(SCRAPER_BOARD_CONCURRENCY (6), len(items))` workers (`thread_name_prefix="scrape-<rate_key>"`);
    boards not started before `query.deadline` are skipped; one failing board (incl. `RateLimited`, HTTP 403)
    is logged and skipped; results returned in original order; reports progress.
  - `search(query)` (abstract), `fetch_job(url)` (optional, default `None`).
  - `filter(jobs, query)`: drops non-internships when `internships_only` (`intern_level.is_internship`),
    title mismatches, non-remote when `remote`, location mismatches, postings older than
    `posted_within_days` (3650 when 0); with a location focus sorts by `location_tier`; truncates to `query.limit`.

### 9.3 ATS / board detection (`scrapers/ats_detect.py`)

`detect_ats_platform(url)` — hostname regexes, checked in order:

| Platform | Host regex |
|---|---|
| GREENHOUSE | `(^\|\.)greenhouse\.io$` |
| LEVER | `(^\|\.)lever\.co$` |
| ASHBY | `(^\|\.)ashbyhq\.com$` |
| WORKDAY | `(^\|\.)(myworkdayjobs\|myworkdaysite\|workday)\.com$` |
| LINKEDIN | `(^\|\.)linkedin\.com$` |
| INDEED | `(^\|\.)indeed\.(com\|co\.[a-z]{2}\|[a-z]{2})$` |
| GLASSDOOR | `(^\|\.)glassdoor\.(com\|co\.[a-z]{2}\|[a-z]{2})$` |
| WELLFOUND | `(^\|\.)(wellfound\|angel)\.(com\|co)$` |
| BAMBOOHR | `(^\|\.)bamboohr\.com$` |
| ICIMS | `(^\|\.)icims\.com$` |
| TALEO | `(^\|\.)taleo\.net$` |
| SMARTRECRUITERS | `(^\|\.)smartrecruiters\.com$` |
| JOBVITE | `(^\|\.)jobvite\.com$` |

Fallbacks: URL containing `gh_jid=` → GREENHOUSE; any other host → CUSTOM; empty → UNKNOWN.

`@dataclass ATSRef(platform, board, job_id, site, host)`; `parse_ats_url(url)`:
- Greenhouse: `boards.greenhouse.io/{token}/jobs/{id}`, `job-boards.greenhouse.io/{token}/jobs/{id}`,
  `boards.greenhouse.io/embed/job_app?for={token}&token={id}`, `?gh_jid=` fallback (job id digits only).
- Lever: `jobs.lever.co/{company}/{uuid}[/apply]`.
- Ashby: `jobs.ashbyhq.com/{board}/{uuid}[/application]`.
- Workday: `{tenant}.wd5.myworkdayjobs.com/[en-US/]{site}/job/{location}/{title}_{req}` → board = tenant
  (first host label), locale segments `xx-XX` dropped, site = first path part, job_id = `"/job/..."` path.
- LinkedIn: `/jobs/view/[slug-]{digits}` or `currentJobId={digits}`.

### 9.4 Browser helper (`scrapers/browser_scraper.py`)

- `BLOCK_MARKERS = ("cf-challenge", "challenge-platform", "Just a moment...", "px-captcha", "Access Denied", "verify you are human", "unusual traffic")`.
- `extract_assigned_json(html, variable)` — brace-matching parser for `<variable> = {...};` inline JSON.
- `next_data(html)` — parses `<script id="__NEXT_DATA__" type="application/json">`.
- `class BrowserScraper(BaseScraper)`: `requires_browser = True`;
  `browser_get(session, url, wait_selector=None)` → rate-limit check, `page.goto(url, wait_until="domcontentloaded")`,
  429 → pause platform + `RateLimited`, waits ≤ 15 s for `wait_selector`, `pause(1.5, 4)`, `human_scroll`,
  raises `ScraperError("<rate_key>: blocked by bot protection (configure PROXY_URLS)")` when a block marker
  is in the first 20 000 chars of a page shorter than 200 000 chars; `open_session()` → `BrowserSession()`
  (wraps `BrowserUnavailable` in `ScraperError`).

### 9.5 Per-scraper reference

| Class (`rate_key`) | Source platform value | HTTP / browser | Endpoints / URLs | Source config key (`query.sources`) | Auth | Caps / limits | Filtering & notes |
|---|---|---|---|---|---|---|---|
| `GreenhouseScraper` (`greenhouse`) | `GREENHOUSE` | HTTP JSON | `https://boards-api.greenhouse.io/v1/boards/{token}` (board name, cached in class dict `_names`), `.../{token}/jobs?content=true`, `.../{board}/jobs/{id}?questions=true` | `greenhouse_boards` | none | `query.limit`; boards in parallel (`map_sources`) | `BaseScraper.filter` per board. Job URL default `https://job-boards.greenhouse.io/{token}/jobs/{id}`; raw keeps `board_token`, departments, metadata, questions. `application_questions(board, job_id)` maps field types `input_text/textarea→text`, `input_file→file`, `multi_value_single_select→select`, `multi_value_multi_select→checkbox`. |
| `LeverScraper` (`lever`) | `LEVER` | HTTP JSON | `https://api.lever.co/v0/postings/{slug}?mode=json`, `.../{slug}/{id}?mode=json` | `lever_companies` | none | `query.limit` | Commitment → JobType map (full-time, part-time, intern(ship), contract(or), temporary); salary only when `interval == "per-year-salary"`; `is_remote` from `workplaceType == "remote"`; description = description + lists + additional; apply URL `.../{id}/apply`. |
| `AshbyScraper` (`ashby`) | `ASHBY` | HTTP JSON | `https://api.ashbyhq.com/posting-api/job-board/{board}?includeCompensation=true` | `ashby_boards` | none | `query.limit` | Skips `isListed == False`; employment map FullTime/PartTime/Intern/Contract/Temporary; salary from `summaryComponents` with type Salary and interval `None`/`"1 YEAR"`; `fetch_job` lists the whole board and matches by id; apply URL `{jobUrl}/application`. |
| `WorkdayScraper` (`workday`) | `WORKDAY` | HTTP JSON (CXS) | `POST https://{host}/wday/cxs/{tenant}/{site}/jobs` body `{"appliedFacets": {}, "limit": 20, "offset": n, "searchText": term}`; detail `GET .../wday/cxs/{tenant}/{site}{externalPath}` | `workday_sites` (full site URLs) | none | pages of 20 up to `query.limit` per search term; stops on `time_up()` | Title matched before fetching detail; `site_parts(url)` → (host, tenant, site); intern title → INTERNSHIP, timeType part/full; apply URL `<url>/apply`; HTTP ≥ 400 on search → `ScraperError`. |
| `LinkedInScraper` (`linkedin`) | `LINKEDIN` | HTTP HTML (public guest endpoints, no login) | `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords=..&location=..&f_TPR=r{days*86400}[&f_WT=2][&f_JT=F%2CP..]&start=N`; detail `https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}` | — (keywords/locations from prefs; `search_terms` override) | **none for discovery** (the `li_at` cookie is used only by Easy Apply + profile sync) | `start` in 0..min(limit,100) step 25 per keyword×location; `days` clamped 1–30; details fetched **3 at a time**; stops on `RateLimited` or `time_up()` | Remote with no locations → `"United States"`; `JOB_TYPE_FILTER` full-time F, part-time P, contract C, internship I, freelance T; already-known URLs (`query.known_urls`) skip detail download; seniority & employment criteria mapped; external apply URL parsed from `code#applyUrl` (unwraps `url=` redirect); `easy_apply` when no external URL and an apply button exists; raw keeps `external_apply_url`, `external_platform`. |
| `IndeedScraper` (`indeed`) | `INDEED` | **Browser** (stealth Playwright) | `https://www.indeed.com/jobs?q=..&l=..&fromage=min(days,14)[&sc=0kf%3Aattr%28DSQF7%29%3B]`; Indian locations → `https://in.indeed.com`; detail `{base}/viewjob?jk={jobkey}` | — | none | stops at `query.limit` / `time_up()` | Parses `window.mosaic.providerData["mosaic-provider-jobcards"]` JSON; description from `#jobDescriptionText`; known URLs skip detail; `easy_apply = indeedApplyEnabled`; `application_url` = `thirdPartyApplyUrl` or viewjob URL. |
| `GlassdoorScraper` (`glassdoor`) | `GLASSDOOR` | **Browser** | `https://www.glassdoor.com/Job/jobs.htm?sc.keyword=..&locKeyword=..&fromAge=min(days,30)[&remoteWorkType=1]`; India → `https://www.glassdoor.co.in` | — | none | `query.limit` / `time_up()` | Cards `li[data-test='jobListing'], li[data-jobid]`; rating suffix stripped from company; detail pane `[class*='JobDetails_jobDescription']`; known URLs skip detail. |
| `WellfoundScraper` (`wellfound`) | `WELLFOUND` | **Browser** | `https://wellfound.com/role/r/{role-slug}` or `/role/l/{role-slug}/{location-slug}`; job URL `https://wellfound.com/jobs/{id}-{slug}` | — | none | `query.limit` / `time_up()` | Default keyword `"software engineer"`; walks `__NEXT_DATA__` Apollo state joining `JobListing` with `Startup`; `easy_apply=True`; intern jobType → INTERNSHIP. |
| `GenericScraper` (`generic`) | `CUSTOM` (or detected ATS) | HTTP HTML | any career page URL | `career_pages` | none | follows ≤ **15** job-looking links, depth 1 | schema.org `JobPosting` JSON-LD (also `@graph`, `ItemList`); else delegates to ATS boards found in the page (`find_ats_boards`: Greenhouse, Lever, Ashby, Workday regexes) via their scrapers; else follows links matching `/(jobs?\|careers?\|positions?\|openings?)/...` whose text matches the title. `company_from_page` (og:site_name / application-name) → `company_from_host` (strips www/careers/jobs/apply/boards/hire/recruiting/talent/work prefixes, handles `.co.uk`). `fetch_job` falls back to `<h1>/<title>` + main text (≤ 20 000 chars). |
| `InternshipListScraper` (`github`) | detected ATS or `CUSTOM` | HTTP JSON | `LISTS`: `simplify-internships` → `https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/.github/scripts/listings.json`; `vanshb03-internships` → `.../vanshb03/Summer2027-Internships/dev/.github/scripts/listings.json`; `simplify-new-grad` → `.../SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json` (any https URL also accepted) | `internship_lists` (default `DEFAULT_LISTS = ["simplify-internships", "vanshb03-internships"]` when the key is absent) | none | in-process cache **30 min** (`CACHE_SECONDS`), thread-locked | Keeps `active` and `is_visible`; newest first; `clean_url` drops `utm_*` and `ref=Simplify`; dedupe by URL; description synthesised from locations / terms / category / degrees / sponsorship; new-grad lists → FULL_TIME + ENTRY, else INTERNSHIP; raw `listing_source` (later used by `enrich_job` to fetch the real JD). |
| `InternshalaScraper` (`internshala`) | `CUSTOM` | **HTTP first, browser fallback** (`requires_browser = False`; subclass of `BrowserScraper`) | `https://internshala.com/internships/{category}-internship-in-{city}/`, `/internships/work-from-home-{category}-internships/`, `/internships/{category}-internship/`; user URLs first | `internshala_urls` | none for scraping (the synced Internshala session is only used by the apply bot) | `MAX_PAGES = 12` pages per scan (~40 cards each); ≤ 4 categories; ≤ 2 cities (default `delhi`); stops collecting at `limit × 2` cards; then `cap_internshala` (Section 9.7) | `CATEGORY_RULES` map roles → slugs (full-stack, backend, front-end, android/mobile, ML/AI, data science/analytics, python-django, java, web, cloud, cyber-security, software/computer-science, product-management, ui-ux-design, marketing, finance); default `software-development, computer-science`; `city_slug` aliases new-delhi/delhi-ncr→delhi, gurugram→gurgaon, bengaluru→bangalore. Search pages fetched in parallel over HTTP; 403/503/block markers → those pages re-fetched one at a time in one browser session. Title filter skipped (pages are category-scoped). Every job: INTERNSHIP, location `"..., India"`, raw `{"listing_source": "internshala", "apply_on_site": "Internshala", stipend, duration, starts_immediately}`; external id `internshala-{id}`. Errors: `"Internshala blocked the request and no browser is available: ..."`, `"Internshala could not be reached"`. |
| `TopCompaniesScraper` (`top_companies`) | `CUSTOM` (jobs carry their board's platform) | HTTP (delegates) | runs `tasks()` = for every `CATALOG` company: `greenhouse\|token\|name`, `lever\|...`, `ashby\|...`, `workday\|site_url\|name`, and `linkedin\|\|name` for companies hiring via own site | — (catalog-driven) | none | `LINKEDIN_PER_COMPANY = 8` (one results page); all tasks in parallel via `map_sources`; returns up to `max(query.limit, 150)` | Keeps only intern titles (`is_internship`) after `filter`; LinkedIn results kept only when `match_company(job.company_name)` is that company (search term `"<name> intern"`, `job_types=["internship"]`); Workday searched with `keywords=["intern"]`; raw gains `top_company`, `company_tier`; `fetch_job` returns `None`. |

Requests per platform are additionally budgeted by `services/rate_limiter.PLATFORM_LIMITS`
(requests/hour) — see Section 10.4.

### 9.6 Scan pipeline services that consume scrapers

| Module | Purpose | Key functions | Key thresholds / constants |
|---|---|---|---|
| `services/agent_orchestrator.py` (1 536 lines) | The agent "brain": discovery → matching → preparation → staging → approval → submission; implements the 10 behavioural rules + DIRECTIVE 2 (never submit without approval); Swipe Review mode. | `RunLog` (agent_runs log, ≤ 500 entries, `finish()` pushes `agent_run_updated`); `get_master_resume`, `resume_embedding`, `upsert_job` (by `source_url`, then `dedupe_key`), `apply_company_check`, `backfill_company_checks(limit=2000)`, `skip_suspicious_waiting`, `skip_ineligible_waiting`, `verify_companies`, `scan_platforms` (adds `top_companies` first when `scan_top_companies`), `discover_jobs`, `user_source_urls`, `known_source_urls(days=30)` (LinkedIn/Indeed/Glassdoor with ≥ 200-char JD), `ensure_application`, `application_platform`, `run_scan`, `score_applications`, `focus_rank`, `queue_preparations`, `keep_application` / `skip_application` / `undo_review`, `import_job_url`, `resume_strategy` (`original`/`light`/`full`), `render_tailored_pdf`, `prepare_application`, `enrich_job`, `unanswered_questions`, `ready_or_submit`, Internshala helpers (`is_internshala_job`, `internshala_ready`, `internshala_missing`, `bot_apply`, `internshala_submitted_today`, `direct_submit_blocker`, `restage_internshala_waiting`), `build_packet`, `stage_application`, `approve_application`, `mark_self_applied`, `remember_answers`, `submit_application`. | `COMPANY_AI_CHECKS_PER_SCAN = 8`; AI company verdicts reused 30 days; sources wrap up at **80 %** of `SCAN_SOURCE_TIMEOUT_SECONDS` (240) and are dropped at 100 %; embeddings batched by 64 (8 000 chars); `auto_apply_threshold` default 80; `max_applications_per_day` default 25; `RESUME_STRATEGIES = ("original", "light", "full")`; `INTERNSHALA_RECHECK_SECONDS = 50*60`; `internshala_daily_limit` clamped 1–25 (default 15); stage retried once; submit retried once after 30 s; rate-limit wait = platform cooldown + 30 s; temp dirs prefixed `hireflow-`. |
| `services/source_mix.py` | Keeps Internshala from crowding out other sources. | `is_internshala`, `internshala_allowance(others, share, per_scan)`, `cap_internshala(jobs, share, focus, per_scan, known)` → (kept, dropped); ranks kept Internshala postings by company verdict (verified → unverified → suspicious), score, then location tier. | `DEFAULT_SHARE = 25` (%), `DEFAULT_PER_SCAN = 10`, `MIN_KEPT = 3`; share clamped 0–100, per-scan 0–50; allowance = `min(per_scan, max(MIN_KEPT, others*share//(100-share)))`; known URLs don't count. |
| `services/role_focus.py` | Tech focus: keep roles in your stack, drop ones in a stack you skip. | `focus_reasons(job, prefs)`, `drop_off_focus(jobs, prefs)` | Prefs `focus_skills` / `avoid_skills` (both empty = no filter); `_PATTERNS` (ai, llm(s), generative ai/genai, ai agents, agents, rag, ml, nlp, fastapi, java (not javascript), spring boot, prompt engineering, hugging face, vector databases); `_TOPICS` set (too broad to rescue a Java posting); "not your focus" only judged on JDs ≥ 300 chars (or Internshala cards). |
| `services/intern_level.py` | Intern-level roles only, and only ones a student in your year can get. | `Student` dataclass, `academic_year_end`, `internships_only(prefs)` (default True), `graduation_year_from_resume`, `student(prefs, resume_content)`, `with_resume`, `is_internship(title, job_type)`, `names_your_year`, `eligibility_reasons`, `intern_level_reasons`, `drop_ineligible`, `year_fit`, `posting_text` | `DEFAULT_YEAR = 2`, `COURSE_YEARS = 4`; academic year Jul–Jun; regexes `INTERN_TITLE`, `_STAFF_WORD`/`_ABOUT_INTERNS` (jobs *about* interns), PhD/Master's/MBA detection, year restrictions ("final year only", rising seniors…), graduation-year windows, `_EXPERIENCE` (≥ 2 years asked → excluded). |
| `services/location_focus.py` | Location focus (country + prime cities + share) and internship season. | `LocationFocus`, `get_focus`, `location_tier`, `is_indian_location`, `location_tier_sql`, `balance_by_location`, `Season`, `get_season`, `season_status`, `season_rank_sql` | Tiers `TIER_PRIME=0`, `TIER_COUNTRY=1`, `TIER_REMOTE=2`, `TIER_ABROAD=3`; default `country_share` 90 %; `COUNTRY_PLACES["india"]` (≈ 60 cities/states); `FALSE_FRIENDS` (indiana, indianapolis); `DEFAULT_PRIME_CITIES` (Delhi NCR list); `balance_by_location` keeps ≤ 10 foreign postings when none in-country; season statuses `match`/`conflict`/`other_mentioned`/`immediate`/`unknown`. |
| `services/company_catalog.py` | Renowned companies to hunt internships at. | `Company` dataclass (`name, tier, domain, aliases, greenhouse, lever, ashby, workday, linkedin`), `CATALOG`, `normalize_company`, `match_company`, `by_board`, `owns_url` | `TIERS`: big_tech "Big Tech", product "Product companies", startup_india "Indian startups", startup_global "Global startups", ai "AI companies". **125 companies** (big_tech 20, product 35, startup_india 39, startup_global 16, ai 15); boards: Greenhouse 31, Lever 8, Ashby 10, Workday 6; LinkedIn-searched 16. `_LEGAL` suffixes stripped (inc, llc, ltd, pvt, private, corp, india, technologies, software, labs…). |
| `services/company_verifier.py` | Company-check agent: verdict `verified` / `unverified` / `suspicious` per posting. | `CompanyCheck`, `check_company`, `check_job`, `verify_with_llm` (inline prompt, `LLM_SCHEMA`, effort low, task `company_check`), `is_trusted`, `summary` | Base score 50; catalog +35 (+10 when the posting links to its domain); own ATS board +30 (`OWN_BOARDS` / `OWN_BOARD_HOSTS`: Greenhouse, Lever, Ashby, Workday, SmartRecruiters, Workable, Recruitee, BambooHR); Internshala non-catalog −5; −12 per soft flag, −60 per hard flag; `suspicious` = any hard flag or ≥ 3 soft flags; `verified` = (catalog or own board) and score ≥ 70; user-trusted → verified (≥ 90); AI can verify only when it recognises the company and names a domain present in the posting (score ≥ 75), or mark suspicious (≤ 20). 7 hard flag rules (fees/deposits, pay money, WhatsApp/Telegram, earn per day, MLM, no-interview guarantee), 5 soft (personal e-mail, data entry, commission only, urgent hiring, unpaid) + generic name + < 160-char JD; negation window. |
| `services/job_matcher.py` | Preference pre-filter, vector similarity and 5-criterion scoring. | `estimate_years_experience`, `resume_skill_set`, `job_text`, `job_skills`, `filter_reasons` (hard, soft), `prefilter(strict)`, `_role_matches`, `heuristic_evaluation`, `llm_evaluation` (prompt `job_evaluation`, `JOB_EVALUATION_SCHEMA`, effort low), `evaluate_match`, `priority_key` | `SCORE_KEYS` (skills, experience, industry, location, compensation; 0–20 each); threshold default 80; `NO_SPONSORSHIP_PATTERNS`; role match ≥ 0.67 token ratio with synonyms engineer/developer/swe, intern/internship/co-op; location score with focus 20/17/13/4; compensation 15 when unknown. |
| `services/embeddings.py` | Text embeddings for semantic matching (pgvector). | `local_embedding` (feature hashing: words, bigrams ×0.5, skills ×3.0, blake2b buckets), `openai_embeddings` (`{OPENAI_BASE_URL}/embeddings`, `dimensions=DIM`), `ollama_embeddings` (`{ollama_base_url}/api/embed`, `truncate: true`), `fit_dim`, `embed_texts`, `embed_text`, `cosine_similarity` | `DIM = EMBEDDING_DIM` (1536); `OLLAMA_EMBED_CHARS = 4000`; OpenAI input ≤ 8 000 chars; provider failure → local fallback; switching provider requires `scripts/migrate.py --reembed`. |
| `services/scan_progress.py` | Live scan progress for the dashboard bar (`agent_runs.progress` + `scan_progress` WebSocket event). | `ScanCancelled`, `ScanProgress` (`source_started`, `source_step`, `source_finished`, `set_phase`, `percent`, `eta_seconds`, `snapshot`, `flush`, `tick`, `finish`) | `PHASES`: queued 0–2, discovering 2–55, saving 55–62, scoring 62–97, finishing 97–100 (%); `FLUSH_INTERVAL = 0.8` s; Stop detected by re-reading `AgentRun.status == "cancelled"`. |

`run_scan` pipeline order: `scan_platforms` → `SearchQuery.from_preferences(limit=max_jobs_per_source or MAX_JOBS_PER_SOURCE)` +
`known_urls` → `discover_jobs` (≤ `SCAN_SOURCE_CONCURRENCY` sources in parallel) → `drop_ineligible` →
`drop_off_focus` → `balance_by_location` (if focus) → `cap_internshala` → save (`upsert_job` + `ensure_application`
in nested transactions) → `backfill_company_checks` → `verify_companies` → `embed_jobs` → rank by cosine
similarity → `score_applications` (top `MAX_LLM_EVALUATIONS_PER_SCAN` via LLM, `SCAN_LLM_CONCURRENCY` at a
time; Ollama-first lowers both via `llm_budget`; rest heuristic) → Swipe mode: optional `auto_keep_min_score`
auto-keep, notify `scan_completed` (link `/dashboard/review`); classic mode: `queue_preparations` within daily
budget, notify (link `/dashboard/jobs`). `ScanCancelled` → run `cancelled`; any other error → run `failed` +
`agent_error` notification.

---

---

## Section 10: Submitter Registry

Source: `backend/app/submitters/` (`__init__.py`, `base.py`, `form_engine.py`, `generic_submit.py`,
`greenhouse_submit.py`, `internshala_apply.py`, `lever_submit.py`, `linkedin_easy_apply.py`,
`workday_submit.py`) and `backend/app/automation/` (`__init__.py` empty, `browser.py`, `captcha.py`,
`human.py`, `proxy.py`). **6 submitter classes** + `BaseSubmitter`.

### 10.1 Registry (`submitters/__init__.py`)

`SUBMITTERS: dict[ATSPlatform, type[BaseSubmitter]]` = GREENHOUSE → `GreenhouseSubmitter`, LEVER →
`LeverSubmitter`, WORKDAY → `WorkdaySubmitter`, LINKEDIN → `LinkedInEasyApplySubmitter`.
`get_submitter(platform)` → mapped class or **`GenericSubmitter`** fallback (Ashby, custom, unknown, …).
`InternshalaSubmitter` is not in the map: the orchestrator picks it explicitly for Internshala jobs
(`_drive_submitter`). `__all__`: `BaseSubmitter, CandidatePacket, InternshalaSubmitter, SessionExpired,
SubmissionError, SubmissionResult, get_submitter`.

### 10.2 Base contract (`submitters/base.py`)

- `stage(packet)` fills the form and pauses (screenshot); `submit(packet)` fills and clicks Submit. Staging
  and submission run in separate ephemeral browser sessions; the approved packet is replayed on submit.
- Exceptions: `SubmissionError`, `SessionExpired(SubmissionError)`.
- `PROFILE_KINDS = ("first_name", "last_name", "full_name", "email", "phone", "location", "linkedin", "github", "portfolio", "current_company", "current_title")`; `override_key(label) = "label:<normalised label>"`.
- `@dataclass CandidatePacket`: profile fields above + `resume_path`, `cover_letter_text`,
  `cover_letter_path`, `answers`, `resolve_answers` (callback → `question_answerer.answer_questions`),
  `ats_credentials`, `linkedin_cookie`, `internshala_session` (extension cookies), `internshala_user_agent`,
  `application_url`, `company_name`, `role_title`, `overrides` (review-queue corrections, win over everything).
  `full_name`, `override_for(label)`, `profile_value(key)`.
- `@dataclass SubmissionResult`: `success`, `stage` (`staged | submitted | dry_run | failed`, plus
  `already_applied` / `unavailable` from Internshala), `screenshot`, `fields`, `answers`,
  `needs_manual_review`, `review_reason`, `confirmation_number`, `error`, `session_expired`, `final_url`,
  `session_cookies`.
- `class BaseSubmitter`: `platform = "generic"`, `form_root = None`, `submit_selectors` (`button[type=submit]`,
  `input[type=submit]`, "Submit application"/"Submit Application"/"Submit"/"Apply" buttons),
  **`unmapped_review_threshold = 0.30`** (> 30 % unmapped fields → manual review), `session_factory` (default `BrowserSession`).
  - Flow `_drive`: `open_application` → `human.dwell()` (3–15 s) → `fill` → `_solve_captcha` → **screenshot**
    → if staging: `stage="staged"`, success. If submitting: required unmapped field → `failed`; if
    `SUBMISSION_DRY_RUN` → `stage="dry_run"` (no click); else `baseline` → `click_submit` → captcha →
    `wait_for_confirmation` (20 s, polls every 1 s, guards against confirmation text already on the page) →
    **second screenshot** + `final_url` → `submitted` (with confirmation number) or `failed` ("Submission not
    confirmed: <visible errors>").
  - Failure modes: `SessionExpired` → `session_expired=True` + screenshot; `SubmissionError` / `CaptchaError` →
    failed + `needs_manual_review` with the message; any other exception → failed `"<Type>: <msg>"` +
    screenshot; `BrowserUnavailable` → failed (no browser).
  - `fill_fields`: fill pass, then up to **2 follow-up passes** for fields revealed by answers (400 ms wait).
  - `_fill_pass`: resume/cover-letter uploads (file fields) or cover-letter text; user override (verbatim, date
    placeholder disabled); profile kinds; everything else → questions resolved by `resolve()` (stored answers
    first, then `packet.resolve_answers`).
  - `_summarize` manual-review triggers: no fields found ("No form fields were found on the application
    page"); any required unmapped ("Required fields need your input: …"); unmapped ratio > 30 % ("N% of fields
    could not be mapped automatically"); low-confidence generated answers ("Some answers were generated with
    low confidence — please review them").
  - `after_run(session, result)` hook (browser still open).

### 10.3 Submitters

| Class | `platform` | Supported ATS / URLs | Open / flow specifics | Field classification | Submit / confirmation | Failure modes & manual-review triggers |
|---|---|---|---|---|---|---|
| `GreenhouseSubmitter` | `greenhouse` | `boards.greenhouse.io`, `job-boards.greenhouse.io`, embedded `iframe#grnhse_iframe` / `iframe[src*='greenhouse.io']` | Clicks "Apply" / "Apply for this job" / `a[href='#app']` when no file input is visible; follows embedded iframe `src`; form root first match of `#application-form, form#application_form, #application, form[action*='applications'], main form, form` | `question_*` / `job_application[answers…` fields are questions unless they classify as linkedin/github/portfolio; `candidate-location` / "location" → location; `country` → question | `submit_selectors`: "Submit application", `#submit_app`, `input#submit_app`, `button[type=submit]`, `input[type=submit]` | No form root → `SubmissionError("Greenhouse application form not found (posting may be closed)")`. Orchestrator pre-fetches Greenhouse questions via the board API during preparation. |
| `LeverSubmitter` | `lever` | `jobs.lever.co/{company}/{id}/apply` | Appends `/apply`; waits ≤ 15 s for `input[name=email], input[type=file]`; **uploads resume first** (Lever parses it and pre-fills), waits 2.5 s; `form_root = "form#application-form, form.application-form, form"` | `LEVER_NAMES`: name→full_name, email, phone, org→current_company, location, `urls[linkedin]`, `urls[github]`, `urls[portfolio]`/`urls[other]`→portfolio, resume, comments→cover_letter; `cards[...]` / `eeo[...]` → questions | `#btn-submit`, "Submit application", `button[type=submit]` | Form not found → "Lever application form not found (posting may be closed)". |
| `WorkdaySubmitter` | `workday` | `*.myworkdayjobs.com` multi-page SPA | Apply (`adventureButton`) → Apply Manually → `_authenticate`: sign-in with `ats_credentials.workday_password` (or field mapping `workday_password`), else Create Account (verify password, checkbox); up to `MAX_PAGES = 10` pages, uploads resume (`file-upload-input-ref`), clicks `bottom-navigation-next-button` / Save and Continue / Next until the Review page | `WORKDAY_IDS` (legalNameSection first/last, email, phone-number, addressSection_city, linkedInQuestion); any file → resume | `SUBMIT_BUTTON` "Submit" | "Workday 'Apply' button not found (posting may be closed)"; no password → "Workday requires a candidate account. Add a 'workday_password' in Settings → Field mappings."; sign-in fail without create option; verification e-mail sent → "Workday sent an account verification e-mail — verify it, then approve again"; validation errors (`errorMessage`) → manual review; not reaching Review → "Did not reach the Workday review page automatically". |
| `LinkedInEasyApplySubmitter` | `linkedin` | LinkedIn Easy Apply modal | `session_kwargs` injects the **`li_at`** cookie (`linkedin_cookies(li_at)` → `.linkedin.com`, httpOnly, secure, SameSite=None); none → `SessionExpired("LinkedIn session not synced — install the extension and sync your session")`; authwall / `/login` / login form → `SessionExpired("LinkedIn session expired — re-sync it with the browser extension")`; clicks Easy Apply, walks up to `MAX_STEPS = 8` modal steps (Next / Review); unticks "follow company" on the review step | form engine inside `MODAL` | `button[aria-label='Submit application']`; confirmation waits for text "application was sent \| Application submitted \| applied" | "This LinkedIn job is no longer accepting applications"; "You already applied to this job on LinkedIn"; "Easy Apply is not available for this job (external application)"; inline errors → "LinkedIn flagged: …"; "Could not reach the Easy Apply review step"; "Some required Easy Apply questions need your input". Orchestrator marks `linkedin_session_valid = False` + `session_expired` notification. |
| `GenericSubmitter` | `generic` | any unknown ATS / career site (incl. Ashby, demo site) | If no form inputs, clicks first visible "Apply now" / "Apply for this job" / "Apply"; picks the form with the most inputs and tags it `data-aa-form="1"` | `classify_field`, then **LLM field mapping** (`form_field_mapper` prompt, `FORM_MAPPING_SCHEMA`, effort low, task `form_mapping`) for unknown fields: `value_source` profile/resume_file/cover_letter | base selectors | LLM failure → empty mapping (fields become questions). |
| `InternshalaSubmitter` | `internshala` | `internshala.com` internship detail pages (opt-in bot) | `session_kwargs` = `browser_kwargs(cookies, user_agent)` → Playwright cookies, `timezone_id="Asia/Kolkata"`, the synced browser's user agent, **`use_proxy=False`**; none synced → `SessionExpired(NOT_SYNCED)`. Flows: detail → Apply now → easy-apply modal (`#easy_apply_modal`); → `/student/resume` interstitial → "Proceed to application" → `/application/form`; external listing (`a.proceed-cta`) → stop `unavailable` with URL; profile gate (`/student/personal_details`, `/student/resume`, `/student/profile` > 3 s) → stop; `_reach_form` timeout 20 s. Login check: login/sign-up page or prompt → probes `/student/dashboard` in a new tab before declaring `SessionExpired(EXPIRED)`. `after_run` keeps renewed login cookies (`session_cookies`). | Own `EXTRACT_JS` reading Quill cover-letter editor (`#cover_letter_holder .ql-editor`), availability radios (`#confirm_availability_container`, "Other" textarea), `.form-group.additional_question` groups, relocation checkbox (`location_single`), chosen.js selects; leftovers through generic engine; **never uploads a resume** (Internshala attaches the profile resume; reported as a row) | `input#submit`, `button#submit`, "Submit"; success markers `#continue_container`, `#success_modal`, "application submitted successfully"; validation "This field is required" → failure; recommended-internships modal skipped | Messages: `NOT_SYNCED` ("Internshala login not synced — log into Internshala in Chrome and click “Sync Internshala session” in the HireFlow extension"), `EXPIRED`, `ALREADY_APPLIED` (stage `already_applied`, orchestrator marks APPLIED), `PROFILE_GATE`, "Applications are closed…" (stage `unavailable`). Cover letter: salutation/sign-off stripped, ≤ `COVER_LETTER_MAX = 2000` chars. `SESSION_COOKIES = {PHPSESSID, l, sessionToken, persistentSession}`; `has_login`: `is_logged_in == "1"` or `PHPSESSID` + `l`. Module helpers: `internshala_cookies`, `extension_cookies`, `has_login`, `browser_kwargs`, `check_session`, `internshala_cover_letter`, `availability_choice`. All selectors centralised in `SELECTORS`. |

Orchestrator-level rules around submitters (`agent_orchestrator.py`): one Internshala browser per user at a time
(`_internshala_lock`); a refused Internshala login is not retried until the next sync (`_internshala_refused`);
`_may_auto_submit`: Internshala only with the bot ready and (`internshala_auto_submit` or "Apply with the bot");
`apply_on_site` boards never auto-submitted; unverified companies held for manual review unless trusted
(`company_hold_reason`); dry run → back to `PENDING_APPROVAL` with "Dry-run mode (SUBMISSION_DRY_RUN=true): the
final Submit click was skipped."; screenshots stored as `screenshots/<uuid>.png` under the user prefix
(`form_screenshot_url` on stage, `confirmation_screenshot_url` on a successful submit; a login page screenshot is
never stored as the form screenshot).

### 10.4 Form engine (`submitters/form_engine.py`)

- `EXTRACT_JS` — DOM walker returning every fillable control (inputs, selects, textareas, ARIA comboboxes,
  contenteditable) with label (for/aria-labelledby/aria-label/wrapping label/nearby label/placeholder),
  required detection (attribute, `*`, "(required)"), radio/checkbox groups (`data-aa-group`), stable handles
  (`data-aa-id`, counter `window.__aaNext`), options, value, autocomplete, accept, multiple, max_length,
  placeholder. Skips hidden/submit/button/image/reset/search and invisible/disabled controls.
- `FormField` dataclass (`selector`, `descriptor`, `as_question()`); `extract_fields(page, root)`.
- `PROFILE_PATTERNS` / `classify_field(f)`: file → `cover_letter` (if "cover") else `resume`; radio/checkbox/select
  → question; regexes for first/last/full name, email, phone, linkedin, github, portfolio, current company/title,
  location; autocomplete fallbacks (`given-name`, `family-name`, `email`, `tel`, `name`).
- Values: `parse_when` (immediate/asap, "N days/weeks/months", dd/mm vs mm/dd, dateutil), `_format_like`,
  `coerce_value` (number digits, ISO date/month/datetime-local, placeholder date format, max_length clip),
  `value_stuck` (phones compare last 7 digits).
- `fill_field` per type (file, select via `choose_option` — never picks a non-matching option, radio,
  multi/single checkbox, combobox/React-select with shorter retry search, contenteditable, date-like via
  `fill()`, else `human_type` with React/Vue setter fallback `_SET_VALUE_JS`).
- `visible_errors(page)` (≤ 10); `CONFIRMATION_PATTERN` + `looks_submitted(page)` (body text or URL containing
  confirm/thank/success/submitted; confirmation number regex).

### 10.5 Browser automation (`backend/app/automation/`)

| Module | Contents |
|---|---|
| `browser.py` | `USER_AGENTS` (5 Chrome 140/141 UAs: Windows, macOS, Linux), `VIEWPORTS` (6 sizes 1366×768 … 1920×1080), `STEALTH_JS` (hides `navigator.webdriver`, fixes languages/plugins/hardwareConcurrency, `window.chrome`, permissions query, WebGL vendor/renderer spoof), `WEBGL` (4 vendor/renderer pairs), `BrowserUnavailable`, `class BrowserSession` (context manager; kwargs `cookies, storage_state, use_proxy=True, headless (BROWSER_HEADLESS), proxies, timezone_id, user_agent`; launches Chromium with `--disable-blink-features=AutomationControlled --no-sandbox --disable-dev-shm-usage`, optional `PLAYWRIGHT_CHROMIUM_EXECUTABLE`, proxy from `ProxyManager.pick()`; fresh isolated context: random UA/viewport, locale en-US, timezone default `America/New_York`, downloads off, default timeout `BROWSER_TIMEOUT_MS`; `screenshot(full_page=SCREENSHOT_FULL_PAGE)` PNG; `html()`), `linkedin_cookies(li_at)`. |
| `captcha.py` | `PROVIDERS` (`2captcha` → `https://api.2captcha.com`, `anticaptcha`/`anti-captcha` → `https://api.anti-captcha.com`), `TASK_TYPES` (recaptcha → `RecaptchaV2TaskProxyless`, hcaptcha → `HCaptchaTaskProxyless`, turnstile → `TurnstileTaskProxyless`), `CaptchaError`, `CaptchaInfo`, `DETECT_JS` (hCaptcha → Turnstile → reCAPTCHA sitekeys, invisible flag), `INJECT_JS` (writes token into response fields, fires `___grecaptcha_cfg` and `data-callback` callbacks), `detect_captcha`, `solve(info, url, timeout=180)` (`/createTask`, polls `/getTaskResult` every 5 s; no `CAPTCHA_API_KEY` → "CAPTCHA detected but CAPTCHA_API_KEY is not configured"), `solve_on_page(page, retries=3)` (3 attempts 5 s apart; raises `CaptchaError` → manual review). |
| `human.py` | Enabled by `HUMAN_EMULATION`. `pause(min,max)`, `dwell()` 3–15 s, `short_pause()` 0.3–1.2 s, cubic Bézier mouse paths (18–35 steps), `human_click`, `human_type` (80–150 ms/char, 2 % typo + backspace, falls back to `fill()` when disabled or > 400 chars, verifies value), `human_scroll` (400–1400 px in 80–220 px steps). |
| `proxy.py` | `ProxyManager(urls=settings.proxy_urls)`: `enabled`, `pick()` (random healthy proxy), `mark_bad(url, cooldown=600)`, `to_playwright(url)` (server/username/password); module singleton `proxy_manager`. |

### 10.6 Remaining services (`backend/app/services/`)

All 32 service modules are listed in Sections 9.6 and here (`__init__.py` is empty).

| Module | Purpose | Public functions / classes / constants |
|---|---|---|
| `llm.py` | LLM access layer: Anthropic (primary; structured outputs, effort, server-side refusal fallback), OpenAI (secondary), Ollama (free). `LLM_PROVIDER` picks order (`auto` = Anthropic → OpenAI → Ollama, whichever configured). Retry: 3 attempts, 1 s / 2 s / 4 s backoff (`LLM_MAX_RETRIES`), then next provider; no provider → `LLMUnavailable` and services fall back to heuristics. | `JSON_RULE`, `REFUSAL_FALLBACK_BETA = "server-side-fallback-2026-07-01"`, `LLMError`, `LLMUnavailable`, `LLMRefusal`, `load_prompt`, `render_prompt`, `system_prompt`, `extract_json`, `scrub_credentials`, `public_url`, `Provider` protocol, `AnthropicProvider` (streaming `messages.stream` / `beta.messages.stream(betas=[...], fallbacks="default")`, `output_config.effort` + `format: json_schema`, `max_tokens` default `ANTHROPIC_MAX_TOKENS`, disables unsupported features on the fly, truncation → error), `OpenAIProvider` (`{OPENAI_BASE_URL}/chat/completions`, `response_format: json_object`, max_tokens ≤ 16 000), `OllamaProvider` (`/api/chat`, JSON-schema `format`, `num_ctx`, `keep_alive`, `think`, one repair round, `fill_defaults`, prompt fitting to context, `ollama_slots` semaphore = `OLLAMA_CONCURRENCY`), `OllamaError`, `CHARS_PER_TOKEN = 4`, `OLLAMA_MAX_PREDICT = 4096`, `estimate_tokens`, `compact_json_blocks`, `fit_prompt`, `ollama_schema`, `schema_shape`, `shape_problems`, `fill_defaults`, `ollama_headers` (Bearer `OLLAMA_API_KEY` only to `OLLAMA_BASE_URL`), `ollama_error_text`, `ollama_slots`, `configured_providers`, `LLMClient` (`available`, `provider_names`, `primary`, `model_of`, `complete_json`, `complete_json_traced`), `get_llm`, `set_llm`, `active_model`, `llm_budget`. |
| `llm_schemas.py` | JSON schemas for structured outputs (strict objects, all keys required). | helpers `obj`, `arr`, `enum`; `STR/INT/NUM/BOOL/STR_LIST`; `RESUME_SCHEMA`, `JOB_EVALUATION_SCHEMA`, `TAILORED_RESUME_SCHEMA`, `COVER_LETTER_SCHEMA`, `CUSTOM_ANSWERS_SCHEMA`, `EMAIL_INTENT_SCHEMA`, `INTERVIEW_PREP_SCHEMA`, `FORM_MAPPING_SCHEMA`, `LINKEDIN_DIFF_SCHEMA`, `CONNECTION_TEST_SCHEMA`. |
| `ai_setup.py` | AI model status, connection test and Ollama model downloads for Settings › Integrations. | `PROBE_TIMEOUT_SECONDS = 2.0`, `DETECT_TIMEOUT_SECONDS = 0.5`, `PULL_READ_TIMEOUT_SECONDS = 600.0`, `PULL_KEY = "hireflow:ollama-pull:{model}"` (Redis), `PULL_TTL_SECONDS = 86400`, `PullError`, `normalize_model`, `ollama_status` (`/api/version`, `/api/tags`), `llm_section`, `hint_for`, `connection_test` (prompt `connection_test`, max_tokens 256), `pull_progress`, `start_pull` (background `POST /api/pull` stream). |
| `resume_parser.py` | Master resume ingestion PDF/DOCX/TXT/MD → text → structured JSON (LLM, heuristic fallback). | `SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".txt", ".md")`, `ResumeParseError`, `extract_text(filename, data)` (PDF positioned-line rebuild, link URIs), `parse_resume_text(text)` → (resume, `"llm"`/`"heuristic"`), `heuristic_parse`, `resume_to_text`, section aliases, education-table rows. Prompt `resume_parser`, effort low. |
| `resume_tailor.py` | Resume tailoring with a hard truthfulness guard (DIRECTIVE 1). | `is_skill_supported`, `enforce_truthfulness(master, tailored)` → (tailored, violations), `heuristic_tailor`, `tailor_resume` (prompt `resume_tailor`, effort medium) → `{"tailored_resume","changes_made","violations","method"}`, `light_tailor` (reorder only). |
| `cover_letter.py` | Cover letter generation. | `FORMAL_HINTS`, `STARTUP_HINTS`, `detect_tone(job)` (formal / balanced / innovative), `heuristic_cover_letter`, `generate_cover_letter(resume_content, job, company_research="")` (prompt `cover_letter`, effort medium; LLM letter accepted only if ≥ 80 words). |
| `question_answerer.py` | Answer ATS custom questions: saved field mappings → rules → LLM → fallback. | `STANDARD_FIELDS` (30 field-mapping keys: work_authorization, requires_sponsorship, willing_to_relocate, years_experience, salary_expectation, expected_stipend, notice_period, highest_education, how_did_you_hear, over_18, pronouns, gender, race_ethnicity, hispanic_latino, veteran_status, disability_status, address, city, state, postal_code, country, website, phone_country_code, school, degree, major, graduation_year, gpa, date_of_birth, workday_password), `DECLINE_PATTERNS`, `choose_option`, `RULES` (36 regex → answer rules), `rule_based_answer`, `FACTUAL` (eligibility questions never guessed), `LEARNABLE` (6 patterns → field-mapping keys learned from approved answers), `learnable_key`, `fallback_answer`, `answer_questions(questions, resume_content, prefs, field_mappings, job=None, use_llm=True)` (prompt `question_answerer`, effort medium; passwords excluded from mappings sent to the LLM), `mappings_dict`. Salary uses the bottom of the range; stipend vs salary currency kept apart. |
| `review_sheet.py` | The "Ready to submit" review sheet for one application. | `LOW_CONFIDENCE = 0.7`, `needs_attention(row)`, `build_rows(form_fields, custom_answers, overrides, cover_letter, resume_url)`, `review_rows(app, resume_url)`, `SheetEdits`, `apply_edits(app, submitted, cover_letter)`, `missing_required(form_fields, edits)`. |
| `application_service.py` | Status transitions with audit trail + real-time updates. | `set_status(db, application, new_status, changed_by="agent", notes=None, only_forward=False) -> bool` (writes `ApplicationStatusHistory`, pushes update; False when unchanged / rejected). |
| `calendar_manager.py` | Google Calendar integration + AI interview prep notes. | `heuristic_prep`, `generate_prep` (prompt `interview_prep`, effort medium), `build_event_body` (description ends "Created by HireFlow"; `extendedProperties.private.hireflow_interview_id`), `calendar_enabled`, `upsert_calendar_event`, `delete_calendar_event`. |
| `gmail_service.py` | Gmail monitoring: fetch, classify recruiter mail, update applications, label, draft replies. | `LABEL_ROOT = "HireFlow"`, `INTENT_LABELS` (Acknowledged, Rejected, Interview, Assessment, Offer, Follow-up, Action Needed, Job Related), `AUTO_DRAFT_INTENTS = {interview_invite, assessment, offer, info_request}`, `parse_gmail_message`, `create_reply_draft`, `send_reply`, `process_message`, `sync_user_inbox(db, user, max_messages=60)` (lookback `GMAIL_LOOKBACK_DAYS`), `start_watch` (Pub/Sub topic), `watch_needs_renewal` (< 2 days). Ignores mails with subject prefix `[HireFlow]`. |
| `google_oauth.py` | Google OAuth2 (login + Gmail/Calendar scopes), token storage. | `AUTH_URL`, `TOKEN_URL`, `USERINFO_URL`, `REVOKE_URL`, `LOGIN_SCOPES = [openid, email, profile]`, `INTEGRATION_SCOPES` (gmail.readonly, gmail.modify, gmail.labels, calendar.events, calendar.readonly), `GoogleNotConfigured`, `GoogleAuthError`, `build_auth_url(mode='login'\|'connect', user_id, redirect_after)`, `parse_state`, `exchange_code`, `fetch_userinfo`, `store_tokens`, `has_scope`, `get_credentials`, `revoke`, `build_service`. |
| `email_parser.py` | Recruiter e-mail understanding (intent + details). | `ATS_SENDER_DOMAINS`, `GENERIC_MAIL_DOMAINS`, `INTENT_TO_STATUS`, `_RULES`, timezone abbreviations, `MEETING_LINK`, `EmailMessage`, `meeting_platform`, `is_job_related`, `match_application`, `heuristic_parse`, `analyze_email(msg, applications, candidate_name, timezone="UTC")` (prompt `email_parser`, effort low, ≤ 60 applications, body ≤ 12 000 chars), `email_intent_enum`. |
| `linkedin_sync.py` | LinkedIn profile sync with the `li_at` cookie; diffs against the master resume. | `LinkedInSessionExpired`, `fetch_profile_text(li_at, profile_url)` (default `https://www.linkedin.com/in/me/`), `heuristic_diff`, `diff_profile` (prompt `linkedin_profile_diff`, effort low, profile text ≤ 20 000), `sync_linkedin_profile(db, user)` (expiry → "Open LinkedIn in Chrome and click 'Sync session' in the HireFlow extension."). |
| `notifier.py` | Multi-channel notifications: dashboard (DB + WebSocket), e-mail, Discord/Slack. | `ALL`, `NOTIFICATION_SUBJECT_PREFIX = "[HireFlow]"`, `EVENT_CHANNELS` (16 events), `PROGRESS_EVENTS` (sent everywhere when `progress_updates_everywhere`, default on), `send_email` (SMTP or user's Gmail), `send_chat` (Discord/Slack webhooks; per-user prefs override env), `notify(db, user, event_type, title, body="", link=None, data=None) -> Notification \| None`, `push_update(user_id, event_type, data)`. |
| `pdf_generator.py` | ATS-parseable resume/cover-letter PDFs (ReportLab, single column, Vera fonts). | `TEMPLATES = ("classic", "modern")`, `ACCENTS`, `render_resume_pdf(content, template="classic", page_size=...)`, `render_cover_letter_pdf(text, candidate)`. |
| `presets.py` | One-click preference presets. | `STARTUP_GREENHOUSE`, `STARTUP_ASHBY`, `STARTUP_LEVER`, `DEFAULT_INTERN_ROLES`, `MASS_APPLY_PLATFORMS`, `intern_roles`, `AI_ENGINEER_ROLES`, `AI_FOCUS_SKILLS`, `AI_AVOID_SKILLS = ["Java", "Spring Boot"]`, `AI_EXCLUDED_TITLES`, `PRESETS = ("ai-engineer", "internships", "startups", "new-grad", "india-internships")`, `INDIA_PLATFORMS`, `apply_preset(prefs, name)` (mass-apply presets set swipe mode, auto_submit_kept, ≥ 100 apps/day, ≥ 300 jobs/source, ≥ 30 days, scan ≤ 6 h; india-internships sets Summer 2027, India focus, `Asia/Kolkata`; new-grad is the only full-time preset). |
| `privacy.py` | GDPR/CCPA export + deletion. | `SECRET_USER_FIELDS` (hashed_password, google tokens, linkedin_session_cookie, internshala_session, ats_credentials), `export_user_data(db, user)`, `delete_user_data(db, user)`. |
| `progress.py` | Progress digest of every tracked application. | `DIGEST_HOUR = 20`, `FOLLOW_UP_DAYS = 7`, `WAITING`, `GROUPS` (Waiting for a reply / In process / Offers / Closed), `tracked_applications`, `build_digest(db, user, days=1, now=None)` → (title, body, count), `send_due_digests(now=None, force=False, db=None)` (daily, or Sundays if weekly), `send_now(db, user, days=7)`. |
| `rate_limiter.py` | Per-platform rate limits & cooldowns, Redis-backed with in-memory fallback. | `PlatformLimit(requests_per_hour, applications_per_day, cooldown_seconds)`; `PLATFORM_LIMITS`: linkedin (100, 25, 120–300 s), indeed (150, 30, 60–180), greenhouse/lever/ashby (200, 40, 30–60), workday (50, 10, 300–600), glassdoor (100, 20, 120–240), wellfound (100, 20, 60–180), internshala (120, 25, 60–180); `DEFAULT_LIMIT = (100, 20, 60–180)` (also used for `github`, `generic`, `top_companies`); `RATE_LIMIT_COOLDOWN_SECONDS = 900`; `RateLimiter` (`allow_request`, `pause_platform`, `is_paused`, `applications_today`, `can_apply`, `record_application`, `cooldown_seconds`); keys `rl:req:{platform}:{YYYYMMDDHH}`, `rl:pause:{platform}`, `rl:apps:{user}:{platform\|all}:{YYYYMMDD}`, `rl:last:*`, `rl:wait:*`; singleton `rate_limiter`. |
| `text_utils.py` | Text helpers for heuristic paths. | `STOPWORDS`, `SKILL_VOCABULARY`, `SOFT_SKILLS`, skill aliases, `html_to_text`, `normalize_text`, `tokenize`, `canonical_skill`, `extract_skills`, `normalize_company`, `normalize_title`, `dedupe_key(company, title, location)`, `keyword_overlap`, `truncate`, `years_of_experience_required`, `display_skill`, `clip`. |
| `analytics.py` | Analytics & reporting. | `compute_overview(db, user, days=None)` → `totals` (total, discovered, matched, preparing, pending_approval, approved, applied, responses, interviews, offers, rejected, skipped, failed), `by_status`, `rates` (response_rate, interview_rate, offer_rate, avg_days_to_response), `timeline`, `match_distribution`, `platforms`, `top_keywords` (≤ 12), `upcoming_interviews`, `recent_runs`. |

---

---

## Section 11: AI/LLM Prompt Files

Source: `prompts/` — **11 files** (522 lines total). Copied into the backend image at `/app/prompts`
(`PROMPTS_DIR=/app/prompts`); locally `PROMPTS_DIR` defaults to `<repo>/prompts`.

### 11.1 Prompt loading (`backend/app/services/llm.py`)

```python
@lru_cache(maxsize=64)
def load_prompt(name: str) -> str:
    path = Path(settings.PROMPTS_DIR) / f"{name}.txt"
    return path.read_text(encoding="utf-8")

def render_prompt(name: str, **variables: Any) -> str:
    # replaces {{ key }} (regex r"\{\{\s*([a-zA-Z0-9_]+)\s*\}\}");
    # dict/list values -> json.dumps(indent=2, ensure_ascii=False, sort_keys=True, default=str);
    # None / missing -> ""
def system_prompt() -> str:
    return load_prompt("master_system") + JSON_RULE
```

- Every `LLMClient.complete_json_traced(prompt, schema, effort, max_tokens, task)` call sends
  `system_prompt()` as the system message and the rendered task prompt as the user message. `JSON_RULE`
  appends an "OUTPUT FORMAT" block ("Every task you receive through this API expects a single JSON object
  as the complete response. Do not wrap it in markdown fences and do not add commentary before or after it.").
- Responses are parsed by `extract_json` (fences / stray prose tolerated; must be a JSON object).
- Effort defaults to `ANTHROPIC_EFFORT` when the caller passes none. Ollama: JSON blocks inside `<tag>`
  sections are compacted and the biggest blocks shortened to fit `OLLAMA_NUM_CTX` (protected blocks:
  `questions`, `form_fields`, `candidate`, `interview_details`, `user_preferences`).
- One inline prompt is **not** a file: the company legitimacy check (`company_verifier._prompt`, task
  `company_check`, schema `LLM_SCHEMA` = `{recognized: bool, official_domain: str, legit: "yes"|"no"|"unsure", concerns: [str]}`).

### 11.2 Prompt inventory

| File | Purpose | Placeholders (`{{…}}`) | Output JSON shape | Loaded by (function · task · schema · effort) |
|---|---|---|---|---|
| `master_system.txt` (218 lines) | System prompt for every call. Heading `# HIREFLOW — MASTER AGENT SYSTEM PROMPT`; "You are **HireFlow**, an elite autonomous career management agent…". CORE DIRECTIVES: 1 ABSOLUTE TRUTHFULNESS, 2 USER SOVEREIGNTY, 3 ATS OPTIMIZATION, 4 STRATEGIC APPLICATION; AVAILABLE CAPABILITIES (### Job Discovery: search_jobs, evaluate_job_match; ### Resume Management: get_master_resume, tailor_resume, generate_resume_pdf; ### Cover Letters: generate_cover_letter; ### Application: detect_ats_platform, fill_application, take_screenshot, submit_application, stage_for_approval; ### Communications: check_emails, parse_email_intent, draft_reply, create_calendar_event; ### Database: store_application, update_status, get_user_preferences, get_field_mappings); TASK SPECIFICATIONS (### TASK: JOB MATCH EVALUATION, RESUME TAILORING, COVER LETTER GENERATION, CUSTOM QUESTION ANSWERING, EMAIL INTENT PARSING); BEHAVIORAL RULES 1–10. | none (`{max_applications_per_day}` appears with **single** braces in rule 3 and is never substituted) | n/a (JSON enforced by `JSON_RULE`) | `llm.system_prompt()` via `load_prompt("master_system")` — every provider call. |
| `connection_test.txt` (8) | Settings "Test AI" check: reachable + answers in JSON. | none | `{"ok": true, "reply": "..."}` (≤ 15 words) | `ai_setup.connection_test` · `connection_test` · `CONNECTION_TEST_SCHEMA` · low · `max_tokens=256` (uses `complete_json_traced` to report the provider). |
| `cover_letter.txt` (32) | 3-paragraph cover letter (hook, value prop, culture fit + CTA), 200–300 words, starts "Dear Hiring Team," ends "Sincerely,\n<name>", tone formal/balanced/innovative, no fabricated claims. | `candidate_name`, `role_title`, `company_name`, `job_description_text`, `resume_json`, `company_research` | `{"cover_letter": "...", "tone": "formal\|balanced\|innovative", "word_count": int}` | `cover_letter.generate_cover_letter` · `cover_letter` · `COVER_LETTER_SCHEMA` · medium (JD ≤ 10 000 chars; `company_research` default "(none — rely on the job description)"; accepted when ≥ 80 words). |
| `email_parser.txt` (39) | Classify recruiter e-mail intent (acknowledgment, rejection, interview_invite, assessment, offer, follow_up, info_request, generic), map `status_update` (acknowledged, rejected, screening, interview, assessment, final_round, offer, none), extract details, draft a reply. | `today`, `timezone`, `candidate_name`, `applications_json`, `sender`, `subject`, `received_at`, `body` | `{"intent", "confidence", "company_name", "matched_application_id", "extracted_details": {"interview_date", "interview_type", "duration_minutes", "meeting_link", "interviewer_name", "deadline", "next_steps"}, "suggested_reply", "urgency": "high\|medium\|low", "status_update"}` | `email_parser.analyze_email` · `email_parse` · `EMAIL_INTENT_SCHEMA` · low (≤ 60 applications, body ≤ 12 000 chars, `today` as "%A %Y-%m-%d"). |
| `form_field_mapper.txt` (31) | Map unknown application-form fields to candidate data. | `candidate_json`, `company_name`, `role_title`, `fields_json` | `{"mappings": [{"field_id", "value_source": "profile\|resume_file\|cover_letter\|answer\|skip", "profile_key", "value", "confidence", "needs_user_review"}]}` | `submitters/generic_submit.GenericSubmitter.llm_mapping` · `form_mapping` · `FORM_MAPPING_SCHEMA` · low (≤ 25 options per field). |
| `interview_prep.txt` (27) | Interview briefing: prep notes, inferred company research, 8–12 likely questions with answer outlines. | `interview_type`, `role_title`, `company_name`, `job_description_text`, `resume_json`, `interview_details_json` | `{"prep_notes": "...", "company_research": "...", "likely_questions": [{"question", "answer_outline"}]}` | `calendar_manager.generate_prep` · `interview_prep` · `INTERVIEW_PREP_SCHEMA` · medium (JD ≤ 10 000; details: scheduled_at, interviewers, platform). |
| `job_evaluation.txt` (42) | Score fit 0–20 on skills / experience / industry / location / compensation (15 when no salary); `match_score` = sum; `proceed_with_application` rule. | `threshold`, `user_preferences_json`, `master_resume_json`, `company_name`, `role_title`, `location`, `salary`, `job_description_text` | `{"evaluation": {"match_score", "skills_match", "experience_match", "industry_match", "location_match", "compensation_match", "proceed_with_application", "reasoning", "missing_skills", "strong_matches"}}` | `job_matcher.llm_evaluation` · `job_evaluation` · `JOB_EVALUATION_SCHEMA` · low (JD ≤ 14 000; prefs subset: target_roles, target_locations, remote_preference, salary_min/max, experience_level, industries, companies_to_avoid/target, job_types, location_focus, internship_season, focus_skills, avoid_skills). Scores clamped 0–20 and re-summed in code. |
| `linkedin_profile_diff.txt` (17) | Detect substantive LinkedIn profile changes vs the master resume. | `master_resume_json`, `profile_text` | `{"has_changes": bool, "changes": [{"section", "change", "linkedin_value"}], "summary": "one sentence"}` | `linkedin_sync.diff_profile` · `linkedin_diff` · `LINKEDIN_DIFF_SCHEMA` · low (profile text ≤ 20 000). |
| `question_answerer.txt` (49) | Answer application-form questions (11 rules: field mappings first, factual from resume, subjective 60–150 words grounded in resume, Yes/No, salary = bottom of range, exact option text, EEO decline, number/date formats, max_length, only known links, confidence < 0.7 → needs_user_review). | `salary_hint`, `today`, `company_name`, `role_title`, `job_description_text`, `resume_json`, `field_mappings_json`, `questions_json` | `{"custom_answers": [{"question", "field_type": "text\|select\|radio\|checkbox\|number", "answer", "confidence", "needs_user_review"}]}` | `question_answerer.answer_questions` · `question_answering` · `CUSTOM_ANSWERS_SCHEMA` · medium (JD ≤ 6 000; password mappings excluded; `salary_hint` = "<min> - <max> <currency>" or "not specified - ask the user"). |
| `resume_parser.txt` (24) | Raw resume text → structured JSON, facts copied exactly, skills split technical/languages/tools/soft_skills. | `resume_text` | `{"personal_info": {name, email, phone, location, linkedin, github, portfolio}, "summary", "education": [{institution, degree, field, gpa, start_date, end_date, highlights}], "experience": [{company, title, start_date, end_date, location, bullets}], "projects": [{name, description, technologies, url}], "skills": {technical, languages, tools, soft_skills}, "certifications": [{name, issuer, date}], "awards": []}` | `resume_parser.parse_resume_text` · `resume_parse` · `RESUME_SCHEMA` · low (LLM result accepted only if it has experience, education or technical skills; else heuristic). |
| `resume_tailor.txt` (35) | Tailor the master resume under DIRECTIVE 1: rewrite summary, reorder/reword bullets keeping metrics, reorder skills (implicit skills only when evidenced), order projects, copy education/certs/personal info. | `company_name`, `role_title`, `job_description_text`, `master_resume_json` | `{"tailored_resume": {<same structure as the master resume>}, "changes_made": [..]}` | `resume_tailor.tailor_resume` · `resume_tailor` · `TAILORED_RESUME_SCHEMA` · medium (JD ≤ 14 000; output passed through `enforce_truthfulness`). |

Branding inside prompts: only `master_system.txt` names the product (`HIREFLOW` heading, `**HireFlow**`
intro). Tests (`test_llm.py::test_system_prompt_contains_directives`, `test_render_prompt_substitutes_json_and_text`)
exercise loading and substitution.

---

---

## Section 12: Browser Extension (Manifest V3)

Source: `extension/` — `manifest.json`, `background.js`, `content.js`, `popup.html`, `popup.js`,
`icons/icon16.png` (16×16 RGBA PNG), `icons/icon48.png` (48×48), `icons/icon128.png` (128×128).
Packaged by CI as `hireflow-extension.zip` (artifact `hireflow-extension`).

### 12.1 `manifest.json`

| Key | Value |
|---|---|
| `manifest_version` | `3` |
| `name` | `"HireFlow — Session Sync"` |
| `short_name` | `"HireFlow"` |
| `version` | `"1.1.1"` |
| `description` | `"Securely syncs your LinkedIn and Internshala sessions to your own HireFlow dashboard so the agent can apply with your accounts."` |
| `permissions` | `["cookies", "storage", "alarms"]` |
| `host_permissions` | `https://www.linkedin.com/*`, `https://*.linkedin.com/*`, `https://internshala.com/*`, `https://*.internshala.com/*` |
| `optional_host_permissions` | `http://*/*`, `https://*/*` (the dashboard origin is requested at runtime) |
| `background` | `{ "service_worker": "background.js" }` |
| `content_scripts` | one entry: `matches: ["https://www.linkedin.com/*"]`, `js: ["content.js"]`, `run_at: "document_idle"` |
| `action` | `default_title: "HireFlow"`, `default_popup: "popup.html"`, `default_icon: {16: "icons/icon16.png", 48: "icons/icon48.png", 128: "icons/icon128.png"}` |
| `icons` | `{16: "icons/icon16.png", 48: "icons/icon48.png", 128: "icons/icon128.png"}` |

### 12.2 `background.js` (service worker)

Header comment: HireFlow extension service worker; LinkedIn `li_at` read only when logged in; Internshala
cookies (httpOnly included) only when logged in and only after the first manual "Sync Internshala session";
both sent only to *your* HireFlow dashboard over HTTPS with a limited-scope extension token; stored
encrypted (AES-256-GCM) by the backend.

| Constant | Value |
|---|---|
| `SYNC_ALARM` | `"hireflow-linkedin-sync"` |
| `SYNC_EVERY_MINUTES` | `12 * 60` (720 min) |
| `INTERNSHALA_DOMAIN` | `"internshala.com"` |
| `INTERNSHALA_SESSION_COOKIES` | `["PHPSESSID", "l", "is_logged_in", "sessionToken", "persistentSession"]` |

`chrome.storage.local` keys: `dashboardUrl`, `token`, `profileUrl`, `lastSync`, `lastError`, `lastReason`,
`internshalaEnabled`, `lastInternshalaSync`, `lastInternshalaError`.

Functions:
- `getConfig()` — reads storage; strips trailing slashes from `dashboardUrl`.
- `readLinkedInCookie()` — `chrome.cookies.get({url: "https://www.linkedin.com", name: "li_at"})`.
- `syncSession(reason="manual")` — requires dashboard URL + token ("Set your dashboard URL and extension
  token first."); no `li_at` → "You're not logged into LinkedIn in this browser."; `POST
  {dashboardUrl}/api/v1/users/me/integrations/linkedin-cookie`, headers `Content-Type: application/json`,
  `Authorization: Bearer <token>`, body `{li_at, profile_url: profileUrl || null}`; 401 → "Token rejected —
  generate a new extension token in Settings → Integrations."; other → `Sync failed (<status>) <detail>`;
  success stores `lastSync`, clears `lastError`, sets `lastReason`, clears the badge text; network error →
  `Could not reach <url>: <err>`.
- `isInternshalaDomain(domain)`; `readInternshalaCookies()` — `chrome.cookies.getAll({domain:
  "internshala.com"})` mapped to `{name, value, domain, path, secure, httpOnly, sameSite, expirationDate,
  hostOnly}`; `internshalaLoggedIn(cookies)` — `is_logged_in === "1"` or (`PHPSESSID` and `l`).
- `syncInternshala(reason="manual")` — non-manual syncs require `internshalaEnabled` ("Click “Sync
  Internshala session” once to turn on Internshala sync."); not logged in → "You're not logged into
  Internshala in this browser."; `POST {dashboardUrl}/api/v1/users/me/integrations/internshala-session`,
  body `{cookies, reason, user_agent: navigator.userAgent}`; 401 same token message; **409** (disconnected in
  the dashboard) sets `internshalaEnabled: false`; success stores `lastInternshalaSync`, clears
  `lastInternshalaError`, sets `internshalaEnabled: true`.

Event listeners:
- `chrome.runtime.onInstalled` and `chrome.runtime.onStartup` → `chrome.alarms.create(SYNC_ALARM, {periodInMinutes: 720})`.
- `chrome.alarms.onAlarm` (`SYNC_ALARM`) → `syncSession("scheduled")` + `syncInternshala("scheduled")`.
- `chrome.cookies.onChanged` (1): `li_at` on a `linkedin.com` domain, not removed → debounce **5000 ms** → `syncSession("cookie-changed")`.
- `chrome.cookies.onChanged` (2): an Internshala session cookie (list above), not removed → debounce 5000 ms → `syncInternshala("cookie-changed")`.
- `chrome.runtime.onMessage` handlers:

| `message.type` | Action / response |
|---|---|
| `"sync"` | `syncSession("manual")` → `{ok, lastSync}` or `{ok: false, error}` (async, returns `true`) |
| `"sync-internshala"` | `syncInternshala("manual")` → same shape |
| `"profile-url"` | when `message.url` contains `linkedin.com/in/`: stores `profileUrl` = URL without query string |
| `"status"` | `{...config, token: "set" \| null, loggedIn: !!li_at, internshala: {loggedIn, lastSync, lastError, enabled}}` |
| anything else | returns `false` |

### 12.3 `content.js`

Runs on `https://www.linkedin.com/*` at `document_idle`. Looks for the signed-in member's profile link
(`a.global-nav__primary-link-me-menu-trigger[href*='/in/']`,
`a[data-control-name='identity_welcome_message'][href*='/in/']`, `.feed-identity-module a[href*='/in/']`)
and sends `{type: "profile-url", url}`; if not found, retries every 1500 ms, up to 10 attempts. Never reads
messages or other page content.

### 12.4 `popup.html` / `popup.js`

`popup.html` — `<title>HireFlow</title>`; 320 px wide; CSS variables (`--primary: #4f46e5`, `--fg`, `--muted`,
`--border`, `--ok: #059669`, `--err: #dc2626`, `--bg`) with a `prefers-color-scheme: dark` override.

| Element | Details |
|---|---|
| Header | `<h1>` with `icons/icon48.png` + "HireFlow"; subtitle "Session sync — LinkedIn & Internshala" |
| `form#config` | `input#dashboardUrl` (`type=url`, placeholder `http://localhost:3000`, `required`); `input#token` (`type=password`, placeholder "Settings → Integrations → Generate extension token"); submit button "Save settings" (class `secondary`) |
| Buttons | `#sync` "Sync LinkedIn session", `#syncInternshala` "Sync Internshala session" |
| Status panel | LinkedIn: `#login`, `#lastSync` ("never"), `#message`; Internshala: `#internshalaLogin`, `#internshalaLastSync`, `#internshalaMessage` |
| Hint | "Nothing is sent anywhere except your own dashboard (the URL above), where your sessions are stored encrypted. They re-sync every 12 hours and whenever LinkedIn or Internshala renews your login; Internshala starts after your first manual sync." |

`popup.js`:
- `RELOAD` = "Reload the extension: open chrome://extensions, click ↻ on HireFlow, then open this popup
  again." — used when the background worker doesn't answer (`ask()` wraps `chrome.runtime.sendMessage`).
- `setMessage(text, ok, id="message")` (classes `ok`/`err`), `showLogin(id, loggedIn)` → "✓ logged in" /
  "not logged in".
- `refresh()` — `status` message; fills dashboard URL; token placeholder "•••••••• (saved — paste to
  replace)" when a token is stored; last-sync times via `toLocaleString()` or "never"; shows `lastError`;
  if the status has no `internshala` block (old background) → "reload needed" + `RELOAD`.
- Save handler — trims and strips trailing slashes; validation via `new URL(...)`, error "Enter a valid
  URL, e.g. https://hireflow.example.com"; requests `chrome.permissions.request({origins: ["<origin>/*"]})`
  (denied → "Permission to contact your dashboard was denied."); stores `dashboardUrl` (+ `token` only if
  typed); clears the token box; "Settings saved.".
- Sync buttons — disabled with label "Syncing…" during the request; success messages "Synced! Easy Apply is
  ready in your dashboard." and "Synced! Turn on the Internshala bot in Settings → Integrations."; errors shown
  in the respective message area; `refresh()` afterwards.

Backend counterparts: `POST /api/v1/users/me/integrations/linkedin-cookie` and
`POST /api/v1/users/me/integrations/internshala-session` (extension-token auth, values never returned);
tokens from Settings › Integrations (`EXTENSION_TOKEN_EXPIRE_DAYS = 180`).

---

---

## Section 13: Infrastructure & Deployment

### 13.1 `docker-compose.yml` (local / single machine)

Header usage: `cp .env.example .env` → `docker compose up --build`; dashboard http://localhost:3000, API docs
http://localhost:8000/docs; Ollama: host app via `host.docker.internal`, or the `ollama` profile
(`COMPOSE_PROFILES=ollama` + `OLLAMA_BASE_URL=http://ollama:11434`, then
`docker compose exec ollama ollama pull qwen3.5:4b` or "Download model" in Settings).

Project `name: hireflow`. Shared anchor `x-backend: &backend`:

| Key | Value |
|---|---|
| `build` | `context: .`, `dockerfile: backend/Dockerfile` |
| `init` | `true` (reaps Chromium child processes) |
| `image` | `hireflow-backend:local` |
| `env_file` | `.env` with `required: false` |
| `environment` (`&backend-env`) | `DATABASE_URL=postgresql+psycopg://hireflow:hireflow@postgres:5432/hireflow`, `REDIS_URL=redis://redis:6379/0`, `LOCAL_STORAGE_PATH=/data/storage`, `FRONTEND_URL=${FRONTEND_URL:-http://localhost:3000}`, `PUBLIC_API_URL=${PUBLIC_API_URL:-http://localhost:8000}`, `CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:3000}` |
| `volumes` | `storage:/data` |
| `extra_hosts` | `host.docker.internal:host-gateway` (reach the demo site / host Ollama, Linux too) |
| `depends_on` | `postgres` (service_healthy), `redis` (service_healthy) |
| `restart` | `unless-stopped` |

| Service | Image / build | Command / role | Env | Ports | Volumes | Healthcheck | depends_on | Other |
|---|---|---|---|---|---|---|---|---|
| `postgres` | `pgvector/pgvector:pg16` | default | `POSTGRES_USER=hireflow`, `POSTGRES_PASSWORD=hireflow`, `POSTGRES_DB=hireflow` | `5432:5432` | `pgdata:/var/lib/postgresql/data` | `pg_isready -U hireflow -d hireflow`, 5 s / 5 s / 20 retries | — | `restart: unless-stopped` |
| `redis` | `redis:7-alpine` | `redis-server --appendonly yes` | — | — | `redisdata:/data` | `redis-cli ping`, 5 s / 3 s / 20 | — | `restart: unless-stopped` |
| `api` | `*backend` | `["api"]` | backend env | `8000:8000` | `storage:/data` | image `HEALTHCHECK` (`curl -fsS http://localhost:8000/health`) | postgres, redis healthy | — |
| `worker` | `*backend` | `["worker"]` | backend env | — | `storage:/data` | `celery -A app.worker.celery_app inspect ping -d celery@$$HOSTNAME --timeout 10`, interval 60 s, timeout 30 s, start_period 30 s | `api` healthy (replaces the anchor's depends_on) | `shm_size: "1gb"` (Chromium) |
| `beat` | `*backend` | `["beat"]` | backend env | — | `storage:/data` | `disable: true` | `api` healthy | — |
| `frontend` | build `context: .`, `dockerfile: frontend/Dockerfile`, arg `BACKEND_URL=http://api:8000`; image `hireflow-frontend:local` | image CMD `node server.js` | `BACKEND_URL=http://api:8000` | `3000:3000` | — | image `HEALTHCHECK` (wget `/`) | `api` healthy | `restart: unless-stopped` |
| `ollama` | `ollama/ollama` | default | `OLLAMA_KEEP_ALIVE=${OLLAMA_KEEP_ALIVE:-30m}`, `OLLAMA_NUM_PARALLEL="1"`, `OLLAMA_CONTEXT_LENGTH=${OLLAMA_NUM_CTX:-8192}` | none (unauthenticated API; add `127.0.0.1:11434:11434` to use it from the host) | `ollama-models:/root/.ollama` | `ollama list`, 15 s / 10 s / 20 | — | `profiles: ["ollama"]`, `restart: unless-stopped` |

Volumes: `pgdata`, `redisdata`, `storage`, `ollama-models`.

### 13.2 `docker-compose.prod.yml` (single VM + automatic HTTPS)

Header: point DNS for `$DOMAIN` at the server; `cp .env.example .env` and set `DOMAIN`, `SECRET_KEY`,
`ENCRYPTION_KEY`, `POSTGRES_PASSWORD` (+ API keys); `docker compose -f docker-compose.prod.yml up -d --build`;
free AI via `WITH_OLLAMA=1 scripts/server-setup.sh` or `COMPOSE_PROFILES=ollama`, `LLM_PROVIDER=ollama`,
`OLLAMA_BASE_URL=http://ollama:11434`, `OLLAMA_MODEL=qwen3.5:4b`; AWS ECS/Fargate + Vercel via the deploy workflows.

Project `name: hireflow-prod`. Anchor `x-backend`:

| Key | Value |
|---|---|
| `build` | `context: .`, `dockerfile: backend/Dockerfile` |
| `init` | `true` |
| `image` | `hireflow-backend:prod` |
| `env_file` | `.env` (required) |
| `environment` | `ENVIRONMENT=production`, `DATABASE_URL=postgresql+psycopg://hireflow:${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD}@postgres:5432/hireflow`, `REDIS_URL=redis://redis:6379/0`, `LOCAL_STORAGE_PATH=/data/storage`, `FRONTEND_URL=https://${DOMAIN:?set DOMAIN}`, `PUBLIC_API_URL=https://${DOMAIN}`, `CORS_ORIGINS=https://${DOMAIN}`, `COOKIE_SECURE="true"`, `SECRET_KEY=${SECRET_KEY:?set SECRET_KEY}`, `ENCRYPTION_KEY=${ENCRYPTION_KEY:?set ENCRYPTION_KEY}` |
| `volumes` | `storage:/data` |
| `extra_hosts` | `host.docker.internal:host-gateway` (an Ollama installed on the server itself) |
| `depends_on` | postgres, redis (service_healthy) |
| `restart` | `always` |
| `logging` | `json-file`, `max-size: "20m"`, `max-file: "5"` |

| Service | Image / build | Command | Env | Ports | Volumes | Healthcheck | depends_on | Resources / other |
|---|---|---|---|---|---|---|---|---|
| `postgres` | `pgvector/pgvector:pg16` | default | `POSTGRES_USER=hireflow`, `POSTGRES_PASSWORD=${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD}`, `POSTGRES_DB=hireflow` | none | `pgdata` | `pg_isready -U hireflow -d hireflow`, 10 s / 5 s / 20 | — | `restart: always` |
| `redis` | `redis:7-alpine` | `redis-server --appendonly yes` | — | none | `redisdata:/data` | `redis-cli ping`, 10 s / 3 s / 20 | — | `restart: always` |
| `api` | `*backend` | `["api"]` | as anchor | none (behind Caddy) | storage | image HEALTHCHECK | postgres, redis | `deploy.resources.limits: cpus "2", memory 2g` |
| `worker` | `*backend` | `["worker"]` | as anchor | none | storage | celery inspect ping (60 s / 30 s / start 30 s) | `api` healthy | `shm_size: "2gb"`; limits `cpus "4", memory 6g` |
| `beat` | `*backend` | `["beat"]` | as anchor | none | storage | disabled | `api` healthy | — |
| `frontend` | build arg `BACKEND_URL=http://api:8000`; image `hireflow-frontend:prod` | `node server.js` | `BACKEND_URL=http://api:8000` | none | — | image HEALTHCHECK | `api` healthy | `restart: always` |
| `caddy` | `caddy:2-alpine` | default | `DOMAIN=${DOMAIN}` | `80:80`, `443:443` | `./Caddyfile:/etc/caddy/Caddyfile:ro`, `caddy_data:/data`, `caddy_config:/config` | — | `frontend`, `api` | `restart: always` |
| `ollama` | `ollama/ollama` | default | `OLLAMA_KEEP_ALIVE=${OLLAMA_KEEP_ALIVE:-30m}`, `OLLAMA_NUM_PARALLEL="1"`, `OLLAMA_CONTEXT_LENGTH=${OLLAMA_NUM_CTX:-8192}` | none (never publish 11434) | `ollama-models:/root/.ollama` | `ollama list`, 30 s / 10 s / 20 | — | `profiles: ["ollama"]`, `restart: always`, memory limit 16g, logging json-file 20m × 3 |

Volumes: `pgdata`, `redisdata`, `storage`, `caddy_data`, `caddy_config`, `ollama-models`.

### 13.3 `backend/Dockerfile`

Header: "HireFlow backend image (API, Celery worker and beat share it)"; build from repo root:
`docker build -f backend/Dockerfile -t hireflow-backend .`

| Step | Detail |
|---|---|
| Base | `ARG PLAYWRIGHT_VERSION=1.56.0`; `FROM mcr.microsoft.com/playwright/python:v${PLAYWRIGHT_VERSION}-noble` (Chromium + system libs preinstalled) |
| ENV | `PYTHONDONTWRITEBYTECODE=1`, `PYTHONUNBUFFERED=1`, `PIP_NO_CACHE_DIR=1`, `PIP_DISABLE_PIP_VERSION_CHECK=1`, `PIP_BREAK_SYSTEM_PACKAGES=1`, `PLAYWRIGHT_BROWSERS_PATH=/ms-playwright`, `PROMPTS_DIR=/app/prompts`, `LOCAL_STORAGE_PATH=/data/storage` |
| Workdir | `/app` |
| Deps | `COPY backend/requirements.txt` → `pip install -r requirements.txt "playwright==${PLAYWRIGHT_VERSION}"` |
| Code | `COPY backend/ /app/`, `COPY prompts/ /app/prompts/`, `COPY scripts/ /app/scripts/` |
| Perms | `mkdir -p /data/storage`, `chmod +x /app/docker-entrypoint.sh`, `chown -R pwuser:pwuser /app /data`; `USER pwuser` |
| Port | `EXPOSE 8000` |
| Healthcheck | `--interval=30s --timeout=5s --start-period=40s CMD curl -fsS http://localhost:8000/health \|\| exit 1` |
| Entrypoint / CMD | `ENTRYPOINT ["/app/docker-entrypoint.sh"]`, `CMD ["api"]` |

### 13.4 `backend/docker-entrypoint.sh` roles (`#!/bin/sh`, `set -e`)

| Role (`$1`) | Command |
|---|---|
| `api` | `python scripts/migrate.py` then `exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${API_WORKERS:-2}" --proxy-headers --forwarded-allow-ips="*"` |
| `worker` | `exec celery -A app.worker.celery_app worker -Q default,browser --concurrency "${WORKER_CONCURRENCY:-2}" --max-tasks-per-child 50 --loglevel "${LOG_LEVEL:-INFO}"` |
| `beat` | `exec celery -A app.worker.celery_app beat --loglevel "${LOG_LEVEL:-INFO}" -s /data/celerybeat-schedule` |
| `migrate` | `exec python scripts/migrate.py` |
| `seed` | `shift; exec python scripts/seed_db.py "$@"` |
| anything else | `exec "$@"` |

### 13.5 `frontend/Dockerfile` (Next.js standalone, 3 stages)

Header: "HireFlow dashboard (Next.js standalone)"; `docker build -f frontend/Dockerfile --build-arg BACKEND_URL=http://api:8000 -t hireflow-frontend .`

| Stage | Base | Steps |
|---|---|---|
| `deps` | `node:20-alpine` | `WORKDIR /app`; copy `frontend/package.json`, `frontend/package-lock.json`; `npm ci --no-audit --no-fund` |
| `build` | `node:20-alpine` | `ARG BACKEND_URL=http://api:8000`, `ARG NEXT_PUBLIC_WS_URL=` (empty); `ENV BACKEND_URL`, `NEXT_PUBLIC_WS_URL`, `NEXT_TELEMETRY_DISABLED=1`; copy node_modules + `frontend/`; `npm run build` (the `/api` rewrite target is compiled in at build time) |
| `run` | `node:20-alpine` | `ARG BACKEND_URL=http://api:8000` (also needed at runtime by `/api/health`); `ENV BACKEND_URL`, `NODE_ENV=production`, `NEXT_TELEMETRY_DISABLED=1`, `PORT=3000`, `HOSTNAME=0.0.0.0`; user/group `app`; copies `.next/standalone`, `.next/static`, `public` (chown app); `USER app`; `EXPOSE 3000`; `HEALTHCHECK --interval=30s --timeout=5s CMD wget -qO- http://127.0.0.1:3000/ >/dev/null \|\| exit 1`; `CMD ["node", "server.js"]` |

### 13.6 `Caddyfile`

```
{$DOMAIN} {
	encode zstd gzip
	handle /api/v1/* { reverse_proxy api:8000 }   # API + WebSocket straight to FastAPI (first-party cookie)
	handle /docs*    { reverse_proxy api:8000 }
	handle /health*  { reverse_proxy api:8000 }
	handle           { reverse_proxy frontend:3000 }  # everything else: Next.js dashboard
	header {
		Strict-Transport-Security "max-age=31536000; includeSubDomains"
		-Server
	}
}
```
TLS certificates issued automatically by Caddy (Let's Encrypt).

### 13.7 `Makefile`

Header `# HireFlow — common tasks. \`make help\` lists them.`; `PY ?= backend/.venv/bin/python`; `SHELL := /bin/bash`.
`.PHONY` lists `start help setup setup-backend setup-frontend dev api worker beat web demo seed migrate test test-pg e2e lint format build up down logs prod-up`
(**`dev` and `format` are declared phony but have no recipe**). 21 targets:

| Target | Runs |
|---|---|
| `start` | `./start.sh` |
| `help` | greps `## ` comments from the Makefile and prints them (cyan, 16-char column) |
| `setup` | `setup-backend setup-frontend`, then `test -f .env \|\| cp .env.example .env` |
| `setup-backend` | `cd backend && python3 -m venv .venv && .venv/bin/pip install -U pip && .venv/bin/pip install -r requirements-dev.txt`; `cd backend && .venv/bin/python -m playwright install chromium` |
| `setup-frontend` | `cd frontend && npm ci` |
| `migrate` | `$(PY) scripts/migrate.py` |
| `api` | `cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000` |
| `worker` | `cd backend && .venv/bin/celery -A app.worker.celery_app worker -Q default,browser --loglevel INFO` |
| `beat` | `cd backend && .venv/bin/celery -A app.worker.celery_app beat --loglevel INFO` |
| `web` | `cd frontend && npm run dev` |
| `demo` | `$(PY) scripts/demo_site.py` (demo careers site on :8765) |
| `seed` | `$(PY) scripts/seed_db.py` |
| `test` | `cd backend && .venv/bin/python -m pytest` (SQLite) |
| `test-pg` | `cd backend && TEST_DATABASE_URL=$${TEST_DATABASE_URL:-postgresql+psycopg://hireflow:hireflow@localhost:5432/hireflow_test} .venv/bin/python -m pytest` |
| `e2e` | `cd backend && .venv/bin/python -m pytest -m e2e` |
| `lint` | `cd backend && .venv/bin/ruff check app tests alembic/env.py && .venv/bin/ruff check ../scripts`; `cd frontend && npm run lint && npm run typecheck` |
| `build` | `cd frontend && npm run build` |
| `up` | `docker compose up --build -d` |
| `down` | `docker compose down` |
| `logs` | `docker compose logs -f --tail=100` |
| `prod-up` | `docker compose -f docker-compose.prod.yml up --build -d` |

### 13.8 `start.sh` (448 lines, `#!/usr/bin/env bash`, `set -euo pipefail`)

Header: "HireFlow — one command to set up and run everything." Banner `[▪ HireFlow — swipe right, we apply`.

| Flag | Effect |
|---|---|
| *(none)* | local mode: no Docker (SQLite; Redis + Celery if installed) |
| `--demo` | also seed a demo account (`scripts/seed_db.py`, "Demo account: demo@example.com / demo-password-123") and serve the demo careers site on `:$DEMO_PORT` (8765); in `--docker` mode seeds via `docker compose exec -T api python scripts/seed_db.py` |
| `--docker` | full stack in Docker Compose: checks docker installed/running, `ensure_env`, optional `setup_ollama`, `docker compose up --build -d`, waits for API `/health` (180 s, demo only) and dashboard (240 s) |
| `--stop` | `docker compose down` |
| `--prod` | local mode with a production dashboard build (`npm run build` → `next start -p $WEB_PORT`) |
| `--reset` | deletes `backend/data/hireflow.db` and `hireflow.db-*` first |
| `--ollama` | `setup_ollama`: checks/starts Ollama (macOS app or `ollama serve`), sets `LLM_PROVIDER=ollama` and `OLLAMA_MODEL=qwen3.5:4b` in `.env` if empty, pulls the model (CLI or `/api/pull` stream with progress); Ollama Cloud URLs only check `OLLAMA_API_KEY` |
| `--no-open` | do not open the browser (not listed in the header help) |
| `-h`, `--help` | prints header lines 3–16 |
| other | `die "Unknown option"` |

Behaviour of local mode:
1. Requires Python ≥ 3.11 (tries `python3.13`, `3.12`, `3.11`, `python3`), Node ≥ 18 (message says 20+ / 18.18+), `curl`.
2. `ensure_env`: creates `.env` from `.env.example`; generates `SECRET_KEY` (`secrets.token_urlsafe(48)`) if
   empty/`change-me…`; generates `ENCRYPTION_KEY` (urlsafe base64 of 32 random bytes) if empty; warns when no
   AI provider is configured (and hints if Ollama is already running).
3. Virtualenv `backend/.venv`; reinstalls `requirements-dev.txt` when the SHA-256 of both requirement files
   changes (`.venv/.req-hash`); installs Chromium when the Playwright version changes (`.venv/.chromium-stamp`,
   log `logs/playwright-install.log`).
4. `npm ci --no-audit --no-fund --loglevel=error` when `package-lock.json` hash changes (`node_modules/.lock-hash`).
5. Exports for this run: `DATABASE_URL=${LOCAL_DATABASE_URL:-sqlite:///$ROOT/backend/data/hireflow.db}`,
   `LOCAL_STORAGE_PATH=$ROOT/backend/data/storage`, `FRONTEND_URL=http://localhost:$WEB_PORT`,
   `PUBLIC_API_URL=http://localhost:$API_PORT`, `CORS_ORIGINS=http://localhost:$WEB_PORT,http://127.0.0.1:$WEB_PORT`,
   `BACKEND_URL=http://127.0.0.1:$API_PORT`, `NEXT_PUBLIC_WS_URL=ws://localhost:$API_PORT/api/v1/ws`,
   `NEXT_TELEMETRY_DISABLED=1`, `PYTHONUNBUFFERED=1`, `OLLAMA_BASE_URL` (when resolved).
6. Redis: running on 6379 → use it; `redis-server` installed → start one (`--save "" --appendonly no`); none →
   `REDIS_URL=""`, `CELERY_TASK_ALWAYS_EAGER=true`; else `REDIS_URL=redis://localhost:6379/0`, `CELERY_TASK_ALWAYS_EAGER=false`.
7. Refuses busy ports (`API_PORT` 8000, `WEB_PORT` 3000).
8. `scripts/migrate.py` (log `logs/migrate.log`); counts accounts in the SQLite DB and points to
   `scripts/account.py where` / `reset-password <email>`.
9. Starts (each in its own process group, logs in `logs/<name>.log`): `api` (`uvicorn app.main:app --host 127.0.0.1 --port $API_PORT`);
   with Redis `worker` (`celery … worker -Q default,browser --concurrency 2`) + `beat` (`--schedule backend/data/celerybeat-schedule`),
   otherwise `scheduler` (`scripts/local_scheduler.py`); `web` (`next dev -p $WEB_PORT` or `next start`); `demo-site` with `--demo`.
10. Waits for `/health` (90 s) and dashboard `/api/health` (180 s); prints URLs, queue mode, first-run tips;
    opens the browser; tails `api.log` + `web.log`; exits if any service dies. Ctrl-C → `cleanup` ("Stopping
    HireFlow…" … "Stopped. See you next scan.") kills process groups (TERM, then KILL after 2 s).

### 13.9 `start.bat` (37 lines, Windows / Docker Desktop)

- `start.bat` → build + start the full stack; `start.bat stop` → `docker compose down`.
- Checks `docker` exists and Docker Desktop is running.
- If no `.env`: copies `.env.example` and generates `SECRET_KEY` (48 random bytes, urlsafe base64, `=` trimmed)
  and `ENCRYPTION_KEY` (32 bytes urlsafe base64) with PowerShell; prints `[ok] Created .env with fresh secrets`.
- `docker compose up --build -d`; waits (240 × 1 s) for `http://localhost:3000/api/health`; prints Dashboard /
  API docs / stop hint; opens http://localhost:3000. Echo text "Building and starting HireFlow…".

### 13.10 GitHub Actions workflows (`.github/workflows/`)

#### `ci.yml` — "CI"
Triggers: `push` to `main` and `claude/**`; `pull_request`; `workflow_dispatch`. `concurrency: ci-${{ github.ref }}`
(cancel in progress). `permissions: contents: read`. No secrets required.

| Job | Runs on / needs | Steps |
|---|---|---|
| `backend` — "Backend (lint, migrations, tests)" | ubuntu-latest; services `postgres` (`pgvector/pgvector:pg16`, user/password/db `hireflow`, port 5432, pg_isready health) and `redis` (`redis:7-alpine`, 6379, `redis-cli ping`); working dir `backend`; env `DATABASE_URL=postgresql+psycopg://hireflow:hireflow@localhost:5432/hireflow`, `REDIS_URL=redis://localhost:6379/0`, `SECRET_KEY=ci-secret-key-that-is-long-enough-for-hs256-signing` | checkout@v4 → setup-python@v5 (3.12, pip cache on `backend/requirements*.txt`) → install (`pip install -r requirements-dev.txt`, `python -m playwright install --with-deps chromium`) → Ruff (`ruff check app tests alembic/env.py`; `ruff check ../scripts`) → Bandit (`bandit -q -r app -ll`) → migrations (`alembic upgrade head`, `alembic check`, `alembic downgrade base`, `alembic upgrade head`) → create test DB (`psql … -c "CREATE DATABASE hireflow_test"`) → Tests SQLite (`python -m pytest -q`) → Tests PostgreSQL + pgvector incl. browser e2e (`TEST_DATABASE_URL=postgresql+psycopg://hireflow:hireflow@localhost:5432/hireflow_test`, `pytest -q --cov=app --cov-report=term-missing:skip-covered`) |
| `frontend` — "Dashboard (lint, typecheck, build)" | ubuntu-latest; working dir `frontend` | checkout → setup-node@v4 (20, npm cache on `frontend/package-lock.json`) → `npm ci` → `npm run lint` → `npm run typecheck` → `npm run build` (env `BACKEND_URL=http://localhost:8000`) |
| `extension` — "Chrome extension" | ubuntu-latest | checkout → setup-node 20 → validate (`node -e` asserts `manifest_version === 3`, prints name + version; `node --check` every `*.js`) → package `cd extension && zip -r ../hireflow-extension.zip . -x '*.DS_Store'` → upload-artifact@v4 (`name: hireflow-extension`, `path: hireflow-extension.zip`) |
| `docker` — "Docker images" | ubuntu-latest; `needs: [backend, frontend]` | checkout → setup-buildx@v3 → build-push@v6 backend (`file: backend/Dockerfile`, `tags: hireflow-backend:ci`, `load: true`, gha cache scope `backend`) → build-push frontend (`frontend/Dockerfile`, `hireflow-frontend:ci`, gha cache scope `frontend`) → smoke test `docker run --rm -e DATABASE_URL=sqlite:////tmp/smoke.db hireflow-backend:ci python -c "import app.main, app.worker.celery_app; …launch chromium, print version"` |

#### `deploy-backend.yml` — "Deploy backend (AWS ECS)"
Triggers: `workflow_run` of `CI` (`completed`, branch `main`) and `workflow_dispatch`. Permissions
`contents: read`, `id-token: write` (OIDC). Concurrency `deploy-backend` (no cancel). Job `deploy` runs only if
`vars.AWS_ROLE_ARN != ''` and (dispatch or CI concluded `success`); `environment: production`.

- Repository **variables**: `AWS_REGION`, `AWS_ROLE_ARN` (required), `ECS_CLUSTER`, optional `ECR_REPOSITORY`
  (default `hireflow-backend`), optional `ECS_SERVICES` (default `"hireflow-api hireflow-worker hireflow-beat"`). No secrets.
- Env: `GIT_SHA = workflow_run.head_sha || github.sha`.
- Steps: checkout `GIT_SHA` → `aws-actions/configure-aws-credentials@v4` (role-to-assume) →
  `aws-actions/amazon-ecr-login@v2` → buildx → build-push `backend/Dockerfile` to
  `<registry>/<repo>:<sha>` and `:latest` (gha cache) → for every service: describe current task definition,
  `jq` swaps the image of containers whose image contains the repo name, strips read-only fields, registers
  the new revision, `aws ecs update-service` → `aws ecs wait services-stable`.
- Every ECS service runs the same image; the task definition sets the command (`api | worker | beat`); the API
  migrates on start-up under a Postgres advisory lock.

#### `deploy-frontend.yml` — "Deploy dashboard (Vercel)"
Triggers: `workflow_run` of `CI` (completed, `main`) and `workflow_dispatch`. Permissions `contents: read`.
Concurrency `deploy-frontend`. Runs only if `vars.VERCEL_PROJECT_ID != ''` and (dispatch or CI success);
`environment: production`.

- Repository variables `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`; **secret** `VERCEL_TOKEN`. Vercel project
  (Root Directory `frontend`) env: `BACKEND_URL=https://api.your-domain.com`,
  `NEXT_PUBLIC_WS_URL=wss://api.your-domain.com/api/v1/ws`.
- Steps: checkout (`head_sha`) → setup-node 20 → `npm install --global vercel@latest` →
  `vercel pull --yes --environment=production` → `vercel build --prod` → `vercel deploy --prebuilt --prod` (all with `--token`).

### 13.11 `scripts/`

| Script | Usage | What it does |
|---|---|---|
| `account.py` (112 lines) | `backend/.venv/bin/python scripts/account.py where [email]`; `… reset-password you@example.com` | Local-mode account helper for `backend/data/hireflow.db` (or `LOCAL_DATABASE_URL` if `sqlite:///…`; non-SQLite URL → exits). `where` shows the database, its accounts (email, created_at) and other copies of the project next to it; `reset-password` prompts for a hidden password. |
| `demo_site.py` (168) | `python scripts/demo_site.py [--host 127.0.0.1] [--port 8765]` | Local demo company "Acme Robotics": `/` or `/careers` (schema.org JSON-LD `@graph` of postings), `/jobs/<id>` (application form `action="/jobs/{id}/submit"`, multipart, with JSON-LD), `POST /jobs/<id>/submit` records a submission (printed to stdout as "NEW APPLICATION:") and answers "Thank you for applying! … Confirmation number: ACME-<1000+n>", `/submissions` (JSON). Lets you try scan → match → tailor → fill → approve → submit without contacting real employers. |
| `init-env.sh` (25) | `scripts/init-env.sh` | Creates a private `.env` (umask 077, chmod 600) from `.env.example` with `SECRET_KEY` (`openssl rand -hex 32`), `ENCRYPTION_KEY` (`openssl rand -base64 32` with `+/`→`-_`), `POSTGRES_PASSWORD` (`openssl rand -hex 24`); never overwrites an existing `.env`; prints nothing secret. |
| `internshala_check.py` (182) | `backend/.venv/bin/python scripts/internshala_check.py [you@example.com]` | Diagnoses why Internshala rejects the synced login: tries it as a plain request and in the bot's browser against `/student/dashboard` (`PROBE_PATH`), reports redirects and which login cookies (`PHPSESSID, l, is_logged_in, sessionToken, persistentSession`) changed/were deleted — names only. Uses `DATABASE_URL` default `LOCAL_DATABASE_URL` or `sqlite:///<root>/backend/data/hireflow.db`; `INTERNSHALA_CHECK_BASE` (default `https://internshala.com`, overridden in tests). Changes nothing. |
| `local_scheduler.py` (70) | `python scripts/local_scheduler.py` | Section 8.5. |
| `migrate.py` (86) | `python scripts/migrate.py` / `--reembed` / `--check` | Default: `wait_for_db()`; SQLite → `create_all()` ("SQLite: tables created"); PostgreSQL → `pg_advisory_lock(7214553901)` (`MIGRATION_LOCK_ID`) around `python -m alembic upgrade head` (cwd backend). `--check` → `alembic check`. `--reembed` → recompute every job (batches of 64, 8 000 chars) and resume embedding. |
| `seed_db.py` (242) | `python scripts/seed_db.py [--email demo@example.com] [--password demo-password-123] [--reset]` | Seeds a demo account ("Alex Rivera") with a master resume, realistic jobs, applications + status history, communications, interviews and an agent run; `--reset` deletes the account first. |
| `server-setup.sh` (249) | `curl -fsSL https://raw.githubusercontent.com/saksham-eng560/HireFlow/main/scripts/server-setup.sh \| bash` (env before `bash`) | Fresh Ubuntu/Debian server: installs Docker + git/curl/openssl/iptables-persistent; opens 80/443 (iptables, ufw); adds 4 GB swap when RAM < 8 GB; clones/updates `REPO_URL` (default `https://github.com/saksham-eng560/HireFlow.git`) branch `BRANCH` (main) into `APP_DIR` (default `~/hireflow`); writes `.env` (ENVIRONMENT=production, DOMAIN default `<public-ip-with-dashes>.sslip.io`, FRONTEND_URL/PUBLIC_API_URL/CORS_ORIGINS https, COOKIE_SECURE=true, fresh SECRET_KEY/ENCRYPTION_KEY/POSTGRES_PASSWORD, ANTHROPIC_API_KEY); `WITH_OLLAMA=1` adds `COMPOSE_PROFILES=ollama`, `OLLAMA_MODEL` (default `qwen3.5:4b`), `LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL=http://ollama:11434`; `docker compose -f docker-compose.prod.yml up -d --build --remove-orphans`; pulls the model in the ollama container; waits for `https://$DOMAIN/health` (60 × 10 s) and prints next steps ("HireFlow is live: https://…", disable `ALLOW_REGISTRATION`, Oracle security-list hint). |
| `test_scraper.py` (74) | `python scripts/test_scraper.py <platform\|url> [target] [-s SOURCE]… [-k KEYWORD]… [-l LOCATION]… [--remote] [--days 30] [--limit 10] [--json]` | Runs one scraper (any `SCRAPERS` key) or imports one URL; `SOURCE_KEYS`: greenhouse→`greenhouse_boards`, lever→`lever_companies`, ashby→`ashby_boards`, workday→`workday_sites`, generic→`career_pages`, internshala→`internshala_urls`, internships→`internship_lists`. |
| `ruff.toml` (7) | used by `ruff check ../scripts` | `extend = "../backend/ruff.toml"`; isort first-party `app`, `tests`; per-file ignores `"*.py" = ["E402", "S", "E501"]`. |

Scripts locate the backend via `<root>/backend` (repo) or the image root (`/app`), inserting it into `sys.path`.

### 13.12 Lint / test configuration and ignore files

**`backend/ruff.toml`**: `line-length = 150`, `target-version = "py311"`, `extend-exclude = ["alembic/versions"]`;
`[lint] select = ["E", "F", "W", "I", "B", "UP", "S", "BLE", "N", "RUF"]`; ignore `S101, S311, B008, RUF001,
RUF002, RUF003, RUF012, S603, S607, UP040, UP042, N818, S110, S112`; per-file ignores: `tests/*` →
`S, E402, BLE001, N802, E501`; `scripts/*` → `S, E402`; `alembic/env.py` → `E402`; `app/automation/captcha.py`,
`app/submitters/form_engine.py`, `app/services/question_answerer.py` → `E501`; isort `known-first-party = ["app", "tests"]`.

**`backend/pytest.ini`**: `testpaths = tests`; `addopts = -ra --strict-markers`; markers `e2e` ("end-to-end
tests that launch a real Chromium browser (deselect with -m "not e2e")"), `postgres` ("tests that require
PostgreSQL + pgvector (TEST_DATABASE_URL)"); `filterwarnings = ignore::DeprecationWarning, ignore::PendingDeprecationWarning`.

**`.dockerignore`** (repo root — the build context for both images): `**/.venv`, `**/__pycache__`, `**/*.pyc`,
`**/.pytest_cache`, `**/.ruff_cache`, `**/node_modules`, `**/.next`, `backend/data`, `.git`, `.env`.

**`backend/.dockerignore`**: `.venv`, `__pycache__`, `*.pyc`, `.pytest_cache`, `.ruff_cache`, `data`,
`tests/fixtures/mock_ats/*.log` (only applies to builds whose context is `backend/`; compose and CI use the root context).

**`.gitignore`**: Python (`__pycache__/`, `*.py[cod]`, `*.egg-info/`, `.venv/`, `venv/`, `.pytest_cache/`,
`.ruff_cache/`, `.coverage`, `htmlcov/`); Node/Next (`node_modules/`, `.next/`, `out/`, `*.tsbuildinfo`,
`next-env.d.ts`); env & secrets (`.env`, `.env.*`, `!.env.example`, `*.pem`); app data (`backend/data/`, `data/`,
`*.sqlite3`, `*.db`); OS/editors (`.DS_Store`, `.idea/`, `.vscode/`, `*.swp`); build artifacts (`extension/dist/`,
`*.zip`); runtime state (`dump.rdb`, `celerybeat-schedule*`, `logs/`).

**`.gitattributes`**: `*.sh text eol=lf`, `*.bat text eol=crlf`.

---

---

## Section 14: Complete Environment Variables

### 14.1 Settings model (`backend/app/config.py`)

- `class Settings(BaseSettings)` with `SettingsConfigDict(env_file=(<repo>/.env, <repo>/backend/.env), env_file_encoding="utf-8", extra="ignore", case_sensitive=True)`.
  Real environment variables override `.env` values; the backend `.env` overrides the repo-root `.env`.
- Module constants: `BACKEND_DIR` (`backend/`), `REPO_ROOT`, `DEFAULT_SECRET = "change-me-in-production-please-use-a-long-random-string"`,
  `DEFAULT_OLLAMA_URL = "http://localhost:11434"`, `DEFAULT_OLLAMA_MODEL = "qwen3.5:4b"`, `LLM_PROVIDERS = ("auto", "anthropic", "openai", "ollama")`.
- Helpers: `_csv(value)` (comma split, trimmed, empties dropped); `in_container()` (`lru_cache`; True when
  `/.dockerenv` or `/run/.containerenv` exists).
- **Validator** `_drop_inline_comments` (`@field_validator("*", mode="before")`): a string value that starts with
  `#` (an inline `.env` comment read as the value by older python-dotenv), or an empty string for a field whose
  default is `None`, is replaced by the field default. (Empty strings for fields with a non-`None` default are
  kept, e.g. `OLLAMA_MODEL=""`, `LLM_PROVIDER=""`, `OLLAMA_BASE_URL=""`; the derived properties normalise them.)
- **Derived properties**:

| Property | Definition |
|---|---|
| `cors_origins` | `_csv(CORS_ORIGINS)` (used by `CORSMiddleware` in `main.py`) |
| `proxy_urls` | `_csv(PROXY_URLS)` (used by `ProxyManager`) |
| `celery_broker` | `CELERY_BROKER_URL or REDIS_URL or "memory://"` |
| `celery_backend` | `CELERY_RESULT_BACKEND or REDIS_URL` |
| `google_redirect_uri` | `GOOGLE_REDIRECT_URI` or `f"{FRONTEND_URL.rstrip('/')}{API_PREFIX}/auth/google/callback"` (through the dashboard's same-origin `/api` proxy so the cookie is first-party) |
| `google_configured` | `bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)` |
| `llm_provider` | `LLM_PROVIDER` lower-cased; empty or unknown → `"auto"` |
| `ollama_model` | `OLLAMA_MODEL.strip()`; if empty and `llm_provider == "ollama"` → `DEFAULT_OLLAMA_MODEL` (`qwen3.5:4b`) |
| `ollama_enabled` | `bool(ollama_model)` |
| `ollama_base_url` | `OLLAMA_BASE_URL` (empty → `http://localhost:11434`) with trailing `/`, `/api`, `/v1` removed; `localhost`/`127.0.0.1` rewritten to `host.docker.internal` when `in_container()` |
| `ollama_is_cloud` | host of `ollama_base_url` is `ollama.com` or `*.ollama.com` |
| `ollama_cloud_model` | `ollama_is_cloud` or model ends with `-cloud` / `:cloud` |
| `is_sqlite` | `DATABASE_URL.startswith("sqlite")` |
| `is_production` | `ENVIRONMENT == "production"` |

- `validate_for_production() -> list[str]`: `SECRET_KEY` equals the default or is shorter than 32 chars;
  `ENCRYPTION_KEY` missing (message includes the generator one-liner); `COOKIE_SECURE` false. `get_settings()`
  (`lru_cache`) logs each problem as `"CONFIG: …"` when `is_production`; `main.py` checks again on start-up.
- Singleton: `settings = get_settings()`.

### 14.2 Every setting (89)

Legend for **.env.example**: `yes` = active line; `commented` = present as a `# KEY=value` line; `—` = absent
(config only). No `Settings` field appears in `frontend/.env.example`.

| # | Name | Type | Default | Purpose / where used | `.env.example` |
|---|---|---|---|---|---|
| 1 | `APP_NAME` | str | `"HireFlow"` | Display name (defined but not referenced anywhere in `app/`) | — |
| 2 | `ENVIRONMENT` | str | `"development"` | `development \| test \| production`; production checks, Sentry environment, `main.py`, `api/auth.py`, `api/deps.py` | yes (`development`) |
| 3 | `DEBUG` | bool | `False` | Not referenced anywhere | — |
| 4 | `LOG_LEVEL` | str | `"INFO"` | `core/logging_config.py`, `scripts/local_scheduler.py` (also read by the entrypoint for Celery) | yes (`INFO`) |
| 5 | `API_PREFIX` | str | `"/api/v1"` | Router prefix, OpenAPI URL, file URLs (`api/serializers.py`), Google redirect | — |
| 6 | `FRONTEND_URL` | str | `"http://localhost:3000"` | Absolute links in notifications, OAuth redirects | yes |
| 7 | `PUBLIC_API_URL` | str | `"http://localhost:8000"` | `api_url` returned with an extension token (`api/auth.py`) | yes |
| 8 | `CORS_ORIGINS` | str (CSV) | `"http://localhost:3000,http://127.0.0.1:3000"` | → `cors_origins` | yes (`http://localhost:3000`) |
| 9 | `ALLOW_REGISTRATION` | bool | `True` | Self sign-up toggle (`api/auth.py`) | yes (`true`) |
| 10 | `SECRET_KEY` | str | `DEFAULT_SECRET` | JWT signing (`core/security.py`); must be ≥ 32 chars in production | yes (placeholder) |
| 11 | `ENCRYPTION_KEY` | str \| None | `None` | urlsafe-base64 32-byte key for AES-256-GCM token/cookie encryption | yes (empty) |
| 12 | `ACCESS_TOKEN_EXPIRE_MINUTES` | int | `10080` (7 days) | JWT + session cookie `max_age` | — |
| 13 | `EXTENSION_TOKEN_EXPIRE_DAYS` | int | `180` | Extension token lifetime | — |
| 14 | `COOKIE_NAME` | str | `"hireflow_session"` | Session cookie name (`api/auth.py`, `api/deps.py`, `api/users.py`, `api/files.py`) | — |
| 15 | `COOKIE_SECURE` | bool | `False` | `Secure` flag on the session cookie | yes (`false`) |
| 16 | `RATE_LIMIT_DEFAULT` | str | `"300/minute"` | slowapi default limit (`api/deps.py`) | — |
| 17 | `DATABASE_URL` | str | `"postgresql+psycopg://hireflow:hireflow@localhost:5432/hireflow"` | SQLAlchemy URL (`sqlite:///…` supported) | yes |
| 18 | `DB_POOL_SIZE` | int | `10` | Pool size; `max_overflow = 2 × pool size` | — |
| 19 | `DB_CONNECT_RETRIES` | int | `5` | `wait_for_db` attempts | — |
| 20 | `REDIS_URL` | str \| None | `"redis://localhost:6379/0"` | Rate limiter, dispatch, Celery fallback broker; empty → in-process mode | yes |
| 21 | `CELERY_BROKER_URL` | str \| None | `None` | → `celery_broker` | — |
| 22 | `CELERY_RESULT_BACKEND` | str \| None | `None` | → `celery_backend` | — |
| 23 | `CELERY_TASK_ALWAYS_EAGER` | bool | `False` | Run tasks in-process (dispatch thread pool / eager Celery) | yes (`false`) |
| 24 | `ANTHROPIC_API_KEY` | str \| None | `None` | Enables the Anthropic provider | yes (empty) |
| 25 | `ANTHROPIC_MODEL` | str | `"claude-opus-5-5"` | Claude model id | yes |
| 26 | `ANTHROPIC_EFFORT` | str | `"medium"` | Default effort (`low \| medium \| high \| xhigh \| max`) for every provider call | yes |
| 27 | `ANTHROPIC_REFUSAL_FALLBACK` | bool | `True` | Server-side `fallbacks: "default"` via beta `server-side-fallback-2026-07-01` | yes (`true`) |
| 28 | `ANTHROPIC_MAX_TOKENS` | int | `32000` | Default `max_tokens` for Claude | — |
| 29 | `OPENAI_API_KEY` | str \| None | `None` | Enables OpenAI provider + OpenAI embeddings | yes (empty) |
| 30 | `OPENAI_MODEL` | str | `"gpt-4o"` | OpenAI chat model | yes |
| 31 | `OPENAI_BASE_URL` | str | `"https://api.openai.com/v1"` | Chat-completions + embeddings base URL | — |
| 32 | `LLM_MAX_RETRIES` | int | `3` | Attempts per provider (backoff 1/2/4 s) | — |
| 33 | `LLM_TIMEOUT_SECONDS` | float | `300.0` | Anthropic/OpenAI request timeout | — |
| 34 | `LLM_PROVIDER` | str | `"auto"` | Provider order (`auto \| anthropic \| openai \| ollama`) → `llm_provider` | yes (empty = auto) |
| 35 | `OLLAMA_BASE_URL` | str | `"http://localhost:11434"` | Ollama server / Ollama Cloud → `ollama_base_url` | yes (empty) |
| 36 | `OLLAMA_MODEL` | str | `""` | Ollama model; empty = Ollama off unless `LLM_PROVIDER=ollama` → `ollama_model` | yes (empty) |
| 37 | `OLLAMA_API_KEY` | str \| None | `None` | Ollama Cloud key (Bearer, sent only to `OLLAMA_BASE_URL`) | yes (empty) |
| 38 | `OLLAMA_NUM_CTX` | int | `8192` | Context window (`num_ctx`); also compose `OLLAMA_CONTEXT_LENGTH` | commented (`8192`) |
| 39 | `OLLAMA_KEEP_ALIVE` | str | `"30m"` | Keep model loaded (chat + embed calls; compose `OLLAMA_KEEP_ALIVE`) | commented (`30m`) |
| 40 | `OLLAMA_TIMEOUT_SECONDS` | float | `600.0` | Ollama request timeout | commented (`600`) |
| 41 | `OLLAMA_CONCURRENCY` | int | `1` | Ollama calls in flight per process (`ollama_slots`); caps `SCAN_LLM_CONCURRENCY` when Ollama is primary | commented (`1`) |
| 42 | `OLLAMA_MAX_EVALUATIONS_PER_SCAN` | int | `15` | Caps `MAX_LLM_EVALUATIONS_PER_SCAN` when Ollama is primary | commented (`15`) |
| 43 | `OLLAMA_THINK` | bool | `False` | Let thinking models reason first | commented (`false`) |
| 44 | `OLLAMA_EMBED_MODEL` | str | `"nomic-embed-text"` | Embeddings model with `EMBEDDING_PROVIDER=ollama` | commented |
| 45 | `EMBEDDING_PROVIDER` | str | `"local"` | `local \| openai \| ollama` | yes (`local`) |
| 46 | `OPENAI_EMBEDDING_MODEL` | str | `"text-embedding-3-small"` | OpenAI embeddings model | — |
| 47 | `EMBEDDING_DIM` | int | `1536` | Vector size (pgvector columns, padding/cutting) | — |
| 48 | `GOOGLE_CLIENT_ID` | str \| None | `None` | Google OAuth client → `google_configured` | yes (empty) |
| 49 | `GOOGLE_CLIENT_SECRET` | str \| None | `None` | Google OAuth secret | yes (empty) |
| 50 | `GOOGLE_REDIRECT_URI` | str \| None | `None` | Override → `google_redirect_uri` | commented (`http://localhost:3000/api/v1/auth/google/callback`) |
| 51 | `GMAIL_PUBSUB_TOPIC` | str \| None | `None` | `projects/<p>/topics/<t>` for Gmail push; enables watch renewal | yes (empty) |
| 52 | `GMAIL_PUBSUB_VERIFICATION_TOKEN` | str \| None | `None` | Token checked on the Gmail push webhook (`api/files.py`) | yes (empty) |
| 53 | `GMAIL_LOOKBACK_DAYS` | int | `14` | Inbox lookback for first sync | — |
| 54 | `STORAGE_BACKEND` | str | `"local"` | `local \| s3` | yes |
| 55 | `LOCAL_STORAGE_PATH` | str | `str(BACKEND_DIR / "data" / "storage")` | Local file storage root (Docker/compose/start.sh set it) | — |
| 56 | `S3_BUCKET` | str \| None | `None` | S3/R2/MinIO bucket | yes (empty) |
| 57 | `S3_ENDPOINT_URL` | str \| None | `None` | Custom endpoint (R2 / MinIO) | yes (empty) |
| 58 | `S3_REGION` | str | `"auto"` | Region | yes (`auto`) |
| 59 | `S3_ACCESS_KEY_ID` | str \| None | `None` | S3 key | yes (empty) |
| 60 | `S3_SECRET_ACCESS_KEY` | str \| None | `None` | S3 secret | yes (empty) |
| 61 | `BROWSER_HEADLESS` | bool | `True` | Playwright headless | yes (`true`) |
| 62 | `PLAYWRIGHT_CHROMIUM_EXECUTABLE` | str \| None | `None` | Custom Chromium binary | — |
| 63 | `BROWSER_TIMEOUT_MS` | int | `30000` | Default Playwright timeout | — |
| 64 | `HUMAN_EMULATION` | bool | `True` | Human typing/mouse/scroll/dwell | yes (`true`) |
| 65 | `PROXY_URLS` | str (CSV) | `""` | `http://user:pass@host:port` list → `proxy_urls` | yes (empty) |
| 66 | `CAPTCHA_PROVIDER` | str | `"2captcha"` | `2captcha \| anticaptcha` | yes |
| 67 | `CAPTCHA_API_KEY` | str \| None | `None` | Solver key | yes (empty) |
| 68 | `SUBMISSION_DRY_RUN` | bool | `False` | Never click the final Submit | yes (`false`) |
| 69 | `SCREENSHOT_FULL_PAGE` | bool | `True` | Full-page screenshots | — |
| 70 | `SCAN_INTERVAL_HOURS` | int | `6` | Not referenced (per-user `scan_interval_hours` pref is used) | — |
| 71 | `EMAIL_POLL_MINUTES` | int | `5` | Beat/local-scheduler e-mail polling interval (min 60 s) | yes (`5`) |
| 72 | `MAX_JOBS_PER_SOURCE` | int | `50` | Default `SearchQuery.limit` when pref `max_jobs_per_source` is None | — |
| 73 | `MAX_LLM_EVALUATIONS_PER_SCAN` | int | `40` | Jobs scored by the LLM per scan | yes (`40`) |
| 74 | `SCAN_SOURCE_CONCURRENCY` | int | `8` | Sources searched at once | commented (`8`) |
| 75 | `SCRAPER_BOARD_CONCURRENCY` | int | `6` | Boards/pages fetched at once per source | commented (`6`) |
| 76 | `SCAN_LLM_CONCURRENCY` | int | `6` | LLM scoring calls at once | commented (`6`) |
| 77 | `SCAN_SOURCE_TIMEOUT_SECONDS` | int | `240` | Per-source limit (wrap-up at 80 %) | commented (`240`) |
| 78 | `AUTO_STAGE_APPLICATIONS` | bool | `True` | Fill forms automatically after preparation | yes (`true`) |
| 79 | `DATA_RETENTION_DAYS` | int | `730` | `retention_cleanup` cutoff | yes (`730`) |
| 80 | `SMTP_HOST` | str \| None | `None` | SMTP server (else e-mails go via the user's Gmail) | yes (empty) |
| 81 | `SMTP_PORT` | int | `587` | SMTP port | yes (`587`) |
| 82 | `SMTP_USER` | str \| None | `None` | SMTP user | yes (empty) |
| 83 | `SMTP_PASSWORD` | str \| None | `None` | SMTP password | yes (empty) |
| 84 | `SMTP_FROM` | str | `"HireFlow <no-reply@example.com>"` | From header | yes (same) |
| 85 | `SMTP_STARTTLS` | bool | `True` | STARTTLS | — |
| 86 | `DISCORD_WEBHOOK_URL` | str \| None | `None` | Global Discord webhook (user pref overrides) | yes (empty) |
| 87 | `SLACK_WEBHOOK_URL` | str \| None | `None` | Global Slack webhook (user pref overrides) | yes (empty) |
| 88 | `SENTRY_DSN` | str \| None | `None` | Sentry init (`traces_sample_rate=0.1`) | yes (empty) |
| 89 | `PROMPTS_DIR` | str | `default_factory: str(REPO_ROOT / "prompts")` | Prompt templates directory (Docker sets `/app/prompts`) | — |

Totals: **89 settings**; 51 active + 12 commented in `.env.example` = **63 in both places**; **26 config-only**
(`APP_NAME, DEBUG, API_PREFIX, ACCESS_TOKEN_EXPIRE_MINUTES, EXTENSION_TOKEN_EXPIRE_DAYS, COOKIE_NAME,
RATE_LIMIT_DEFAULT, DB_POOL_SIZE, DB_CONNECT_RETRIES, CELERY_BROKER_URL, CELERY_RESULT_BACKEND,
ANTHROPIC_MAX_TOKENS, OPENAI_BASE_URL, LLM_MAX_RETRIES, LLM_TIMEOUT_SECONDS, OPENAI_EMBEDDING_MODEL,
EMBEDDING_DIM, GMAIL_LOOKBACK_DAYS, LOCAL_STORAGE_PATH, PLAYWRIGHT_CHROMIUM_EXECUTABLE, BROWSER_TIMEOUT_MS,
SCREENSHOT_FULL_PAGE, SCAN_INTERVAL_HOURS, MAX_JOBS_PER_SOURCE, SMTP_STARTTLS, PROMPTS_DIR`). Unused settings:
`APP_NAME`, `DEBUG`, `SCAN_INTERVAL_HOURS`.

### 14.3 `.env.example`-only variables (not `Settings` fields)

| Variable | `.env.example` value | Consumer |
|---|---|---|
| `DOMAIN` | `hireflow.example.com` | `docker-compose.prod.yml` (`${DOMAIN:?set DOMAIN}`), Caddy `{$DOMAIN}`, `server-setup.sh` |
| `POSTGRES_PASSWORD` | `change-me` | `docker-compose.prod.yml` (postgres + `DATABASE_URL` interpolation), `init-env.sh`, `server-setup.sh` |
| `COMPOSE_PROFILES` | commented `# COMPOSE_PROFILES=ollama` | Docker Compose itself (starts the `ollama` service) |

`.env.example` header: "HireFlow — environment configuration". Example values that differ from code defaults:
`CORS_ORIGINS=http://localhost:3000` (default also includes `127.0.0.1`), `LLM_PROVIDER=` / `OLLAMA_BASE_URL=`
(empty → normalised to `auto` / `http://localhost:11434`).

### 14.4 `frontend/.env.example`

| Variable | Value | Purpose | Also in root `.env.example`? |
|---|---|---|---|
| `BACKEND_URL` | `http://localhost:8000` | Server-side target of the `/api/v1/*` and `/docs` rewrites (`next.config.js`) and `/api/health` route; compiled in at build time | no |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000/api/v1/ws` | Browser WebSocket endpoint (`hooks/use-websocket.ts`; optional — the file's comment says it falls back to polling; the hook derives a URL from the page location when unset) | no |

### 14.5 Variables read directly from the environment (outside `Settings`)

| Variable | Read in | Default / behaviour |
|---|---|---|
| `BACKEND_URL` | `frontend/next.config.js`, `frontend/src/app/api/health/route.ts` (`process.env`) | `http://localhost:8000` |
| `NEXT_PUBLIC_WS_URL` | `frontend/src/hooks/use-websocket.ts` | unset → `ws(s)://<host>/api/v1/ws`, where host is `<hostname>:8000` when the page is on port 3000, else the page's own host |
| `TEST_DATABASE_URL` | `backend/tests/conftest.py` | unset → `sqlite:///<tmp hireflow-tests-*>/test.db` |
| `LOCUST_EMAIL`, `LOCUST_PASSWORD` | `backend/tests/load/locustfile.py` | `demo@example.com` / `demo-password-123` |
| `LOCAL_DATABASE_URL` | `scripts/account.py`, `scripts/internshala_check.py`, `start.sh` | unset → `sqlite:///<root>/backend/data/hireflow.db` |
| `DATABASE_URL` | `scripts/internshala_check.py` (`os.environ.setdefault`) | set from `LOCAL_DATABASE_URL` or the local SQLite file |
| `INTERNSHALA_CHECK_BASE` | `scripts/internshala_check.py` | `https://internshala.com` |

`tests/conftest.py` sets (before importing `app`): `ENVIRONMENT=test`, `DATABASE_URL` (from `TEST_DATABASE_URL`
or temp SQLite), `REDIS_URL=""`, `CELERY_TASK_ALWAYS_EAGER=true`, `LOCAL_STORAGE_PATH=<tmp>/storage`,
`HUMAN_EMULATION=false`, `SECRET_KEY=test-secret-key-that-is-long-enough-1234567890`, `ANTHROPIC_API_KEY=""`,
`OPENAI_API_KEY=""`, `LLM_PROVIDER=auto`, `OLLAMA_MODEL=""`, `OLLAMA_API_KEY=""`, `EMBEDDING_PROVIDER=local`,
`GOOGLE_CLIENT_ID=""`, `GOOGLE_CLIENT_SECRET=""`, `SMTP_HOST=""`, `PROXY_URLS=""`, `CAPTCHA_API_KEY=""`,
`AUTO_STAGE_APPLICATIONS=true`, `SUBMISSION_DRY_RUN=false`, `BROWSER_TIMEOUT_MS=15000`.

### 14.6 Variables used by compose files, Dockerfiles, entrypoint, scripts and CI

| Variable | Where | Value / role |
|---|---|---|
| `DATABASE_URL`, `REDIS_URL`, `LOCAL_STORAGE_PATH` | both compose files (backend anchor) | `postgresql+psycopg://hireflow:hireflow@postgres:5432/hireflow` (prod: password `${POSTGRES_PASSWORD}`), `redis://redis:6379/0`, `/data/storage` |
| `FRONTEND_URL`, `PUBLIC_API_URL`, `CORS_ORIGINS` | compose (with `:-` defaults), prod (`https://${DOMAIN}`) | — |
| `ENVIRONMENT`, `COOKIE_SECURE`, `SECRET_KEY`, `ENCRYPTION_KEY` | `docker-compose.prod.yml` | `production`, `"true"`, required `${…:?}` |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | postgres service (compose, prod, CI services) | `hireflow` / `hireflow` (prod: `${POSTGRES_PASSWORD}`) / `hireflow` |
| `DOMAIN` | prod compose (caddy env, URLs), Caddyfile, `server-setup.sh` | — |
| `OLLAMA_KEEP_ALIVE`, `OLLAMA_NUM_PARALLEL`, `OLLAMA_CONTEXT_LENGTH` | `ollama` service | `${OLLAMA_KEEP_ALIVE:-30m}`, `"1"`, `${OLLAMA_NUM_CTX:-8192}` |
| `COMPOSE_PROFILES` | `.env` read by Docker Compose; `server-setup.sh` | `ollama` |
| `BACKEND_URL` | frontend service env + build arg; frontend Dockerfile ARG/ENV | `http://api:8000` |
| `HOSTNAME` | worker healthcheck (`celery@$$HOSTNAME`); frontend Dockerfile `HOSTNAME=0.0.0.0` | — |
| `PLAYWRIGHT_VERSION` | backend Dockerfile ARG | `1.56.0` |
| `PYTHONDONTWRITEBYTECODE`, `PYTHONUNBUFFERED`, `PIP_NO_CACHE_DIR`, `PIP_DISABLE_PIP_VERSION_CHECK`, `PIP_BREAK_SYSTEM_PACKAGES`, `PLAYWRIGHT_BROWSERS_PATH`, `PROMPTS_DIR`, `LOCAL_STORAGE_PATH` | backend Dockerfile ENV | `1`, `1`, `1`, `1`, `1`, `/ms-playwright`, `/app/prompts`, `/data/storage` |
| `NEXT_PUBLIC_WS_URL`, `NEXT_TELEMETRY_DISABLED`, `NODE_ENV`, `PORT` | frontend Dockerfile | build ARG (empty), `1`, `production`, `3000` |
| `PORT`, `API_WORKERS`, `WORKER_CONCURRENCY`, `LOG_LEVEL` | `docker-entrypoint.sh` | `8000`, `2`, `2`, `INFO` |
| `API_PORT`, `WEB_PORT`, `DEMO_PORT`, `LOCAL_DATABASE_URL` | `start.sh` inputs | `8000`, `3000`, `8765`, SQLite |
| `DATABASE_URL`, `LOCAL_STORAGE_PATH`, `FRONTEND_URL`, `PUBLIC_API_URL`, `CORS_ORIGINS`, `BACKEND_URL`, `NEXT_PUBLIC_WS_URL`, `NEXT_TELEMETRY_DISABLED`, `PYTHONUNBUFFERED`, `OLLAMA_BASE_URL`, `REDIS_URL`, `CELERY_TASK_ALWAYS_EAGER` | `start.sh` exports (local mode, see 13.8) | — |
| `SECRET_KEY`, `ENCRYPTION_KEY`, `LLM_PROVIDER`, `OLLAMA_MODEL`, `OLLAMA_BASE_URL`, `OLLAMA_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` | `start.sh` reads/writes `.env` (`env_value`, `env_set_if_empty`) | generated secrets; Ollama setup |
| `SECRET_KEY`, `ENCRYPTION_KEY` | `start.bat` (PowerShell writes `.env`) | generated |
| `SECRET_KEY`, `ENCRYPTION_KEY`, `POSTGRES_PASSWORD` | `scripts/init-env.sh` | generated with openssl |
| `DOMAIN`, `BRANCH`, `REPO_URL`, `APP_DIR`, `WITH_OLLAMA`, `OLLAMA_MODEL`, `ANTHROPIC_API_KEY` | `scripts/server-setup.sh` inputs | defaults: sslip.io host, `main`, `https://github.com/saksham-eng560/HireFlow.git`, `~/hireflow`, `0`, `qwen3.5:4b`; writes `ENVIRONMENT, DOMAIN, FRONTEND_URL, PUBLIC_API_URL, CORS_ORIGINS, COOKIE_SECURE, SECRET_KEY, ENCRYPTION_KEY, POSTGRES_PASSWORD, ANTHROPIC_API_KEY, COMPOSE_PROFILES, OLLAMA_MODEL, LLM_PROVIDER, OLLAMA_BASE_URL` |
| `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY` | CI `backend` job env | `postgresql+psycopg://hireflow:hireflow@localhost:5432/hireflow`, `redis://localhost:6379/0`, `ci-secret-key-that-is-long-enough-for-hs256-signing` |
| `TEST_DATABASE_URL` | CI PostgreSQL test step; Makefile `test-pg` | `postgresql+psycopg://hireflow:hireflow@localhost:5432/hireflow_test` |
| `BACKEND_URL` | CI frontend build | `http://localhost:8000` |
| `DATABASE_URL` | CI docker smoke test | `sqlite:////tmp/smoke.db` |
| `AWS_REGION`, `AWS_ROLE_ARN`, `ECS_CLUSTER`, `ECR_REPOSITORY`, `ECS_SERVICES` (repo **vars**); `GIT_SHA`, `IMAGE` (job env) | `deploy-backend.yml` | defaults `hireflow-backend`, `hireflow-api hireflow-worker hireflow-beat` |
| `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` (vars), `VERCEL_TOKEN` (**secret**) | `deploy-frontend.yml` | Vercel project env: `BACKEND_URL`, `NEXT_PUBLIC_WS_URL` |

---

---

## Section 15: Alembic Migration History

Location: `backend/alembic/versions/`. Every source revision uses short numeric IDs: the file `0001_initial_schema.py` has `revision = '0001'`. The chain is linear (`0001 → 0002 → 0003 → 0004 → 0005 → 0006`) and has no branch labels or `depends_on`. Every file imports `sqlalchemy as sa` and `alembic.op`. 0001 also imports `pgvector.sqlalchemy.Vector` and `sqlalchemy.dialects.postgresql`, and 0003, 0004 and 0006 import `postgresql`.

### 15.1 `0001_initial_schema.py`: "initial schema"

- `revision = '0001'`, `down_revision = None`, Create Date `2026-09-29 14:04:31.298338`.
- Module constant: `ENUM_NAMES = ['job_type', 'experience_level', 'ats_platform', 'application_status', 'email_direction', 'email_intent', 'interview_type']`.

**upgrade()**, in this order:
1. `op.execute("CREATE EXTENSION IF NOT EXISTS vector")`
2. `op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")`
3. Create the 7 ENUM types with `postgresql.ENUM(<values>, name=<name>).create(op.get_bind(), checkfirst=True)`. Values are in the order given in 2.12:
   `job_type`, `experience_level`, `ats_platform`, `application_status`, `email_direction`, `email_intent`, `interview_type`.
4. `create_table('jobs')` with 30 columns: every column in 2.4 except `company_verdict`, `company_tier` and `company_check`. Constraints: `PrimaryKeyConstraint('id')`, `UniqueConstraint('source_url')`. Enum columns use `postgresql.ENUM(name=…, create_type=False)`, `description_embedding` uses `Vector(1536)`, JSON columns use `postgresql.JSONB(astext_type=sa.Text())`, and datetimes use `sa.DateTime(timezone=True)`.
   - Indexes: `idx_jobs_company` (company_name), `idx_jobs_dedupe` (dedupe_key), `idx_jobs_platform` (source_platform), `op.f('ix_jobs_is_active')` (is_active). All are non-unique.
5. `create_table('users')` with 26 columns: every column in 2.1 except the 4 Internshala columns. `ats_credentials` is `sa.Text()`. `PrimaryKeyConstraint('id')`.
   - Index: `op.f('ix_users_email')` on `email`, **unique=True**.
6. `create_table('agent_runs')` with 14 columns (no `progress`). FK `user_id → users.id ON DELETE CASCADE`, PK.
   - Index: `ix_agent_runs_user_id`.
7. `create_table('notifications')` with 9 columns. FK user CASCADE, PK.
   - Indexes: `ix_notifications_created_at`, `ix_notifications_user_id`.
8. `create_table('resumes')` with 17 columns. FKs: `parent_resume_id → resumes.id SET NULL`, `tailored_for_job_id → jobs.id SET NULL`, `user_id → users.id CASCADE`. PK.
   - Index: `ix_resumes_user_id`.
9. `create_table('user_field_mappings')` with 5 columns. FK user CASCADE, PK, `UniqueConstraint('user_id', 'field_name', name='uq_user_field_mapping')`.
   - Index: `ix_user_field_mappings_user_id`.
10. `create_table('applications')` with 31 columns: every column in 2.6 except `review_decision`, `reviewed_at`, `auto_submit` and `field_overrides`. `similarity_score` is `sa.Double()`. FKs: `job_id → jobs.id` (no ondelete), `tailored_resume_id → resumes.id SET NULL`, `user_id → users.id CASCADE`. PK and `UniqueConstraint('user_id', 'job_id', name='uq_application_user_job')`.
    - Indexes: `idx_applications_user_status` (user_id, status), `ix_applications_job_id`, `ix_applications_status`, `ix_applications_user_id`.
11. `create_table('application_status_history')` with 7 columns. FK `application_id → applications.id CASCADE`, PK.
    - Index: `ix_application_status_history_application_id`.
12. `create_table('communications')` with 24 columns. `intent_confidence` is `sa.Float()`. FKs: `application_id → applications.id SET NULL`, `user_id → users.id CASCADE`. PK and `UniqueConstraint('gmail_message_id')`.
    - Indexes: `idx_comms_action`, `ix_communications_application_id`, `ix_communications_gmail_thread_id`, `ix_communications_user_id`.
13. `create_table('interviews')` with 24 columns. FKs: `application_id → applications.id CASCADE`, `communication_id → communications.id SET NULL`. PK and `UniqueConstraint('google_event_id')`.
    - Indexes: `ix_interviews_application_id`, `ix_interviews_scheduled_at`.
14. Raw SQL (the comment reads "PLAN.md §4 extras: vector similarity + partial / trigram indexes"):
    - `CREATE INDEX IF NOT EXISTS idx_jobs_embedding ON jobs USING ivfflat (description_embedding vector_cosine_ops) WITH (lists = 100)`
    - `CREATE INDEX IF NOT EXISTS idx_jobs_active ON jobs (is_active) WHERE is_active = true`
    - `CREATE INDEX IF NOT EXISTS idx_jobs_title_trgm ON jobs USING gin (role_title gin_trgm_ops)`
    - `CREATE INDEX IF NOT EXISTS idx_comms_action_required ON communications (is_action_required) WHERE is_action_required = true`

In total 0001 creates 10 tables with 187 columns, 21 ORM indexes, 4 raw indexes, 7 enum types and 2 extensions. It has no data migrations.

**downgrade()**, in reverse dependency order:
1. Drop the `interviews` indexes (`ix_interviews_scheduled_at`, `ix_interviews_application_id`), then drop `interviews`.
2. Drop the `communications` indexes (`ix_communications_user_id`, `ix_communications_gmail_thread_id`, `ix_communications_application_id`, `idx_comms_action`), then drop `communications`.
3. Drop `ix_application_status_history_application_id`, then drop `application_status_history`.
4. Drop the `applications` indexes (`ix_applications_user_id`, `ix_applications_status`, `ix_applications_job_id`, `idx_applications_user_status`), then drop `applications`.
5. Drop `ix_user_field_mappings_user_id`, then drop `user_field_mappings`.
6. Drop `ix_resumes_user_id`, then drop `resumes`.
7. Drop `ix_notifications_user_id` and `ix_notifications_created_at`, then drop `notifications`.
8. Drop `ix_agent_runs_user_id`, then drop `agent_runs`.
9. Drop `ix_users_email`, then drop `users`.
10. Drop the `jobs` indexes (`ix_jobs_is_active`, `idx_jobs_platform`, `idx_jobs_dedupe`, `idx_jobs_company`), then drop `jobs`.
11. `for name in ENUM_NAMES: op.execute(f"DROP TYPE IF EXISTS {name}")`.

The raw-SQL indexes are not dropped explicitly; they go away with their tables. The extensions `vector` and `pg_trgm` are **not** dropped.

### 15.2 `0002_swipe_review.py`: "swipe review: keep / skip decisions and auto-submit for kept jobs"

- `revision = '0002'`, `down_revision = '0001'`, Create Date `2026-09-30 10:00:00.000000`.
- **upgrade()**: `with op.batch_alter_table('applications')`, add `review_decision` `sa.String(length=16)` NULL, `reviewed_at` `sa.DateTime(timezone=True)` NULL, and `auto_submit` `sa.Boolean()` **`server_default=sa.false()`** NOT NULL. On PG this becomes `ALTER TABLE applications ADD COLUMN auto_submit BOOLEAN DEFAULT false NOT NULL`, which backfills existing rows with false.
- **downgrade()**: batch drop of `auto_submit`, `reviewed_at` and `review_decision`.

### 15.3 `0003_scan_progress.py`: "scan progress: live phase / percent / per-source status for the dashboard's progress bar"

- `revision = '0003'`, `down_revision = '0002'`, Create Date `2026-09-30 18:00:00.000000`.
- **upgrade()**: batch on `agent_runs`, add `progress` `sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql')` NULL.
- **downgrade()**: batch drop `progress`.

### 15.4 `0004_internshala_and_overrides.py`: "internshala session + review-queue field overrides"

- `revision = '0004'`, `down_revision = '0003'`, Create Date `2026-10-01 09:00:00.000000`.
- **upgrade()**:
  - Batch on `users`: add `internshala_session` `sa.Text()` NULL (holds `EncryptedJSON`), `internshala_session_updated_at` `sa.DateTime(timezone=True)` NULL, and `internshala_session_valid` `sa.Boolean()` `server_default=sa.false()` NOT NULL.
  - Batch on `applications`: add `field_overrides` JSON-with-JSONB-variant NULL.
- **downgrade()**: drop `applications.field_overrides`, then drop `users.internshala_session_valid`, `internshala_session_updated_at` and `internshala_session`.

### 15.5 `0005_internshala_user_agent.py`: "internshala login: the browser (user agent) the synced cookies belong to"

- `revision = '0005'`, `down_revision = '0004'`, Create Date `2026-10-01 12:00:00.000000`.
- **upgrade()**: batch on `users`, add `internshala_user_agent` `sa.String(length=512)` NULL.
- **downgrade()**: drop `internshala_user_agent`.

### 15.6 `0006_company_check.py`: "company check: verdict, tier and reasons per job"

- `revision = '0006'`, `down_revision = '0005'`, Create Date `2026-10-01 16:30:00.000000`.
- **upgrade()**: batch on `jobs`:
  - add `company_verdict` `sa.String(length=16)` NULL
  - add `company_tier` `sa.String(length=32)` NULL
  - add `company_check` JSON-with-JSONB-variant NULL
  - `create_index('idx_jobs_company_tier', ['company_tier'], unique=False)`
  - `create_index('idx_jobs_company_verdict', ['company_verdict'], unique=False)`
- **downgrade()**: drop the index `idx_jobs_company_verdict`, then `idx_jobs_company_tier`, then the columns `company_check`, `company_tier` and `company_verdict`.

None of 0002–0006 creates enums or extensions or migrates data. On PostgreSQL, `batch_alter_table` (default `recreate="auto"`) emits plain `ALTER TABLE` statements.

The offline SQL for the whole chain (`alembic upgrade head --sql`) ends with `UPDATE alembic_version SET version_num='0006'`.

### 15.7 `backend/alembic/env.py`

1. Imports `app.models` to register every model on `Base.metadata`, plus `app.config.settings` and `app.core.database.Base`.
2. `config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))`. The URL always comes from the `DATABASE_URL` setting or environment variable, with `%` escaped for configparser.
3. `fileConfig(config.config_file_name)` when an ini file is present.
4. `target_metadata = Base.metadata`.
5. `MANUAL_INDEXES = {"idx_jobs_embedding", "idx_jobs_active", "idx_jobs_title_trgm", "idx_comms_action_required"}`. `include_object(obj, name, type_, reflected, compare_to)` returns `not (type_ == "index" and name in MANUAL_INDEXES)`.
6. **Offline mode**: `context.configure(url=settings.DATABASE_URL, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"}, compare_type=True)`. It does not pass `include_object` or `render_as_batch`.
7. **Online mode**: `engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)` and then `context.configure(connection=…, target_metadata=…, compare_type=True, include_object=include_object, render_as_batch=connection.dialect.name == "sqlite")`. All pending migrations run inside one `context.begin_transaction()` block, because `transaction_per_migration` is left at its default of False. `compare_server_default` is not enabled, so server defaults are not compared by `alembic check` or autogenerate.

### 15.8 `backend/alembic.ini` and template

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
# sqlalchemy.url is taken from the DATABASE_URL environment variable (see alembic/env.py)
```

- Loggers: `root` (WARN, console), `sqlalchemy` (qualname `sqlalchemy.engine`, WARN), `alembic` (INFO).
- Handler `console`: `StreamHandler`, `args = (sys.stderr,)`, level NOTSET, formatter `generic`.
- Formatter `generic`: `format = %(levelname)-5.5s [%(name)s] %(message)s`, `datefmt = %H:%M:%S`.
- The file has no branding, so HireFlow's copy is identical.
- `alembic/script.py.mako` is the standard template, with `from __future__ import annotations` and typed `revision`, `down_revision`, `branch_labels` and `depends_on` declarations (`str | None`, `str | Sequence[str] | None`).

**Operational wrappers**:
- `scripts/migrate.py`:
  - Default action: `wait_for_db()`. On SQLite it then runs `create_all()` and prints `SQLite: tables created`. On PG it takes `pg_advisory_lock(7214553901)`, runs `python -m alembic upgrade head` in `backend/`, and unlocks in a `finally` block.
  - `--check` runs `alembic check`.
  - `--reembed` recomputes all job and resume embeddings.
- The Docker `api` role runs `scripts/migrate.py` before uvicorn, and the `migrate` role runs it alone.
- CI (`.github/workflows/ci.yml`, service `pgvector/pgvector:pg16`) runs `alembic upgrade head`, then `alembic check`, then `alembic downgrade base`, then `alembic upgrade head`.

### 15.9 HireFlow squash

- In HireFlow the six source migrations are **consolidated into a single fresh revision `0001_initial_schema`**. The file is `backend/alembic/versions/0001_initial_schema.py`, it is the only file in `versions/`, and it has `down_revision = None`, so it is both base and head. Its revision identifier string follows the source's numeric style, `'0001'`.
- Its `upgrade()` creates the **complete final schema**: everything documented in Section 2.
  - The extensions `vector` and `pg_trgm`.
  - The 7 PG ENUM types with the exact value lists and order from 2.12.
  - All 10 tables with all **199** columns, with the exact types and lengths, nullability, the two `server_default false` columns, and the FKs with their ondelete actions.
  - The PKs and the named and unnamed unique constraints.
  - All 23 ORM indexes, including `idx_jobs_company_tier` and `idx_jobs_company_verdict`.
  - The 4 raw-SQL indexes: `idx_jobs_embedding` (ivfflat, `vector_cosine_ops`, `lists = 100`), `idx_jobs_active` (partial), `idx_jobs_title_trgm` (GIN `gin_trgm_ops`) and `idx_comms_action_required` (partial).
- Its `downgrade()` drops it all: every index, every table in FK-safe reverse order, and the 7 enum types (`DROP TYPE IF EXISTS`). Like the source, it may leave the `vector` and `pg_trgm` extensions installed.
- On an empty PostgreSQL 16 + pgvector database, **`alembic upgrade head` followed by `alembic check` must report no drift** ("No new upgrade operations detected"). The CI cycle `upgrade head → check → downgrade base → upgrade head` must also pass. `env.py` (with `MANUAL_INDEXES`/`include_object`, `compare_type=True`, `render_as_batch` on SQLite and `NullPool`), `alembic.ini` and `script.py.mako` are carried over unchanged.
- The resulting schema is identical to the one the source chain `0001…0006` produces. The columns from 0002–0006 are appended to each table in the order the source ALTERs added them. **Verified:** `pg_dump --schema-only` of the two databases matches line for line (877 lines; only `pg_dump`'s random `\restrict` token differs).
- **Adopting an existing AutoApply AI PostgreSQL database:** a database created by the source chain carries `alembic_version = '0006'`, a revision that does not exist in HireFlow. `alembic upgrade head` (which the `api` role runs on start) fails with "Can't locate revision identified by '0006'". Its schema is already identical, so re-stamp it once with `cd backend && alembic stamp --purge 0001`. **Verified:** after the stamp, `alembic current` reports `0001 (head)`, `upgrade head` is a no-op and `alembic check` reports no drift. SQLite installs (`./start.sh`) don't use Alembic (`create_all`), so an old `backend/data/autoapply.db` can be renamed to `backend/data/hireflow.db`. For either database, applications that were logged without a link store the old placeholder URL. HireFlow hides only `MANUAL_URL_PREFIX = "https://manual.hireflow.invalid/"`, so rewrite the old prefix once, or those placeholders will show as job links: `UPDATE jobs SET source_url = replace(source_url, 'https://manual.autoapply.invalid/', 'https://manual.hireflow.invalid/') WHERE source_url LIKE 'https://manual.autoapply.invalid/%';`. Everything else carries over:
  - Encrypted columns stay readable as long as the same `SECRET_KEY` / `ENCRYPTION_KEY` are kept.
  - Users sign in once more, because the cookie is now `hireflow_session`.
  - New Gmail labels and notification subjects use the `HireFlow` names.

---

## Section 16: Test Suite Inventory

Source: `backend/tests/` — `__init__.py` (empty), `conftest.py`, **20 `test_*.py` modules**, `load/locustfile.py`,
`fixtures/mock_ats/apply.html` and **18 files** in `fixtures/scrapers/`.

**Totals:** 219 `def test_` functions → **280 collected test items** (parametrization). Reference results:
**280 passed on SQLite**; **278 passed + 2 skipped ("SQLite only") on PostgreSQL + pgvector**. 22 items carry
the `e2e` marker (launch a real Chromium; additionally `skipif` Chromium unavailable). The `postgres` marker is
declared in `pytest.ini` but not applied to any test.

### 16.1 How to run (`backend/pytest.ini`)

```ini
[pytest]
testpaths = tests
addopts = -ra --strict-markers
markers =
    e2e: end-to-end tests that launch a real Chromium browser (deselect with -m "not e2e")
    postgres: tests that require PostgreSQL + pgvector (TEST_DATABASE_URL)
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
```

| Goal | Command (from `backend/`) |
|---|---|
| Full suite on SQLite (default) | `python -m pytest` (`make test`) |
| PostgreSQL + pgvector | `TEST_DATABASE_URL=postgresql+psycopg://hireflow:hireflow@localhost:5432/hireflow_test python -m pytest` (`make test-pg`; the database must exist — CI runs `CREATE DATABASE hireflow_test`) |
| Browser end-to-end only | `python -m pytest -m e2e` (`make e2e`) |
| Skip browser tests | `python -m pytest -m "not e2e"` |
| Coverage (CI) | `python -m pytest -q --cov=app --cov-report=term-missing:skip-covered` |
| Load test | `python scripts/seed_db.py`, then `cd backend && locust -f tests/load/locustfile.py --host http://localhost:8000 --headless -u 100 -r 20 -t 2m --only-summary` |

SQLite vs PostgreSQL: `conftest.py` sets `DATABASE_URL` to `TEST_DATABASE_URL` when present, otherwise to a
temporary SQLite file (`<tmp>/hireflow-tests-*/test.db`). Two tests in `test_swipe_review.py` call
`pytest.skip("SQLite only")` on other dialects: `test_sqlite_upgrade_adds_new_columns` and
`test_no_write_lock_held_through_llm_calls`. Browser tests need Playwright Chromium
(`python -m playwright install chromium`, CI: `--with-deps`).

### 16.2 `conftest.py`

Environment set before any `app` import (see Section 14.5 for the full list; temp dir prefix `hireflow-tests-`).
Module data: `FIXTURES = tests/fixtures`, `SAMPLE_RESUME_TEXT` (Jane Doe — backend engineer, Acme Corp
Jan 2022–Present, Beta Labs intern, UC Berkeley B.S. CS 2017–2021, project JobBot, skills list).

| Fixture / helper | Scope | Behaviour |
|---|---|---|
| `_reset_state` | function, **autouse** | `Base.metadata.drop_all` + `create_all()`; `engine.dispose()` (fresh PostgreSQL connections, avoids cached enum plans); clears `rate_limiter._mem`; installs `LLMClient(providers=[])` (heuristic mode); after the test `set_llm(None)` |
| `db` | function | `SessionLocal()` session, committed and closed after the test |
| `client` | function | `TestClient(app.main.app)` context |
| `auth_client` | function | `client` after `POST /api/v1/auth/register` (`jane@example.com` / `supersecret1` / "Jane Doe", expects 201) |
| `master_resume` | function | `POST /api/v1/resumes/from-text` with `SAMPLE_RESUME_TEXT` (expects 201), returns JSON |
| `FakeProvider` | class | Deterministic LLM provider (`name = "fake"`): returns the canned JSON whose key appears in the prompt, records `calls` (prompt, schema, effort), optional `fail` exception, `is_retryable → False`; raises `AssertionError` when no response matches |
| `fake_llm` | function | Returns `install(responses, fail=None)` that builds a `FakeProvider` and installs it via `set_llm(LLMClient(providers=[provider]))` |

### 16.3 Test modules

| File | `def test_` | Collected | Markers | What it covers |
|---|---|---|---|---|
| `test_api.py` | 13 | 13 | — | API integration (TestClient + SQLite): auth flow, preference validation, muting notification popups, resume PDF upload + edit, user-scoped files, job import by URL (`careers_jsonld.html`) and prepare without a browser, approval gate, approval requiring answers and learning them, import without resume doesn't prepare, cross-user access denied, manual status + interviews, export + delete account, Gmail webhook + health. |
| `test_company_check.py` | 8 | 8 | — | Company catalog matching (legal names vs look-alikes), verdict rules, AI verification only when the posting backs it up, Internshala capped at a quarter keeping the best, top-companies scraper keeps that company's internships, scan caps Internshala / flags fraud / files top companies, fraud already in the deck skipped, new preferences validated. |
| `test_e2e_pipeline.py` | 3 | 3 | module `pytestmark = pytest.mark.e2e`; each `skipif` no Chromium | Full pipeline against a local mock company site + ATS (`fixtures/mock_ats/apply.html`): scan → match → tailor → fill in Chromium → approval → submit; swipe keep then auto-submit; swipe keep stops for eligibility questions. |
| `test_form_filling.py` | 5 | 5 | 1 × `e2e` (+ skipif) | Real-browser Indian internship form (tricky fields), `choose_option` wording matches, dates/numbers/length limits, resume facts answering education/location questions, ambiguous dates following the box format. |
| `test_intern_level.py` | 13 | 43 | 2 × `parametrize` | Intern titles only, internship job type without "intern" in the title, eligibility for a 2nd-year student, graduation years, graduation year source (you → resume → estimate), full-time search untouched, scrapers keep internships only, Internshala allowance, known postings don't count, scan keeps ten Internshala + interns only, full-time cards skipped, student settings, presets keep internships only (except new-grad). |
| `test_internshala_apply.py` | 40 | 48 | 12 × `e2e`, 5 × `parametrize`, `needs_browser` skipif | Internshala bot against a local mock of Internshala (easy-apply modal, Quill editor, availability radios, custom questions, resume interstitial, external/closed/already-applied listings, login redirect, profile gate): staging then submit, review corrections sent, notice-period "Other", logged-out/sign-up detection, presenting the synced browser's UA, unanswered required never submitted, session probe, cookie conversion, cover-letter/availability helpers, session-sync API never returns cookie values, preferences, blocker logic, staging/short-circuit while bot off, re-staging when turned on, session expiry flag, auto-submit pref, daily limit, expired session back to review, already-applied tracking, external listing waiting, keep→prepare→review→submit, disconnect stickiness, "Apply with the bot" (one click, missing-reason messages, Internshala-only), refused login tried once, one browser per account, renewed cookies kept/stored, only verified companies auto-applied, marking a company legit releases waiting applications. |
| `test_internshala_check.py` | 2 | 3 | 1 × `e2e`, `parametrize("accepted", [True, False])`, skipif | `scripts/internshala_check.py`: reports what Internshala does with the synced login (names only); message when nothing is synced. |
| `test_llm.py` | 10 | 19 | `parametrize` over every `*_SCHEMA` in `llm_schemas` | `extract_json` variants, `render_prompt` substitution, system prompt contains the directives, fallback to second provider, refusal moves on, unavailable without providers, retry policy, schemas strict, Anthropic request shape and refusal handling. |
| `test_location_focus.py` | 14 | 14 | — | Default India internship targeting, location tiers, Delhi-first location score, ~90 % India per scan, search query uses focus, season rules + matching filter, review queue Delhi→India ordering, India preset + validation, India job-board domains, Internshala parser (`internshala_search.html`), search URLs, end-to-end search, Internshala jobs ask you to apply yourself. |
| `test_matching_and_tailoring.py` | 10 | 10 | — | Prefilter rules, heuristic scoring of a good match, LLM evaluation clamp + sum, priority ordering, years of experience excludes internships, truthfulness guard, skill support detection, heuristic tailor reorders without inventing, LLM tailoring through the guard, grounded heuristic cover letter. |
| `test_ollama.py` | 22 | 22 | — | Ollama provider: native `/api/chat` body with schema + small context, cloud key + no schema, think tags / missing nested keys, one JSON repair round, missing top-level key repair then failure, model-not-pulled and connection-refused messages, truncated reply error, busy retry, models without thinking, prompt shortening keeps instructions, prompt helpers, provider selection, `llm_budget`, base URL cleanup + Docker host, Ollama-only scan scores top jobs one at a time, embeddings padded + local fallback, integrations status without secrets, quick answer when Ollama is down, LLM test endpoint, background pull with progress, credentials in the URL never shown. |
| `test_questions_email_notify.py` | 9 | 9 | — | `choose_option`, rule-based answers, facts never guessed, LLM answers for subjective questions, e-mail heuristics, `process_message` updating status and creating an interview, notifier channels, rate limiter limits, stipend vs salary currency. |
| `test_resume_parser.py` | 9 | 9 | — | Heuristic section parsing, ATS-parseable PDF round trip, cover-letter PDF, DOCX extraction, extract-text errors, LLM parse when available, resume normalisation, one-text-object-per-word PDFs rebuilt into lines, wrapped bullets / education table / project stack. |
| `test_review_queue.py` | 5 | 5 | 1 × `e2e` (+ skipif) | "Ready to submit": rows needing attention first without duplicates, queue lists pending applications best match first, submit saves corrections and submits, refusal of what can't be sent, submitter types the corrections (browser). |
| `test_role_focus.py` | 8 | 21 | `parametrize` | AI-engineer focus, no focus no filter, preset built from the resume changes only what you look for, data-science titles skipped, AI scoring sees the focus, scan with the preset keeps AI/Python roles, waiting Java cards skipped, focus settings validated. |
| `test_scan_speed.py` | 8 | 8 | — | Sources searched concurrently, slow source left out, boards in parallel with single-board failure isolation, LinkedIn doesn't re-download saved postings, progress reported until done, Stop ends a running scan, parallel LLM scoring, sources wrap up before the limit. |
| `test_scrapers.py` | 14 | 14 | — | Snapshot tests, no network, one per platform: Greenhouse board / questions / fetch, Lever, Ashby, Workday, LinkedIn parsers + end-to-end search, Indeed parsers, Glassdoor + Wellfound parsers, generic JSON-LD + ATS delegation, helpers, 429 pauses the platform, company-name fallbacks, job page without JSON-LD uses site name. |
| `test_security.py` | 4 | 4 | — | Password hashing round trip, JWT scopes + expiry, randomized AES-GCM, tokens encrypted at rest. |
| `test_self_applied.py` | 7 | 7 | — | "I Applied" → applied + tracking, self-applied section filters, logging an application made anywhere, progress updates on every channel, recruiter update text / own e-mails ignored, progress digest, agent stands down when you applied mid-fill. |
| `test_swipe_review.py` | 15 | 15 | 2 tests `pytest.skip("SQLite only")` on PostgreSQL | Internship list scraper (`internship_listings.json`), `clean_url`, hard vs soft filters, internship preset + preset endpoint, review decisions, review requires resume + user scoping, SQLite upgrade adds new columns, undo skip only while skipped, stale prepare tasks never submit twice, undo during preparation respected, scan respects swipes made while running, no write lock held through LLM calls, `.env` inline comments are not values, resume strategies. |
| **Total** | **219** | **280** | 22 `e2e` items | |

### 16.4 Fixture data files

| File | Used by | Content |
|---|---|---|
| `fixtures/mock_ats/apply.html` | `test_e2e_pipeline.py` | "Software Engineer - Acme Corp" page with `form#application-form` (multipart, POST `/submit`): fields `first_name`, `last_name`, `email`, `phone`, `resume` (file), `cover_letter`, `auth` (radio), `sponsor`, `why`, `gender`, `consent` |
| `fixtures/scrapers/ashby_board.json` | `test_scrapers.py` | Ashby job-board API response |
| `fixtures/scrapers/careers_ats_links.html` | `test_scrapers.py` | Careers page linking ATS boards (delegation) |
| `fixtures/scrapers/careers_jsonld.html` | `test_scrapers.py`, `test_api.py` | Careers page with schema.org JobPosting JSON-LD |
| `fixtures/scrapers/glassdoor_search.html` | `test_scrapers.py` | Glassdoor search cards |
| `fixtures/scrapers/greenhouse_board.json` | `test_scrapers.py` | Greenhouse board (name) |
| `fixtures/scrapers/greenhouse_job_questions.json` | `test_scrapers.py` | Greenhouse job with `questions` |
| `fixtures/scrapers/greenhouse_jobs.json` | `test_scrapers.py` | Greenhouse jobs list (`content=true`) |
| `fixtures/scrapers/indeed_detail.html` | `test_scrapers.py` | Indeed `#jobDescriptionText` |
| `fixtures/scrapers/indeed_search.html` | `test_scrapers.py` | Indeed mosaic job-cards JSON |
| `fixtures/scrapers/internshala_search.html` | `test_location_focus.py` | Internshala search page cards |
| `fixtures/scrapers/internship_listings.json` | `test_swipe_review.py` | SimplifyJobs-style `listings.json` (Summer 2027, utm-tagged URLs) |
| `fixtures/scrapers/lever_postings.json` | `test_scrapers.py` | Lever postings (`mode=json`) |
| `fixtures/scrapers/linkedin_detail_easy.html` | `test_scrapers.py` | LinkedIn guest detail, Easy Apply |
| `fixtures/scrapers/linkedin_detail_external.html` | `test_scrapers.py` | LinkedIn guest detail with external `applyUrl` |
| `fixtures/scrapers/linkedin_search.html` | `test_scrapers.py` | LinkedIn guest search results |
| `fixtures/scrapers/wellfound_next.html` | `test_scrapers.py` | Wellfound `__NEXT_DATA__` Apollo state |
| `fixtures/scrapers/workday_detail.json` | `test_scrapers.py` | Workday CXS job detail |
| `fixtures/scrapers/workday_jobs.json` | `test_scrapers.py` | Workday CXS search response |

Other test servers (Internshala mock, review-queue form, mock company site) are built inline in the test
modules with `http.server` on local threads.

### 16.5 `load/locustfile.py` (no `def test_`)

Load test: dashboard traffic from many concurrent sessions (plan target: 100 users, p95 < 500 ms). Logs in once
at test start (`POST /api/v1/auth/login` with `LOCUST_EMAIL` / `LOCUST_PASSWORD`, defaults
`demo@example.com` / `demo-password-123`) and shares the Bearer token. `DashboardUser(HttpUser)`,
`wait_time = between(1, 3)`, `on_start` loads up to 50 application ids. Tasks (weight): `overview` (5:
`/agent/status`, `/applications?status=pending_approval`, `/notifications`), `applications` (4: list page 1 ×
25 + one random detail named `/api/v1/applications/[id]`), `jobs` (3), `analytics` (2:
`/analytics/overview?days=30`), `inbox_and_interviews` (2: `/communications`, `/interviews`), `agent_logs` (1:
`/agent/runs`), `health` (1: `/health`). Requires `locust` (in `requirements-dev.txt`).

---

## Migration verification

Phase 6 results for the HireFlow tree, run on 4 Oct 2026 against AutoApply AI `8fe0747`.

| # | Check | How | Result |
|---|---|---|---|
| 1 | File inventory | `git ls-files` (source) vs files committed in HireFlow | 317 source files → 312 carried over. The 5 not carried over are revisions `0002`–`0006`, folded into `0001`. Nothing dropped, nothing extra. `frontend/src/app/dashboard/logs/page.tsx` matches the `.gitignore` rule `logs/` (meant for runtime logs), so it is force-added exactly as in the source. |
| 2 | Content fidelity | Every source file put through the naming map and byte-compared with its HireFlow counterpart | 304 identical. 8 differ on purpose: the squashed `0001_initial_schema.py`, the wordmark in `brand.tsx`, and the 6 re-captured `docs/screenshots/*.png` (1440×900, seeded demo account, HireFlow branding). |
| 3 | Leftover names | `grep -ri 'auto[ _-]?apply'` | Only `auto_apply_threshold` (preference key) and one quoted user report in a test docstring. Both are intentional. |
| 4 | Schema (PostgreSQL 16 + pgvector) | `alembic upgrade head` → `alembic check` → `alembic downgrade base` → `alembic upgrade head` → `alembic check` | Upgrade, downgrade and re-upgrade all ran cleanly. Both checks: "No new upgrade operations detected". |
| 5 | Squash equivalence | `pg_dump --schema-only` of the old 6-revision chain vs the new single revision | Identical. The 877-line dumps differ only in `pg_dump`'s random `\restrict` session token. |
| 6 | Backend lint | `ruff check app tests alembic/env.py`, `ruff check ../scripts`, `bandit -q -r app -ll` | All pass. |
| 7 | Backend tests (SQLite) | `pytest -q` | 280 passed. Baseline: the AutoApply AI suite on the same machine also gives 280 passed. |
| 8 | Backend tests (PostgreSQL + pgvector, incl. browser end-to-end) | `TEST_DATABASE_URL=… pytest -q --cov=app` | 278 passed, 2 skipped (marked "SQLite only"). 78 % coverage. |
| 9 | Dashboard | `npm ci`, `npm run lint`, `npm run typecheck`, `npm run build` | All pass. The build generates 19 routes: every page in Section 5 plus `/_not-found`. |
| 10 | Extension | MV3 manifest check, `node --check *.js` | `HireFlow — Session Sync` v1.1.1. All scripts parse. |
| 11 | Docker | `docker build` of `backend/Dockerfile` and `frontend/Dockerfile`, then the CI smoke test | Both images build. The backend image imports `app.main` and `app.worker.celery_app` and launches Chromium 141. The dashboard image serves `/` with `<title>HireFlow</title>`. |
| 12 | Compose | `docker compose config -q` (dev + prod) | Valid. Projects: `hireflow` (postgres, redis, api, worker, beat, frontend + `ollama` profile) and `hireflow-prod` (+ caddy). |
| 13 | Shell scripts | `bash -n` / `sh -n` on `start.sh`, `scripts/*.sh`, `docker-entrypoint.sh` | All parse. |
| 14 | Running app | `uvicorn` + `next start` on SQLite with seeded demo data, driven by Playwright | Landing, login, overview, swipe review, application detail, settings and analytics all render with HireFlow branding. Live updates connect. |
| 15 | Spec cross-check | QA agent checks every endpoint, table/column, route, component, task, scraper, submitter, prompt, script and setting in this document against the HireFlow tree | See the QA report below. |
