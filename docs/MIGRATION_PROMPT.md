# HireFlow — Full Project Migration Prompt

> **Copy everything below this line and paste it into a new Claude conversation.**

---

You are a **Master Orchestrator Agent** responsible for executing a complete, zero-regression migration of an existing production-grade application called **"AutoApply AI"** into a new, clean repository called **"HireFlow"**.

## 🎯 MISSION

Migrate the entire AutoApply AI codebase (located at `~/autoapply-ai/autoapply-ai/`) into a brand-new GitHub repository named **`HireFlow`** at `~/HireFlow/`. The target tech stack is:

- **Backend**: FastAPI (Python 3.12+)
- **Database**: PostgreSQL 16 + pgvector extension (with SQLite fallback for local dev)
- **ORM**: SQLAlchemy 2.0 (async)
- **Authentication**: JWT (HS256) with HTTP-only secure cookies + Bearer token support
- **Task Queue**: Celery + Redis
- **Frontend**: Next.js 14 (App Router) + React 18 + TypeScript + Tailwind CSS + shadcn/ui
- **Browser Automation**: Playwright (Chromium)
- **Containerization**: Docker + Docker Compose
- **Reverse Proxy**: Caddy v2
- **CI/CD**: GitHub Actions
- **Cloud Deployment**: AWS ECS Fargate + Vercel

> **CRITICAL RULE**: The existing project already uses this exact stack. Your job is NOT to change the stack — it is to create a **pixel-perfect, feature-complete clone** in a new repository with the new name "HireFlow", ensuring every single feature, endpoint, model, component, automation, integration, and behavior is preserved with zero regressions. Think of this as a meticulous rebrand + clean-room rebuild.

---

## 📋 PHASE 0: PRE-MIGRATION — COMPLETE PROJECT STRUCTURE DOCUMENT

**Before writing any migration code**, you MUST first create a comprehensive **`PROJECT_SPECIFICATION.md`** file (save it at `~/HireFlow/PROJECT_SPECIFICATION.md`). This document serves as your source of truth and post-migration verification checklist. It must contain ALL of the following sections with every minute detail:

### Section 1: Complete Backend API Endpoint Registry
Document EVERY endpoint with:
- HTTP method, full path (e.g., `POST /api/v1/auth/login`)
- Request body schema (every field, type, validation rule)
- Response schema (every field, type)
- Authentication requirement (none, cookie, bearer, ws-token, extension-token)
- Rate limiting rules
- Side effects (emails sent, tasks queued, WebSocket events emitted, files created)

The endpoints to document (exhaustive list):

**Health & Core:**
| Method | Path | Auth |
|--------|------|------|
| GET | `/health` | No |
| GET | `/health/ready` | No |
| GET (WebSocket) | `/ws?token=...` | Yes (ws-token or cookie) |
| POST | `/webhooks/gmail` | No (Pub/Sub verification) |

**Auth (`/api/v1/auth`):**
| Method | Path | Auth |
|--------|------|------|
| GET | `/auth/config` | No |
| POST | `/auth/register` | No |
| POST | `/auth/login` | No |
| POST | `/auth/logout` | Yes |
| GET | `/auth/me` | Yes |
| POST | `/auth/password` | Yes |
| GET | `/auth/ws-token` | Yes |
| POST | `/auth/extension-token` | Yes |
| GET | `/auth/google/login` | No |
| GET | `/auth/google/connect` | Yes |
| GET | `/auth/google/callback` | Yes (via state token) |
| POST | `/auth/google/disconnect` | Yes |

**Users (`/api/v1/users`):**
| Method | Path | Auth |
|--------|------|------|
| GET | `/users/me` | Yes |
| PATCH | `/users/me` | Yes |
| GET | `/users/me/preferences` | Yes |
| PUT | `/users/me/preferences` | Yes |
| POST | `/users/me/progress-report` | Yes |
| POST | `/users/me/preferences/preset/{name}` | Yes |
| GET | `/users/me/field-mappings` | Yes |
| PUT | `/users/me/field-mappings` | Yes |
| DELETE | `/users/me/field-mappings/{field_name}` | Yes |
| PUT | `/users/me/ats-credentials` | Yes |
| GET | `/users/me/integrations` | Yes |
| POST | `/users/me/integrations/llm/test` | Yes |
| POST | `/users/me/integrations/ollama/pull` | Yes |
| GET | `/users/me/integrations/ollama/pull` | Yes |
| POST | `/users/me/integrations/linkedin-cookie` | Yes |
| DELETE | `/users/me/integrations/linkedin` | Yes |
| POST | `/users/me/integrations/linkedin/sync` | Yes |
| POST | `/users/me/integrations/internshala-session` | Yes |
| DELETE | `/users/me/integrations/internshala` | Yes |
| POST | `/users/me/integrations/internshala/check` | Yes |
| GET | `/users/me/export` | Yes |
| DELETE | `/users/me` | Yes |

**Resumes (`/api/v1/resumes`):**
| Method | Path | Auth |
|--------|------|------|
| POST | `/resumes/upload` | Yes |
| POST | `/resumes/from-text` | Yes |
| GET | `/resumes` | Yes |
| GET | `/resumes/master` | Yes |
| GET | `/resumes/{resume_id}` | Yes |
| PUT | `/resumes/{resume_id}` | Yes |
| POST | `/resumes/{resume_id}/set-master` | Yes |
| GET | `/resumes/{resume_id}/pdf` | Yes |
| DELETE | `/resumes/{resume_id}` | Yes |

