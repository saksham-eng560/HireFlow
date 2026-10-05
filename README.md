<p align="center">
  <img src="frontend/public/icon.svg" width="84" alt="HireFlow logo" />
</p>

<h1 align="center">HireFlow</h1>

<p align="center"><b>Swipe right. We apply.</b> An AI internship-application assistant that you run yourself.</p>

<p align="center">
  <a href="https://github.com/saksham-eng560/HireFlow/actions/workflows/ci.yml"><img src="https://github.com/saksham-eng560/HireFlow/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
  <a href="docs/TESTING.md"><img src="https://img.shields.io/badge/tests-439%20backend%20%2B%2015%20e2e-2563EB" alt="Tests" /></a>
  <a href="docs/TESTING.md"><img src="https://img.shields.io/badge/coverage-80%25-2563EB" alt="Coverage" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-2563EB" alt="MIT license" /></a>
  <a href="https://hireflow-three-woad.vercel.app"><img src="https://img.shields.io/badge/live%20demo-hireflow--three--woad.vercel.app-2563EB" alt="Live demo" /></a>
</p>

HireFlow finds internships, puts every one that passes your filters into a **Swipe Review** deck, and for each
job you keep it tailors your resume (truthfully), writes a cover letter, fills the application form in a real
browser and applies, then tracks the replies from Gmail and puts interviews on your calendar.

