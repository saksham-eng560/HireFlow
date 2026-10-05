# Deploying the public demo

A live, always-safe demo on free or cheap tiers: visitors press **Try the demo** (or sign up), swipe through
internships at fictional companies and watch forms get filled on the bundled demo careers site. Nothing reaches a
real employer, real sign-ins are off, and everything resets every night. To run HireFlow for yourself instead, see
[SELF_HOSTING.md](SELF_HOSTING.md).

There are two ways to host it:

- **[Free](#free-deployment-vercel--render)**: the dashboard on Vercel and the API on Render's free plan, $0 a
  month and no card, set up in about five minutes. This is the one running at https://hireflow-three-woad.vercel.app.
- **[Always on](#always-on-deployment-render-neon-upstash-r2)**: Render, Neon, Upstash and Cloudflare R2, on paid
  instances (see [costs](#costs-and-limits)), with no cold starts and a database that survives restarts.

## Free deployment: Vercel + Render

| Part | Service (free plan) | What you get |
|---|---|---|
| Dashboard | Vercel Hobby | Global CDN, a deploy on every push to `main` |
| API, scheduler and Chromium | Render free web service (Docker) | 512 MB of memory, a tenth of a CPU; sleeps when idle |
| Database, queue, files | Inside the container | SQLite, in-process tasks, local disk; no Redis needed |

The API runs as one container, one process ([`deploy/Dockerfile`](../deploy/Dockerfile), the `all-in-one` role
of [`backend/docker-entrypoint.sh`](../backend/docker-entrypoint.sh)): the API in demo mode, with its tasks and
the scheduler in background threads (`RUN_SCHEDULER_IN_API`). That's what fits the free 512 MB: measured at about
350 MB at its peak while Chromium fills a form, and CI runs the image under a 512 MB limit on every push. It makes
its own `SECRET_KEY` and `ENCRYPTION_KEY` if none are set, and finds its own URL from Render (`RENDER_EXTERNAL_URL`).
Its disk is wiped whenever it restarts, which suits a demo that resets every night anyway: the demo account is
re-created at start-up.

### 1. The dashboard on Vercel

1. On https://vercel.com: **Add New → Project**, import this repository, set **Root Directory** to `frontend`
   and deploy. (The framework, install and build commands come from
   [`frontend/vercel.json`](../frontend/vercel.json).)
2. Note the production URL (**Settings → Domains**), e.g. `https://hireflow-three-woad.vercel.app`, and add the
   environment variables `NEXT_PUBLIC_SITE_URL` (that URL) and `NEXT_PUBLIC_DEMO_MODE` (`true`).

### 2. The API on Render

1. If your dashboard's URL isn't `https://hireflow-three-woad.vercel.app`, change `FRONTEND_URL` and
   `CORS_ORIGINS` in [`render.yaml`](../render.yaml) first.
2. Open **https://render.com/deploy?repo=https://github.com/saksham-eng560/HireFlow** (for a fork, use its URL),
   sign in with GitHub (no card needed) and press **Deploy Blueprint**. Render reads [`render.yaml`](../render.yaml)
   and creates `hireflow-api` on the free plan.
3. The first build takes about 10 minutes. Then the service's page shows its URL, e.g.
   `https://hireflow-api.onrender.com` (Render adds a suffix if the name is taken); `/health/ready` there must
   answer `"database": "ok"`. Every push to `main` redeploys it.

### 3. Connect them

On Vercel, add the environment variables below, then **Deployments → ⋯ → Redeploy** (they're read at build
time):

| Variable | Value |
|---|---|
| `BACKEND_URL` | the Render URL, e.g. `https://hireflow-api.onrender.com` |
| `NEXT_PUBLIC_WS_URL` | `wss://<render host>/api/v1/ws` (live updates; without it the dashboard polls) |

Open the dashboard and press **Try the demo**. To check everything at once:
`python3 scripts/smoke_test.py --site https://<dashboard> --api https://<render host> --demo --timeout 120`.

### Good to know

- **Sleeping.** The free plan sleeps after 15 minutes without visitors. The next visitor wakes it, which takes
  about a minute: meanwhile the dashboard says "Can't reach the HireFlow server right now… try again in a
  minute", and "Try the demo" works once it's up.
- **Slow form filling.** A tenth of a CPU is enough for the dashboard and the deck, but filling a form in
  Chromium takes a minute or two instead of seconds.
- **Restarts reset the data.** Accounts made by visitors last until the next restart or nightly reset. For a
  database that survives, set `DATABASE_URL` to a free Neon database (Render: the service → **Environment**),
  together with fixed `SECRET_KEY` and `ENCRYPTION_KEY`.
- **AI.** Without a key the demo runs on built-in heuristics; no AI model fits in 512 MB. To use Claude, add
  `ANTHROPIC_API_KEY` in **Environment** (each visitor's daily AI calls are capped by
  `DEMO_LLM_CALLS_PER_USER_PER_DAY`); for a free AI model see [Ollama Cloud](OLLAMA.md#the-deployed-demo).
- **Logs.** Render: the service → **Logs**; the dashboard's in Vercel → **Logs**.

### On a Hugging Face Space

The same container runs on a Hugging Face Space (2 vCPUs, 16 GB of memory, sleeps only after 48 hours without
visitors), but Hugging Face hosts Docker Spaces only with a PRO subscription. With one: save a **Write** token as
the repository secret `HF_TOKEN`, then **Actions → Deploy API (Hugging Face Space) → Run workflow**. It creates
the Space `<your-user>/hireflow`, points it at the dashboard, uploads the API, waits until it answers and runs the
smoke test; its URL is `https://<your-user>-hireflow.hf.space`, for `BACKEND_URL` as above.
[`scripts/deploy_space.py`](../scripts/deploy_space.py) does the work and can also run from your computer:
`HF_TOKEN=... python scripts/deploy_space.py --frontend-url https://<dashboard>` (`--dry-run` lists what it
uploads: the app, prompts and scripts; never tests, local databases or `.env`).

## Always-on deployment: Render, Neon, Upstash, R2

| Part | Service | Config in this repo |
|---|---|---|
| Dashboard | Vercel (root directory `frontend/`) | [`frontend/vercel.json`](../frontend/vercel.json) |
| API | Render web service (Docker) | [`deploy/render-always-on.yaml`](../deploy/render-always-on.yaml) |
| Celery worker + scheduler | Render background worker (one instance, `worker-beat`) | [`deploy/render-always-on.yaml`](../deploy/render-always-on.yaml) |
| PostgreSQL + pgvector | Neon | the first migration enables `vector` and `pg_trgm` |
| Redis | Upstash (TLS) | `rediss://` URLs work as copied |
| Files (resumes, form screenshots) | Cloudflare R2 (`STORAGE_BACKEND=s3`) | |
| Errors | Sentry, for the API, the worker and the dashboard | optional |
| Uptime | UptimeRobot or Better Stack, plus the daily smoke test | [`smoke.yml`](../.github/workflows/smoke.yml) |

Keep everything in one region (the configs use Singapore: Render `singapore`, Vercel `sin1`; pick Neon and
Upstash regions next to it). No secret goes into git: every key below is typed into the providers' dashboards.

### 1. Database: Neon

1. Create a project and a database named `hireflow` in the region next to Render.
2. Copy the **direct** connection string (the host without `-pooler`). It looks like
   `postgresql://<user>:<password>@<endpoint>.<region>.aws.neon.tech/hireflow?sslmode=require`; HireFlow switches
   it to its psycopg 3 driver itself. pgvector needs no setup: the first migration runs `CREATE EXTENSION vector`.

### 2. Redis: Upstash

1. Create a Redis database in the same region with TLS on.
2. Copy its `rediss://default:<password>@<host>:6379` URL. HireFlow adds the certificate check Celery requires
   (`ssl_cert_reqs=required`), so paste it as is.
3. A Celery worker polls Redis all the time, so a free plan with a small daily command allowance can run out:
   use pay-as-you-go (or a fixed plan) for an always-on demo.

### 3. File storage: Cloudflare R2

1. Create a private bucket, e.g. `hireflow-demo`.
2. Create an R2 API token with **Object Read & Write** on that bucket. Note its access key ID and secret.
3. The endpoint is `https://<account-id>.r2.cloudflarestorage.com`.

### 4. Errors: Sentry (optional)

Create two projects, one **Python (FastAPI)** for the API and worker and one **Next.js** for the dashboard, and
copy each DSN. HireFlow sends no personal data: the API scrubs its events, and the dashboard turns off user info,
cookies, headers, bodies and query strings. Without a DSN nothing is sent, and the browser SDK isn't even
downloaded.

### 5. API and worker: Render

1. **New → Blueprint**, pick this repository and set **Blueprint path** to `deploy/render-always-on.yaml`.
   Render reads [it](../deploy/render-always-on.yaml) and creates
   `hireflow-api` (web, `starter`) and `hireflow-worker` (background worker, `standard`: Chromium needs 1–2 GB).
   `SECRET_KEY` and `ENCRYPTION_KEY` are generated once and shared by both.
2. Fill in the values it asks for, on both services (table below). For the first deploy, set `PUBLIC_API_URL` to
   the API's future URL (`https://hireflow-api.onrender.com`, or what Render shows) and use a placeholder for
   `FRONTEND_URL` / `CORS_ORIGINS` until step 6.
3. Deploy. On every deploy the database is migrated (the pre-deploy command, and again when the API starts; a
   Postgres advisory lock keeps two from running at once). With `DEMO_MODE=true` the API creates the shared demo
   account when it starts, and the worker's scheduler wipes everything and re-creates it every night at 03:37 UTC.
   To do either by hand, open a shell on the API: `python scripts/seed_demo.py` (or `--reset`).
4. Check `https://<api>/health/ready`: the database must be `ok` and Redis `ok`.

With `autoDeployTrigger: checksPass`, Render deploys `main` only once CI is green.

### 6. Dashboard: Vercel

1. **New Project** → import this repository → **Root Directory** `frontend`. The framework, install and build
   commands come from [`frontend/vercel.json`](../frontend/vercel.json).
2. Set the environment variables (table below). `BACKEND_URL`, `NEXT_PUBLIC_*` and the Sentry build settings are
   read **at build time**: redeploy after changing them.
3. Deploy, then copy the dashboard's URL into Render's `FRONTEND_URL` and `CORS_ORIGINS` (both services) and
   redeploy the API. The dashboard proxies `/api/v1/*` to the API, so the session cookie is first-party; the
   API accepts cookie-authenticated changes only from these origins.
4. Optional: [`deploy-frontend.yml`](../.github/workflows/deploy-frontend.yml) deploys from GitHub Actions after CI
   passes instead of Vercel's own Git integration (repository variables `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` and
   the secret `VERCEL_TOKEN`).

### 7. Smoke test and uptime

```bash
python3 scripts/smoke_test.py --site https://<dashboard> --api https://<api> --demo
```

It visits the deployment like a visitor: the home page, SEO files and social image, the `/api` proxy, the API's
health (database, Redis, HSTS), then **Try the demo**, the deck, dry run, the demo careers site, and that real
actions such as password changes are refused. Every check prints a line and a failure exits with 1. The e2e
suite runs the same script on every push.

To run it every day and after each dashboard deploy, set the repository variables `DEMO_SITE_URL` and
`DEMO_API_URL` ([`smoke.yml`](../.github/workflows/smoke.yml)). For alerts within minutes, add an uptime monitor
(UptimeRobot, Better Stack) on `https://<api>/health/ready` and on the dashboard.

### 8. Link it

Point the README's demo badge and the commented-out live-demo line at the dashboard's URL, and set
`NEXT_PUBLIC_SITE_URL` (and `NEXT_PUBLIC_DEMO_VIDEO_URL` once the walkthrough is recorded) on Vercel.

## Environment variables

### API and worker (Render)

Set on both services unless noted. The ones marked *secret* are typed into Render and never committed.

| Variable | Value | |
|---|---|---|
| `ENVIRONMENT` | `production` (from the Blueprint): refuses to start with default secrets or insecure cookies | |
| `DEMO_MODE` | `true` (from the Blueprint) | |
| `COOKIE_SECURE` | `true` (from the Blueprint) | |
| `SECRET_KEY` | generated by Render | *secret* |
| `ENCRYPTION_KEY` | generated by Render (encrypts tokens and sessions at rest) | *secret* |
| `DATABASE_URL` | Neon's direct connection string | *secret* |
| `REDIS_URL` | Upstash's `rediss://` URL | *secret* |
| `STORAGE_BACKEND` | `s3` (from the Blueprint) | |
| `S3_BUCKET`, `S3_ENDPOINT_URL` | the R2 bucket and `https://<account-id>.r2.cloudflarestorage.com` | |
| `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | the R2 API token | *secret* |
| `S3_REGION` | `auto` (from the Blueprint) | |
| `PUBLIC_API_URL` | the API's URL; the worker's browser opens the demo careers site at `<this>/api/v1/demo-careers` | |
| `FRONTEND_URL` | the dashboard's URL | |
| `CORS_ORIGINS` | the dashboard's URL, plus any custom domain, comma-separated (API only) | |
| `SENTRY_DSN` | the Python project's DSN (optional) | |
| `SENTRY_TRACES_SAMPLE_RATE`, `SENTRY_RELEASE` | optional; the release defaults to the deployed commit | |
| `ANTHROPIC_API_KEY` | optional: without an AI key the demo runs on built-in heuristics | *secret* |
| `DEMO_ANTHROPIC_MODEL` | optional: a cheaper model used only in the demo | |
| `DEMO_LLM_CALLS_PER_USER_PER_DAY` | AI calls each visitor gets per day (default 40) | |
| `API_WORKERS`, `WORKER_CONCURRENCY`, `DB_POOL_SIZE` | sized for small instances by the Blueprint | |
| `DEMO_ACCOUNT_EMAIL` | the shared account (default `demo@hireflow.app`) | |
| `DEMO_SITE_URL` | only if the worker can't reach the demo site at `PUBLIC_API_URL` | |

Everything else (Google, SMTP, proxies, CAPTCHA solvers) stays unset: the demo turns those features off.

### Dashboard (Vercel)

| Variable | Value | |
|---|---|---|
| `BACKEND_URL` | the API's URL (`/api/v1/*` is proxied there) | build time |
| `NEXT_PUBLIC_WS_URL` | `wss://<api host>/api/v1/ws` (live updates; Vercel doesn't proxy WebSockets) | build time |
| `NEXT_PUBLIC_SITE_URL` | the dashboard's public URL (canonical links, sitemap, social previews) | build time |
| `NEXT_PUBLIC_DEMO_MODE` | `true`: "Try the demo" shows before the API answers (and while it's waking up) | build time |
| `NEXT_PUBLIC_GITHUB_URL`, `NEXT_PUBLIC_AUTHOR_NAME`, `NEXT_PUBLIC_AUTHOR_URL` | the landing page's links (optional) | build time |
| `NEXT_PUBLIC_DEMO_VIDEO_URL` | the walkthrough: a YouTube or Loom link or an `.mp4` (optional) | build time |
| `NEXT_PUBLIC_SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_ENVIRONMENT` | the Next.js project's DSN (optional) | build time |
| `SENTRY_DSN` | for the dashboard's server-side errors (defaults to the public DSN) | |
| `SENTRY_AUTH_TOKEN`, `SENTRY_ORG`, `SENTRY_PROJECT` | only to upload source maps at build time | *secret* token |

### GitHub (repository settings)

| Name | Kind | Used by |
|---|---|---|
| `DEMO_SITE_URL`, `DEMO_API_URL` | variables | the daily smoke test |
| `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` / `VERCEL_TOKEN` | variables / secret | deploying the dashboard from Actions (optional) |

## Costs and limits

Free tiers cover the dashboard (Vercel Hobby), the database (Neon), files (R2) and errors (Sentry). Render's free
web services sleep when idle and it has no free background workers, so an always-on demo needs the paid API and
worker instances in `deploy/render-always-on.yaml`. Redis needs a plan that allows a continuously polling worker (see step 2).
Each visitor's AI use is capped per day, and without an AI key there's no model cost at all.

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Cross-site request blocked" on sign-in | `FRONTEND_URL` / `CORS_ORIGINS` on the API don't match the dashboard's URL exactly (scheme, no trailing slash). |
| The dashboard shows "degraded" at `/api/health`, or every API call fails | `BACKEND_URL` was wrong when the dashboard was built: fix it on Vercel and redeploy. |
| No live updates | `NEXT_PUBLIC_WS_URL` must be `wss://` to the API itself, not the dashboard. |
| The worker can't fill demo forms | `PUBLIC_API_URL` must be the API's public URL (the worker's browser opens the demo careers site there). |
| The worker restarts or Chromium crashes | Give it more memory (the `standard` plan or above) and keep `WORKER_CONCURRENCY=1`. |
| The API refuses to start: "ENCRYPTION_KEY must be set", "COOKIE_SECURE must be true" | Production checks: set them (the Blueprint does) or don't use `ENVIRONMENT=production`. |