**Jobs (`/api/v1/jobs`):**
| Method | Path | Auth |
|--------|------|------|
| GET | `/jobs` | Yes |
| GET | `/jobs/{job_id}` | Yes |
| POST | `/jobs/import` | Yes |
| POST | `/jobs/{job_id}/evaluate` | Yes |
| POST | `/jobs/{job_id}/prepare` | Yes |

**Applications (`/api/v1/applications`):**
| Method | Path | Auth |
|--------|------|------|
| GET | `/applications` | Yes |
| GET | `/applications/review-queue` | Yes |
| POST | `/applications/{id}/submit` | Yes |
| GET | `/applications/{id}` | Yes |
| PATCH | `/applications/{id}` | Yes |
| POST | `/applications/{id}/approve` | Yes |
| POST | `/applications/{id}/skip` | Yes |
| POST | `/applications/{id}/withdraw` | Yes |
| POST | `/applications/{id}/mark-applied` | Yes |
| POST | `/applications/manual` | Yes |
| POST | `/applications/{id}/restage` | Yes |
| POST | `/applications/{id}/prepare` | Yes |
| PUT | `/applications/{id}/resume` | Yes |
| POST | `/applications/{id}/status` | Yes |
| GET | `/applications/{id}/history` | Yes |

**Review (`/api/v1/review`):**
| Method | Path | Auth |
|--------|------|------|
| GET | `/review/queue` | Yes |
| POST | `/review/bulk` | Yes |
| POST | `/review/{application_id}` | Yes |
| POST | `/review/{application_id}/undo` | Yes |
| POST | `/review/{application_id}/details` | Yes |

**Agent (`/api/v1/agent`):**
| Method | Path | Auth |
|--------|------|------|
| POST | `/agent/start-scan` | Yes |
| GET | `/agent/status` | Yes |
| GET | `/agent/runs` | Yes |
| GET | `/agent/runs/{run_id}` | Yes |
| POST | `/agent/runs/{run_id}/cancel` | Yes |
| POST | `/agent/check-email` | Yes |

**Communications (`/api/v1/communications`):**
| Method | Path | Auth |
|--------|------|------|
| GET | `/communications` | Yes |
| GET | `/communications/{id}` | Yes |
| PATCH | `/communications/{id}` | Yes |
| POST | `/communications/{id}/draft` | Yes |
| POST | `/communications/{id}/send` | Yes |

**Interviews (`/api/v1/interviews`):**
| Method | Path | Auth |
|--------|------|------|
| GET | `/interviews` | Yes |
| GET | `/interviews/{id}` | Yes |
| POST | `/interviews` | Yes |
| PATCH | `/interviews/{id}` | Yes |
| POST | `/interviews/{id}/prep` | Yes |
| DELETE | `/interviews/{id}` | Yes |

**Analytics (`/api/v1/analytics`):**
| Method | Path | Auth |
|--------|------|------|
| GET | `/analytics/overview` | Yes |

**Notifications (`/api/v1/notifications`):**
| Method | Path | Auth |
|--------|------|------|
| GET | `/notifications` | Yes |
| POST | `/notifications/{id}/read` | Yes |
| POST | `/notifications/read-all` | Yes |

**Files (`/api/v1/files`):**
| Method | Path | Auth |
|--------|------|------|
| GET | `/files/{key:path}` | Yes |

### Section 2: Complete Database Schema Registry
Document EVERY table with EVERY column:

**Table: `users`**
- `id` UUID PK default uuid4
- `email` VARCHAR(255) unique indexed not-null
- `hashed_password` VARCHAR(255) nullable (null for Google OAuth accounts)
- `full_name` VARCHAR(255) nullable
- `phone` VARCHAR(50) nullable
- `linkedin_url` VARCHAR(500) nullable
- `location` VARCHAR(255) nullable
- `google_access_token` EncryptedText nullable
- `google_refresh_token` EncryptedText nullable
- `google_token_expiry` UTCDateTime nullable
- `google_scopes` EncryptedJSON nullable
- `google_email` VARCHAR(255) nullable
- `gmail_history_id` VARCHAR(100) nullable
- `gmail_watch_expiration` UTCDateTime nullable
- `linkedin_session_cookie` EncryptedText nullable
- `linkedin_session_valid` BOOLEAN default=False
- `linkedin_profile_snapshot` JSON nullable
- `internshala_session` EncryptedJSON nullable
- `internshala_session_valid` BOOLEAN default=False
- `ats_credentials` EncryptedJSON nullable
- `preferences` JSON not-null (defaults to full preset structure)
- `consents` JSON not-null (defaults to GDPR consent schema)
- `is_active` BOOLEAN default=True
- `last_scan_at` UTCDateTime nullable
- `created_at` UTCDateTime default now(UTC)
- `updated_at` UTCDateTime default now(UTC)
- Relationships: resumes (1:M), applications (1:M), agent_runs (1:M), notifications (1:M), field_mappings (1:M) — all cascade delete-orphan