**Try it:** **[hireflow-three-woad.vercel.app](https://hireflow-three-woad.vercel.app)**, then **Try the demo**: one
click, fictional companies, nothing really sent. Or run the same demo on your machine with `./start.sh --demo`.
<!-- 60-second walkthrough: <video link> (add after recording) -->

<p align="center"><img src="docs/screenshots/landing.png" alt="HireFlow's landing page: Swipe right. We apply." width="900" /></p>

<table>
  <tr>
    <td width="50%"><img src="docs/screenshots/swipe-review.png" alt="Swipe Review: a job card with its match score, the skills you have and the ones it wants" /><br /><sub><b>Swipe Review.</b> Every matching internship, best first: keep or skip with a drag, a tap or ← →.</sub></td>
    <td width="50%"><img src="docs/screenshots/review.png" alt="Ready to submit: each prefilled field with Correct and Fix buttons" /><br /><sub><b>Ready to submit.</b> The agent filled the form and stopped short of Submit: check each field, fix anything, send.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/application.png" alt="An application: the screenshot of the filled form next to every field and its value" /><br /><sub><b>Proof of what was sent.</b> A screenshot of the filled form and every field, plus the tailored resume, cover letter and answers.</sub></td>
    <td><img src="docs/screenshots/onboarding.png" alt="Onboarding, step 1 of 8: welcome" /><br /><sub><b>Onboarding.</b> Eight short steps (or one click on <i>Load sample profile</i>), then the first scan.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/overview.png" alt="Overview: jobs waiting to swipe, applications sent, response rate, interviews, offers" /><br /><sub><b>Overview.</b> What's waiting for you, what was sent, and how employers are answering.</sub></td>
    <td><img src="docs/screenshots/applications.png" alt="Applications: every application with its match score and status" /><br /><sub><b>Applications.</b> Every application and its status, from needs approval to offer.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/interviews.png" alt="Interviews: upcoming interviews with prep notes and a meeting link" /><br /><sub><b>Interviews.</b> Created from recruiter e-mails, on your calendar, with prep notes.</sub></td>
    <td><img src="docs/screenshots/analytics.png" alt="Analytics: applications sent, response, interview and offer rates, daily activity" /><br /><sub><b>Analytics.</b> Response, interview and offer rates, and what gets callbacks.</sub></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/mass-apply.png" alt="Settings: one-click mass-apply presets" /><br /><sub><b>Mass-apply settings.</b> One-click presets for internships, startups, new grad and India.</sub></td>
    <td><img src="docs/screenshots/dark.png" alt="Swipe Review in the dark theme" /><br /><sub><b>Dark theme.</b> Deep navy, still blue and white.</sub></td>
  </tr>
  <tr>
    <td colspan="2" align="center"><img src="docs/screenshots/phone-swipe.png" alt="Swipe Review on a phone" width="300" /><br /><sub><b>On a phone.</b> Swipe the card right to keep, left to skip.</sub></td>
  </tr>
</table>

## Features

- **Finds the jobs.** Greenhouse, Lever, Ashby and Workday boards through their public APIs, any careers page
  (schema.org `JobPosting` data), curated internship lists, 107 startup boards with one click, and, only if you
  opt in, LinkedIn, Internshala, Indeed and Glassdoor. Duplicates are merged; scans run every few hours.
- **Swipe Review.** Every job that passed your filters, best match first, with a 0–100 score and why: the
  skills you have, the ones they want, location, term and visa sponsorship. Drag, tap or use ← →; undo any
  swipe; keep everything above a score in one click.
- **Resume tailoring, without inventing anything.** Your original file, light reordering, or full AI
  tailoring checked line by line against your master resume, plus a cover letter for the actual role.
- **Form filling across ATSs.** A real browser fills Greenhouse, Lever, Workday, LinkedIn Easy Apply and
  generic forms, with a screenshot of every filled form. Eligibility questions are never guessed.
- **Gmail and Calendar.** Replies are classified (acknowledged, interview, assessment, rejection, offer) and
  each application's status follows; interviews go on your calendar with prep notes.
- **Analytics.** Pipeline by status, response, interview and offer rates, time to first reply, which platforms
  answer, and the keywords that get callbacks.
- **Onboarding in minutes**, a sample profile to try it, and a guided first scan.
- **Works on your phone** (swipe gestures, installable as an app), in light and dark, and with a keyboard or a
  screen reader (no serious axe-core findings on any page).

The full tour, with every setting: [docs/USER_GUIDE.md](docs/USER_GUIDE.md).

## Architecture

```mermaid
flowchart LR
    web[Next.js dashboard] -- "/api/v1 proxy + WebSocket" --> api[FastAPI]
    api <--> db[(PostgreSQL + pgvector)]
    api --> redis[(Redis)]
    beat[Celery beat] --> redis --> worker[Celery workers]
    worker <--> db
    worker -- "APIs + Playwright" --> ats[ATS sites and careers pages]
    worker --> llm[LLMs: Anthropic → OpenAI → Ollama]
    worker --> gmail[Gmail + Calendar]
```

The API stays fast because everything slow (scans, AI calls, a browser filling a form) runs on Celery queues,
with retries and crash-safe hand-offs. One application's whole journey, why Celery and Playwright, and how the
LLM fallback works: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Tech stack

| | |
|---|---|
| Dashboard | Next.js 15, React 19, TypeScript, Tailwind CSS, Radix UI (shadcn/ui), SWR, framer-motion, Recharts |
| API | Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, Pydantic, slowapi |
| Data | PostgreSQL 16 + pgvector (SQLite for local use), Redis, local disk or S3 / Cloudflare R2 |
| Workers | Celery + beat, Playwright (Chromium) |
| AI | Anthropic, OpenAI or Ollama, with JSON-schema outputs and a heuristic fallback |
| Quality | pytest, Playwright e2e, axe-core, ruff, bandit, ESLint, pip-audit, npm audit, gitleaks, GitHub Actions |

## Quick start

```bash
git clone https://github.com/saksham-eng560/HireFlow.git && cd HireFlow
./start.sh --demo      # the demo: press "Try the demo" at http://localhost:3000
./start.sh             # your own agent: sign up and follow the onboarding
```

**What to try in the demo** (nothing is really sent; the data resets every night):

1. Open http://localhost:3000 and press **Try the demo**: you're signed in to a sample candidate with a few past
   applications, replies and interviews.
2. **Swipe Review**: keep a job (drag right or press →) and skip one (←). Undo with **Z**.
3. A few seconds later the kept job is in **Ready to submit**: its resume tailored and the form filled on the bundled
   demo careers site (dry run). Check each field, then open **Full details** to see the form screenshot.
4. Look around **Overview**, **Applications**, **Interviews** and **Analytics**, and try **Pause** in the header.
5. To see onboarding, sign out, **Get started** with any e-mail, and press **Load sample profile**.

Needs Python 3.11+ and Node 20+ (macOS, Linux or WSL). The first run creates `.env` with fresh secrets,
installs everything and prepares a local database; later runs start in seconds. `./start.sh --docker` runs the
full stack (PostgreSQL, Redis, workers) in Docker instead, and `./start.sh --ollama` sets up a free local AI
model. Everything works without an AI key, on built-in heuristics; add `ANTHROPIC_API_KEY` to `.env` for the
best results.

More: [running and self-hosting](docs/SELF_HOSTING.md) · [AI models](docs/AI_MODELS.md).

### Free AI with Ollama

[Ollama](https://ollama.com) runs open AI models on your own computer, free and private, with no API key:

1. Install it from https://ollama.com/download (Mac: open the app once; Linux:
   `curl -fsSL https://ollama.com/install.sh | sh`).
2. Run `./start.sh --ollama`. It downloads the default model (`qwen3.5:4b`, about 3.4 GB) once and adds
   `LLM_PROVIDER=ollama` and `OLLAMA_MODEL=qwen3.5:4b` to `.env`.
3. In the dashboard, open **Settings › Integrations › AI model** and press **Test AI**.

Choosing a model for your RAM, Docker, servers, Ollama Cloud, the deployed demo and troubleshooting:
**[docs/OLLAMA.md](docs/OLLAMA.md)**.

## Guardrails

Applying for someone is only useful if it never embarrasses them. These are enforced by the server, not just
the UI:

<p align="center"><img src="docs/screenshots/safety.png" alt="Safe by design: the guardrails, as shown on the landing page" width="900" /></p>

- **You pick every job.** Nothing is prepared for a job you didn't keep, and new accounts start with
  "Submit automatically" off.
- **A 10-minute undo window** on every automatic send, a daily cap (never above 25), at most 3 applications per
  company a week, and never the same job twice.
- **Eligibility is never guessed** and never sent to an AI; **experience is never invented** (a truthfulness
  check reverts anything not on your resume).
- **Job posts are treated as data**, not instructions (prompt-injection defences); every AI reply is
  schema-validated, and each user has a daily AI budget.
- **Proof of what was sent:** a screenshot before every submit, AI-written answers labelled and editable,
  a dry-run mode, and one switch to pause everything.
- **Site rules respected:** sources that forbid automation stay off unless you opt in; per-site rate limits
  and back-off; captchas pause the site.
- **Your data:** secrets encrypted at rest, CSRF and upload checks, PII kept out of logs, download everything
  or delete your account at any time.

Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#guardrails-and-where-theyre-enforced) ·
[docs/SECURITY.md](docs/SECURITY.md).

## Testing

```bash
make test        # backend suite (pytest), including real-Chromium tests
make e2e-demo    # Playwright through the dashboard in demo mode
make lint        # ruff, ESLint, TypeScript, colour contrast
make metrics     # measure the numbers below
```

Measured with `scripts/metrics.py`, not guessed: **439 backend tests (80% coverage) and 15 end-to-end tests**; on the demo
careers site the first scan takes about 0.3 s, sign-up to the first Swipe Review deck takes under a second of
server time (about 5 s through the UI), and 12 of 12 forms are filled in Chromium with every required field.
CI runs all of it plus migrations, security audits and Docker builds: [docs/TESTING.md](docs/TESTING.md).

## Deployment

- **Free public demo** (what runs at [hireflow-three-woad.vercel.app](https://hireflow-three-woad.vercel.app)): the
  dashboard on Vercel and the API, scheduler and Chromium in one free Hugging Face Space, deployed by
  [`deploy-space.yml`](.github/workflows/deploy-space.yml) after every green CI run:
  [docs/DEPLOY.md](docs/DEPLOY.md#free-deployment-vercel--hugging-face).
- **Always-on demo** (Vercel + Render + Neon + Upstash + Cloudflare R2 + Sentry): [docs/DEPLOY.md](docs/DEPLOY.md#always-on-deployment-render-neon-upstash-r2),
  with [`render.yaml`](render.yaml). Both are checked daily by a smoke test (`scripts/smoke_test.py`) that visits
  the deployment like a visitor would.
- **Your own server** (Docker Compose with automatic HTTPS, Oracle Cloud Always Free, AWS):
  [docs/SELF_HOSTING.md](docs/SELF_HOSTING.md#deployment).

## Roadmap

- A 60-second walkthrough video.
- Dedicated submitters for Ashby, SmartRecruiters and iCIMS (today they go through the generic form engine).
- Fair per-user queues and a separate browser-worker pool for many users.
- Browser-extension autofill for applications you fill in yourself.
- More languages and regions beyond the India and US presets.

## Docs

[User guide](docs/USER_GUIDE.md) · [Architecture](docs/ARCHITECTURE.md) · [AI models](docs/AI_MODELS.md) ·
[Free AI with Ollama](docs/OLLAMA.md) ·
[Self-hosting](docs/SELF_HOSTING.md) · [Deploying the demo](docs/DEPLOY.md) · [Testing](docs/TESTING.md) ·
[Security and responsible use](docs/SECURITY.md) · [The plan](docs/HIREFLOW_PLAN.md)

## License

[MIT](LICENSE)