**Table: `jobs`**
- `id` UUID PK
- `company_name` VARCHAR(255) not-null indexed
- `company_logo_url` VARCHAR(1000) nullable
- `company_domain` VARCHAR(255) nullable
- `role_title` VARCHAR(255) not-null indexed
- `description` TEXT not-null
- `requirements` JSON nullable
- `nice_to_haves` JSON nullable
- `job_type` VARCHAR(50) enum(full_time, part_time, contract, internship)
- `experience_level` VARCHAR(50) enum(internship, entry, mid, senior, lead, executive)
- `location` VARCHAR(255) nullable
- `is_remote` BOOLEAN default=False indexed
- `salary_min` INTEGER nullable
- `salary_max` INTEGER nullable
- `salary_currency` VARCHAR(10) default="USD"
- `source_url` VARCHAR(2000) not-null
- `source_platform` VARCHAR(50) enum(greenhouse, lever, workday, ashby, linkedin, indeed, glassdoor, wellfound, custom)
- `application_url` VARCHAR(2000) not-null
- `external_id` VARCHAR(255) nullable
- `easy_apply` BOOLEAN default=False
- `dedupe_key` VARCHAR(64) unique not-null indexed (SHA-256 hash)
- `description_embedding` Vector(1536) nullable
- `extracted_skills` JSON nullable
- `raw_data` JSON nullable
- `posted_date` DATE nullable
- `deadline_date` DATE nullable
- `is_active` BOOLEAN default=True indexed
- `last_checked` UTCDateTime default now(UTC)
- `created_at` UTCDateTime default now(UTC)
- Indexes: GIN trigram on role_title (pg_trgm), IVFFlat on description_embedding (vector_cosine_ops, lists=100)

**Table: `resumes`**
- `id` UUID PK
- `user_id` UUID FK(users.id, CASCADE) indexed
- `label` VARCHAR(255) not-null
- `original_file_url` VARCHAR(1000) nullable
- `original_filename` VARCHAR(255) nullable
- `raw_text` TEXT not-null
- `parsed_content` JSON not-null (ResumeContent schema)
- `skills_embedding` Vector(1536) nullable
- `is_master` BOOLEAN default=False indexed
- `is_active` BOOLEAN default=True
- `version` INTEGER default=1
- `parent_resume_id` UUID FK(resumes.id) nullable
- `tailored_for_job_id` UUID FK(jobs.id) nullable
- `changes_made` JSON nullable
- `pdf_url` VARCHAR(1000) nullable
- `created_at` UTCDateTime default now(UTC)
- `updated_at` UTCDateTime default now(UTC)

**Table: `applications`**
- `id` UUID PK
- `user_id` UUID FK(users.id, CASCADE) indexed
- `job_id` UUID FK(jobs.id, CASCADE) indexed
- `status` VARCHAR(50) enum(discovered, matched, tailoring, tailored, pending_approval, approved, staging, staged, submitting, submitted, failed, skipped, withdrawn, rejected, interviewing, offered, accepted) indexed
- `match_score` FLOAT nullable indexed (0-100)
- `match_reasoning` TEXT nullable
- `match_details` JSON nullable
- `similarity_score` FLOAT nullable
- `review_decision` VARCHAR(20) nullable (keep/skip)
- `reviewed_at` UTCDateTime nullable
- `auto_submit` BOOLEAN default=False
- `tailored_resume_id` UUID FK(resumes.id) nullable
- `tailored_resume_pdf_url` VARCHAR(1000) nullable
- `cover_letter` TEXT nullable
- `custom_answers` JSON nullable
- `field_overrides` JSON nullable
- `ats_platform` VARCHAR(50) nullable
- `form_fields` JSON nullable
- `needs_manual_review` BOOLEAN default=False indexed
- `manual_review_reason` TEXT nullable
- `form_screenshot_url` VARCHAR(1000) nullable
- `staged_at` UTCDateTime nullable
- `approved_at` UTCDateTime nullable
- `submitted_at` UTCDateTime nullable
- `confirmation_screenshot_url` VARCHAR(1000) nullable
- `confirmation_number` VARCHAR(255) nullable
- `error_log` TEXT nullable
- `retry_count` INTEGER default=0
- `notes` TEXT nullable
- `created_at` UTCDateTime default now(UTC)
- `updated_at` UTCDateTime default now(UTC)
- Unique constraint: (user_id, job_id)
- Relationships: status_history (1:M), communications (1:M), interviews (1:M) — all cascade delete-orphan

**Table: `application_status_history`**
- `id` UUID PK
- `application_id` UUID FK(applications.id, CASCADE) indexed
- `old_status` VARCHAR(50) nullable
- `new_status` VARCHAR(50) not-null
- `changed_by` VARCHAR(50) default="system"
- `notes` TEXT nullable
- `created_at` UTCDateTime default now(UTC)

**Table: `communications`**
- `id` UUID PK
- `application_id` UUID FK(applications.id, CASCADE) indexed
- `gmail_message_id` VARCHAR(255) unique not-null indexed
- `gmail_thread_id` VARCHAR(255) not-null indexed
- `sender_email` VARCHAR(255) not-null
- `sender_name` VARCHAR(255) nullable
- `recipient_email` VARCHAR(255) not-null
- `subject` VARCHAR(500) not-null
- `body_text` TEXT not-null
- `body_html` TEXT nullable
- `received_at` UTCDateTime not-null
- `detected_intent` VARCHAR(50) enum(interview_invite, rejection, offer, acknowledgment, information_request, other)
- `intent_confidence` FLOAT nullable
- `urgency` VARCHAR(20) enum(urgent, normal, low)
- `extracted_details` JSON nullable
- `suggested_reply` TEXT nullable
- `gmail_draft_id` VARCHAR(255) nullable
- `is_action_required` BOOLEAN default=False indexed
- `action_taken` VARCHAR(100) nullable
- `created_at` UTCDateTime default now(UTC)

**Table: `interviews`**
- `id` UUID PK
- `application_id` UUID FK(applications.id, CASCADE) indexed
- `communication_id` UUID FK(communications.id, SET NULL) nullable
- `google_event_id` VARCHAR(255) nullable
- `google_event_link` VARCHAR(1000) nullable
- `interview_type` VARCHAR(50) enum(recruiter_screen, technical, behavioral, system_design, hiring_manager, onsite, other)
- `scheduled_at` UTCDateTime not-null indexed
- `duration_minutes` INTEGER default=45
- `timezone` VARCHAR(50) default="UTC"
- `meeting_link` VARCHAR(1000) nullable
- `meeting_platform` VARCHAR(50) nullable
- `physical_location` VARCHAR(500) nullable
- `interviewers` JSON nullable
- `prep_notes` TEXT nullable
- `company_research` JSON nullable
- `likely_questions` JSON nullable
- `outcome` VARCHAR(50) nullable (pending, passed, failed, cancelled)
- `outcome_notes` TEXT nullable
- `reminder_24h_sent` BOOLEAN default=False
- `reminder_1h_sent` BOOLEAN default=False
- `created_at` UTCDateTime default now(UTC)
- `updated_at` UTCDateTime default now(UTC)

**Table: `agent_runs`**
- `id` UUID PK
- `user_id` UUID FK(users.id, CASCADE) indexed
- `run_type` VARCHAR(50) enum(scan, tailor, apply, email_sync, full_cycle)
- `status` VARCHAR(50) enum(pending, running, completed, failed, cancelled) indexed
- `trigger` VARCHAR(50) default="manual"
- `jobs_discovered` INTEGER default=0
- `jobs_matched` INTEGER default=0
- `applications_prepared` INTEGER default=0
- `applications_submitted` INTEGER default=0
- `errors_count` INTEGER default=0
- `error_log` JSON nullable
- `progress` JSON nullable
- `started_at` UTCDateTime default now(UTC)
- `completed_at` UTCDateTime nullable

**Table: `notifications`**
- `id` UUID PK
- `user_id` UUID FK(users.id, CASCADE) indexed
- `event_type` VARCHAR(50) not-null
- `title` VARCHAR(255) not-null
- `body` TEXT not-null
- `link` VARCHAR(1000) nullable
- `data` JSON nullable
- `is_read` BOOLEAN default=False indexed
- `created_at` UTCDateTime default now(UTC)

**Table: `user_field_mappings`**
- `id` UUID PK
- `user_id` UUID FK(users.id, CASCADE) indexed
- `field_name` VARCHAR(255) not-null
- `field_value` TEXT not-null
- `field_type` VARCHAR(50) default="text"
- Unique constraint: (user_id, field_name)

### Section 3: Custom SQLAlchemy Type Implementations
- `UTCDateTime`: PostgreSQL → TIMESTAMP WITH TIME ZONE; SQLite → ISO 8601 TEXT with UTC roundtrip
- `JSONType`: PostgreSQL → native JSONB; SQLite → JSON-serialized TEXT
- `EmbeddingType(dim=1536)`: PostgreSQL → pgvector Vector(1536); SQLite → comma-separated float TEXT
- `EncryptedText`: AES-256-GCM with 12-byte nonce, format `v1:{base64(nonce+ciphertext+tag)}`
- `EncryptedJSON`: Same encryption over JSON-serialized dicts

### Section 4: Security Architecture
- Password hashing: SHA-256 pre-hash → bcrypt cost 12 (prevents 72-byte truncation)
- JWT scopes: `access` (7 days), `ws` (5 min), `extension` (180 days), `oauth_state` (15 min)
- Session cookie: `autoapply_session`, httpOnly, SameSite=Lax (None in prod + Secure)
- AES-256-GCM encryption at rest for all OAuth tokens, session cookies, ATS credentials
- Rate limiting: SlowAPI — auth endpoints 5/minute, global default 300/minute
- Security headers: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy
- CORS: Configurable origins with credentials support

### Section 5: Complete Frontend Route Registry
| Route | Description |
|-------|-------------|
| `/` | Public landing page — hero, marquee, pipeline motion, swipe preview, CTA |
| `/login` | Email/password + Google OAuth sign in |
| `/register` | Account creation with name, email, password + Google OAuth |
| `/api/health` | BFF health check (Next.js route handler) |
| `/dashboard` | Overview — onboarding checklist, KPI tiles, scan status, activity timeline |
| `/dashboard/review` | Tinder-style swipe deck — drag cards, keyboard nav (←→AZ), bulk actions |
| `/dashboard/submit` | Staged application review — field-by-field confirmation, inline editing |
| `/dashboard/applications` | Applications directory — status tabs, search, sort, pagination |
| `/dashboard/applications/[id]` | Application detail — 7 tabs (form, resume, cover letter, questions, match, job desc, timeline) |
| `/dashboard/applied` | Manual "I Applied" tracker — funnel stages, follow-up alerts |
| `/dashboard/jobs` | Discovered jobs catalog — filters, URL importer |
| `/dashboard/emails` | Recruiter email inbox — intent badges, AI draft/send replies |
| `/dashboard/interviews` | Interview calendar — AI prep notes, questions, company research |
| `/dashboard/analytics` | Metrics dashboard — Recharts charts, conversion tables |
| `/dashboard/logs` | Agent execution history — run details, console logs |
| `/dashboard/resume` | Resume Lab — upload, editor, PDF preview, LinkedIn diff |
| `/dashboard/settings` | 7-tab settings — mass apply, preferences, sources, answers, integrations, profile, privacy |

### Section 6: Frontend Component Inventory
Document all 30+ components in `src/components/` with their props, behavior, and animations.

### Section 7: Real-Time Architecture
- WebSocket at `/ws` with ticket-based auth
- Heartbeat: ping every 25s client-side, 30s server-side
- Reconnection: exponential backoff up to 30s
- Redis Pub/Sub channel `autoapply:events` for multi-worker scaling
- Event types: `notification`, `scan_progress`, `application_updated`, `agent_run_updated`, `application_staged`, `application_submitted`, `interview_detected`, `interview_reminder`
- Service Worker (`sw.js`) for OS-level push notifications and offline shell caching

### Section 8: Background Task Registry (Celery Beat)
| Task | Schedule | Description |
|------|----------|-------------|
| `scan_due_users` | Hourly at :07 | Check scan intervals, enqueue scans |
| `check_all_emails` | Every 5 min | Gmail inbox sync for all users |
| `renew_gmail_watches` | Daily 03:17 UTC | Renew Gmail push subscriptions |
| `interview_reminders` | Every 10 min | 24h and 1h interview reminders |
| `linkedin_sync_all` | Daily 06:23 UTC | Refresh LinkedIn profile snapshots |
| `weekly_summary` | Mon 08:41 UTC | 7-day funnel metrics digest |
| `progress_digest` | Hourly at :43 | Daily progress digest at ~20:00 local |
| `retention_cleanup` | Daily 04:11 UTC | Purge data older than 2 years |
| `expire_stale_jobs` | Daily 05:03 UTC | Mark jobs inactive after 45 days |

### Section 9: Scraper Registry
- `greenhouse.py` — Greenhouse ATS API scraper
- `lever.py` — Lever ATS API scraper
- `ashby.py` — Ashby ATS API scraper
- `workday.py` — Workday ATS scraper (browser-based)
- `linkedin.py` — LinkedIn scraper (authenticated via li_at cookie)
- `indeed.py` — Indeed scraper (browser-based)
- `glassdoor.py` — Glassdoor scraper (browser-based)
- `wellfound.py` — Wellfound (AngelList) scraper
- `internshala.py` — Internshala scraper + auto-apply bot
- `internships.py` — GitHub curated internship feeds (SimplifyJobs, vanshb03)
- `generic.py` — Generic HTML job page scraper
- `base.py` — Base scraper abstract class
- `ats_detect.py` — ATS platform auto-detection
- `browser_scraper.py` — Browser-based scraper base class

### Section 10: Submitter Registry
- `greenhouse_submit.py` — Greenhouse form filler
- `lever_submit.py` — Lever form filler
- `workday_submit.py` — Workday form filler
- `linkedin_easy_apply.py` — LinkedIn Easy Apply automation
- `internshala_apply.py` — Internshala application bot
- `generic_submit.py` — Generic HTML form filler
- `base.py` — Base submitter abstract class
- `form_engine.py` — Universal form detection and field mapping engine

### Section 11: AI/LLM Prompt Files
All 11 prompt files from `prompts/` directory:
1. `master_system.txt` — Core operational constitution with 4 directives
2. `job_evaluation.txt` — 5-criteria scoring (0-100)
3. `resume_tailor.txt` — Resume customization with anti-hallucination guards
4. `cover_letter.txt` — 200-300 word structured cover letters
5. `question_answerer.txt` — ATS question answering with confidence flagging
6. `form_field_mapper.txt` — HTML form-to-profile field mapping
7. `email_parser.txt` — Recruiter email intent classification
8. `interview_prep.txt` — Interview briefing generation
9. `linkedin_profile_diff.txt` — LinkedIn vs resume change detection
10. `resume_parser.txt` — Unstructured text to structured JSON parsing
11. `connection_test.txt` — LLM connectivity verification

### Section 12: Browser Extension (Manifest V3)
- `manifest.json` — Permissions: cookies, storage, alarms; hosts: linkedin.com, internshala.com
- `background.js` — Cookie extraction (li_at, Internshala session), 12h alarm sync, cookie change listener
- `content.js` — LinkedIn profile URL detection from DOM
- `popup.html` + `popup.js` — Configuration UI for dashboard URL and API token

### Section 13: Infrastructure & Deployment
- Docker Compose (dev): postgres, redis, api, worker, beat, frontend, ollama (optional profile)
- Docker Compose (prod): Caddy, resource limits, restart policies, log rotation
- Backend Dockerfile: Playwright/Python base, entrypoint routing (api/worker/beat/migrate/seed)
- Frontend Dockerfile: Multi-stage Next.js standalone build
- Caddyfile: Auto-TLS, zstd/gzip, API/frontend reverse proxy, security headers
- start.sh: 449-line bootstrap with --docker/--stop/--demo/--prod/--reset/--ollama/--no-open flags
- start.bat: Windows Docker bootstrap
- CI: 4-job pipeline (backend lint/test, frontend build, extension validate, docker smoke test)
- CD: deploy-backend.yml (AWS ECR + ECS Fargate), deploy-frontend.yml (Vercel)
- server-setup.sh: One-command Ubuntu VPS provisioner

### Section 14: Complete Environment Variables
Document ALL 80+ environment variables with their types, defaults, and purposes (reference the full list from the source `.env.example` and `app/config.py`).

### Section 15: Alembic Migration History
- `0001_initial_schema` — Base tables, extensions (uuid-ossp, vector, pg_trgm), enums, vector indices
- `0002_swipe_review` — review_decision, reviewed_at columns
- `0003_scan_progress` — Real-time scanning progress JSON fields
- `0004_internshala_and_overrides` — Internshala session, field overrides, ATS credentials

### Section 16: Test Suite Inventory
Document all test files, what they test, and their fixtures. Include load testing (Locust).

---

## 🏗️ PHASE 1: REPOSITORY INITIALIZATION

1. Create a new directory at `~/HireFlow/`
2. Initialize git: `git init`
3. Create `.gitignore`, `.gitattributes`, `LICENSE` (MIT, Copyright 2026 HireFlow contributors)
4. Rename ALL references from "AutoApply AI" / "autoapply-ai" / "autoapply" to "HireFlow" / "hireflow" / "HireFlow":
   - Package names, import paths, Docker image tags, cookie names (`hireflow_session`), Celery app names, database names, env var prefixes where applicable, README branding, landing page copy, manifest.json extension name, CI workflow names, docker-compose service names
5. Create the complete directory structure mirroring the original

---

## 🔧 PHASE 2: BACKEND MIGRATION

Migrate the entire backend preserving:
- **Every** FastAPI router, endpoint, request/response schema
- **Every** SQLAlchemy model with exact column types, constraints, indexes, relationships
- **Every** custom type (UTCDateTime, JSONType, EmbeddingType, EncryptedText, EncryptedJSON)
- **Every** Pydantic v2 schema with all validators
- **Every** service module (LLM client, embeddings, job matcher, resume parser/tailor, question answerer, review sheet, application service, agent orchestrator, calendar manager, gmail service, google oauth, email parser, linkedin sync, notifier, pdf generator, presets, privacy, progress/scan_progress, rate limiter, text_utils, location_focus)
- **Every** scraper (greenhouse, lever, ashby, workday, linkedin, indeed, glassdoor, wellfound, internshala, internships, generic + base, ats_detect, browser_scraper)
- **Every** submitter (greenhouse, lever, workday, linkedin_easy_apply, internshala, generic + base, form_engine)
- **Every** automation module (browser stealth, captcha solving, human emulation, proxy rotation)
- **Every** Celery task and beat schedule
- **Every** WebSocket event type and Redis Pub/Sub logic
- **Every** middleware (CORS, security headers, rate limiting)
- **Every** Alembic migration (renumbered as fresh 0001 with complete schema)
- **Every** dependency from `requirements.txt` and `requirements-dev.txt`
- The docker-entrypoint.sh with role routing
- The Dockerfile with Playwright base image

---

## 🎨 PHASE 3: FRONTEND MIGRATION

Migrate the entire frontend preserving:
- **Every** page and route (landing, login, register, all 13 dashboard pages)
- **Every** component (30+ components including dashboard-shell, swipe-card, scan-progress, analytics-charts, auth-form, approval-modal, resume-editor, i-applied-button, etc.)
- **Every** hook (use-applications, use-scan, use-websocket)
- **Every** utility (api-client with 401 redirect, types.ts with all interfaces, utils.ts)
- **Every** API call (all 80+ fetch calls documented above)
- **Every** form with validation logic (auth, submit review, approval modal, manual application, job import, internshala bot, saved answers, account deletion, resume import)
- **Every** animation (Framer Motion: swipe gestures, page transitions, nav indicators, number rollups, particle bursts)
- **Every** Recharts visualization
- The complete Tailwind design system (ink/paper themes, noise overlay, custom animations, typography)
- All 26 shadcn/ui primitives
- The Service Worker (sw.js)
- The PWA manifest
- All Radix UI primitives
- SWR caching strategy with adaptive polling intervals
- next.config.js with BFF proxy, 15-minute timeout, security headers, standalone output
- The multi-stage Dockerfile

---

## 🔌 PHASE 4: EXTENSION MIGRATION

Migrate the Chrome extension:
- Rename to "HireFlow — Session Sync"
- Update manifest.json with new name/description
- Preserve all functionality: LinkedIn cookie sync, Internshala session sync, alarm-based re-sync, cookie change listeners, popup UI

---

## ⚙️ PHASE 5: INFRASTRUCTURE MIGRATION

Migrate all infrastructure:
- docker-compose.yml (rename services, images)
- docker-compose.prod.yml (same with production hardening)
- Caddyfile
- Makefile (all targets)
- start.sh (rename all references, preserve all flags and logic)
- start.bat
- .env.example (complete with all 80+ variables)
- GitHub Actions CI/CD (all 4 workflows)
- scripts/ (account.py, demo_site.py, init-env.sh, local_scheduler.py, migrate.py, seed_db.py, server-setup.sh, test_scraper.py)
- prompts/ (all 11 prompt files)
- docs/ (screenshots directory)
- PLAN.md → Updated with HireFlow branding
- README.md → Updated with HireFlow branding, same structure

---

## 🧪 PHASE 6: VERIFICATION & TESTING

After migration is complete:
1. **Schema Verification**: Run `alembic upgrade head` → `alembic check` (zero drift)
2. **Endpoint Verification**: Cross-reference every endpoint in `PROJECT_SPECIFICATION.md` against the migrated code — confirm all exist with correct methods, paths, schemas, auth requirements
3. **Model Verification**: Cross-reference every table/column in the spec against `app/models/`
4. **Frontend Verification**: Cross-reference every route in the spec against `src/app/`
5. **Component Verification**: Confirm all components exist and render
6. **Linting**: Run `ruff check` on backend, `npm run lint` and `npm run typecheck` on frontend
7. **Test Execution**: Run full test suite
8. **Docker Build**: Verify `docker compose build` succeeds
9. **Import Verification**: Verify all Python imports resolve correctly (no broken references to old names)

---

## 🚀 PHASE 7: GIT PUSH

1. `git add -A`
2. `git commit -m "feat: initial HireFlow migration from AutoApply AI — complete feature-parity migration with FastAPI, PostgreSQL, SQLAlchemy, JWT auth, Next.js 14, Celery, Docker, and full CI/CD pipeline"`
3. Create the GitHub repository: `gh repo create HireFlow --public --source=. --push` (or private if preferred)
4. `git push -u origin main`

---

## 🤖 MULTI-AGENT EXECUTION STRATEGY

You MUST use a **multi-agent architecture** to execute this migration efficiently. Organize as follows:

### Master Orchestrator Agent (YOU)
- Controls the overall flow
- Delegates tasks to specialized subagents
- Tracks progress across all phases
- Makes final decisions on conflicts
- Runs the final verification phase

### Subagent 1: Documentation Agent
- **Task**: Create the complete `PROJECT_SPECIFICATION.md` (Phase 0)
- **Input**: Read every file in the source repository
- **Output**: The exhaustive specification document

### Subagent 2: Backend Migration Agent
- **Task**: Migrate all backend code (Phase 2)
- **Subtasks**: Models → Schemas → Core → Services → Scrapers → Submitters → Automation → API Routes → Worker → Alembic → Config → Dockerfile
- **Rule**: Must preserve every endpoint, every model field, every service method

### Subagent 3: Frontend Migration Agent
- **Task**: Migrate all frontend code (Phase 3)
- **Subtasks**: Layout → Pages → Components → Hooks → Lib → Styles → Config → Dockerfile
- **Rule**: Must preserve every route, every component, every API call, every animation

### Subagent 4: Infrastructure Migration Agent
- **Task**: Migrate all infrastructure (Phase 4 + 5)
- **Subtasks**: Docker Compose → Scripts → CI/CD → Extension → Prompts → Docs → README
- **Rule**: Must preserve every script, every workflow, every configuration

### Subagent 5: Verification & QA Agent
- **Task**: Run Phase 6 verification
- **Input**: The completed migration + PROJECT_SPECIFICATION.md
- **Process**: Systematically verify every item in the spec exists in the migrated code
- **Output**: Pass/Fail report with specific discrepancies
- **Rule**: Must check every single endpoint, model, route, component — NO shortcuts

### Subagent 6: Git & Push Agent
- **Task**: Handle Phase 7
- **Process**: Stage, commit, create repo, push
- **Rule**: Must verify clean git status before pushing

---

## ⚠️ CRITICAL RULES — READ BEFORE STARTING

1. **ZERO FEATURE REGRESSION**: Every single feature in AutoApply AI must exist in HireFlow. Not one endpoint, model field, component, animation, scraper, submitter, prompt, script, or configuration may be dropped.

2. **ZERO NEW BUGS**: Do not introduce bugs. Copy logic faithfully. When in doubt, copy verbatim and only change naming references.

3. **NAMING CONSISTENCY**: Replace ALL occurrences of:
   - `autoapply-ai` → `hireflow`
   - `AutoApply AI` → `HireFlow`
   - `autoapply` → `hireflow`
   - `AUTOAPPLY` → `HIREFLOW`
   - `autoapply_session` → `hireflow_session`
   - Docker image tags: `autoapply-backend` → `hireflow-backend`, `autoapply-frontend` → `hireflow-frontend`

4. **DO NOT CHANGE THE TECH STACK**: The source already uses FastAPI + PostgreSQL + SQLAlchemy + JWT + Next.js + Celery + Docker. Keep it exactly the same.

5. **DO NOT "IMPROVE" OR "MODERNIZE"**: This is a migration, not a refactor. Keep the code structure, patterns, and conventions identical.

6. **PRESERVE ALL COMMENTS AND DOCSTRINGS**: Do not remove any existing documentation in the code.

7. **PRESERVE ALL ERROR HANDLING**: Every try/except, every HTTP status code, every error message.

8. **PRESERVE ALL TESTS**: Migrate the entire test suite with updated imports.

9. **SPECIFICATION FIRST**: Do NOT start coding until `PROJECT_SPECIFICATION.md` is complete and verified.

10. **VERIFY EVERYTHING**: The QA Agent must cross-check every item in the specification against the migrated code. If anything is missing, it must be added before the push.

---

## 📂 EXPECTED FINAL DIRECTORY STRUCTURE

```
~/HireFlow/
├── .dockerignore
├── .env.example
├── .git/
├── .gitattributes
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── deploy-backend.yml
│       └── deploy-frontend.yml
├── .gitignore
├── Caddyfile
├── LICENSE
├── Makefile
├── PLAN.md
├── PROJECT_SPECIFICATION.md
├── README.md
├── backend/
│   ├── .dockerignore
│   ├── Dockerfile
│   ├── docker-entrypoint.sh
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── ruff.toml
│   ├── alembic/
│   │   ├── alembic.ini
│   │   ├── env.py
│   │   └── versions/
│   │       └── 0001_initial_schema.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py
│   │   │   ├── serializers.py
│   │   │   ├── auth.py
│   │   │   ├── users.py
│   │   │   ├── resumes.py
│   │   │   ├── jobs.py
│   │   │   ├── applications.py
│   │   │   ├── review.py
│   │   │   ├── agent.py
│   │   │   ├── communications.py
│   │   │   ├── interviews.py
│   │   │   ├── analytics.py
│   │   │   └── files.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── database.py
│   │   │   ├── security.py
│   │   │   ├── redis.py
│   │   │   ├── storage.py
│   │   │   ├── websocket.py
│   │   │   └── logging_config.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── enums.py
│   │   │   ├── user.py
│   │   │   ├── job.py
│   │   │   ├── resume.py
│   │   │   ├── application.py
│   │   │   ├── interview.py
│   │   │   ├── communication.py
│   │   │   └── agent_run.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── job.py
│   │   │   ├── resume.py
│   │   │   ├── resume_content.py
│   │   │   ├── application.py
│   │   │   └── agent.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── llm.py
│   │   │   ├── llm_schemas.py
│   │   │   ├── ai_setup.py
│   │   │   ├── embeddings.py
│   │   │   ├── job_matcher.py
│   │   │   ├── resume_parser.py
│   │   │   ├── resume_tailor.py
│   │   │   ├── question_answerer.py
│   │   │   ├── review_sheet.py
│   │   │   ├── application_service.py
│   │   │   ├── agent_orchestrator.py
│   │   │   ├── calendar_manager.py
│   │   │   ├── gmail_service.py
│   │   │   ├── google_oauth.py
│   │   │   ├── email_parser.py
│   │   │   ├── linkedin_sync.py
│   │   │   ├── notifier.py
│   │   │   ├── pdf_generator.py
│   │   │   ├── presets.py
│   │   │   ├── privacy.py
│   │   │   ├── progress.py
│   │   │   ├── scan_progress.py
│   │   │   ├── rate_limiter.py
│   │   │   ├── text_utils.py
│   │   │   └── location_focus.py
│   │   ├── automation/
│   │   │   ├── __init__.py
│   │   │   ├── browser.py
│   │   │   ├── captcha.py
│   │   │   ├── human.py
│   │   │   └── proxy.py
│   │   ├── scrapers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── ats_detect.py
│   │   │   ├── browser_scraper.py
│   │   │   ├── generic.py
│   │   │   ├── ashby.py
│   │   │   ├── glassdoor.py
│   │   │   ├── greenhouse.py
│   │   │   ├── indeed.py
│   │   │   ├── internshala.py
│   │   │   ├── internships.py
│   │   │   ├── lever.py
│   │   │   ├── linkedin.py
│   │   │   ├── wellfound.py
│   │   │   └── workday.py
│   │   ├── submitters/
│   │   │   ├── __init__.py
│   │   │   ├── base.py
│   │   │   ├── form_engine.py
│   │   │   ├── generic_submit.py
│   │   │   ├── greenhouse_submit.py
│   │   │   ├── internshala_apply.py
│   │   │   ├── lever_submit.py
│   │   │   ├── linkedin_easy_apply.py
│   │   │   └── workday_submit.py
│   │   └── worker/
│   │       ├── __init__.py
│   │       ├── celery_app.py
│   │       ├── dispatch.py
│   │       ├── tasks_scan.py
│   │       ├── tasks_apply.py
│   │       ├── tasks_email.py
│   │       ├── tasks_sync.py
│   │       └── tasks_calendar.py
│   └── tests/
│       ├── conftest.py
│       ├── test_*.py (all test files)
│       └── load/
│           └── locustfile.py
├── docker-compose.yml
├── docker-compose.prod.yml
├── docs/
│   └── screenshots/
├── extension/
│   ├── manifest.json
│   ├── background.js
│   ├── content.js
│   ├── popup.html
│   ├── popup.js
│   ├── popup.css
│   ├── icon-48.png
│   └── icon-128.png
├── frontend/
│   ├── Dockerfile
│   ├── next.config.js
│   ├── package.json
│   ├── package-lock.json
│   ├── components.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── public/
│   │   ├── manifest.webmanifest
│   │   ├── sw.js
│   │   └── (icons)
│   └── src/
│       ├── app/
│       │   ├── layout.tsx
│       │   ├── template.tsx
│       │   ├── globals.css
│       │   ├── page.tsx
│       │   ├── login/page.tsx
│       │   ├── register/page.tsx
│       │   ├── api/health/route.ts
│       │   └── dashboard/
│       │       ├── layout.tsx
│       │       ├── template.tsx
│       │       ├── page.tsx
│       │       ├── review/page.tsx
│       │       ├── submit/page.tsx
│       │       ├── applications/
│       │       │   ├── page.tsx
│       │       │   └── [id]/page.tsx
│       │       ├── applied/page.tsx
│       │       ├── jobs/page.tsx
│       │       ├── emails/page.tsx
│       │       ├── interviews/page.tsx
│       │       ├── analytics/page.tsx
│       │       ├── logs/page.tsx
│       │       ├── resume/page.tsx
│       │       └── settings/page.tsx
│       ├── hooks/
│       │   ├── use-applications.ts
│       │   ├── use-scan.ts
│       │   └── use-websocket.ts
│       ├── lib/
│       │   ├── api-client.ts
│       │   ├── types.ts
│       │   └── utils.ts
│       └── components/
│           ├── (all 30+ components)
│           └── ui/
│               └── (26 shadcn primitives)
├── logs/
├── prompts/
│   ├── master_system.txt
│   ├── job_evaluation.txt
│   ├── resume_tailor.txt
│   ├── cover_letter.txt
│   ├── question_answerer.txt
│   ├── form_field_mapper.txt
│   ├── email_parser.txt
│   ├── interview_prep.txt
│   ├── linkedin_profile_diff.txt
│   ├── resume_parser.txt
│   └── connection_test.txt
├── scripts/
│   ├── account.py
│   ├── demo_site.py
│   ├── init-env.sh
│   ├── local_scheduler.py
│   ├── migrate.py
│   ├── seed_db.py
│   ├── server-setup.sh
│   ├── test_scraper.py
│   └── ruff.toml
├── start.sh
└── start.bat
```

---

**BEGIN EXECUTION NOW. Start with Phase 0 (PROJECT_SPECIFICATION.md), then proceed through all phases sequentially. Use multiple subagents for parallel execution where phases are independent. Do not skip any phase. Do not skip any file. The final QA verification is mandatory before pushing.**
