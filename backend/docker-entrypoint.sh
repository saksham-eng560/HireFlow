#!/bin/sh
# Role-based entrypoint: api | worker | beat | worker-beat | all-in-one | migrate | seed | <any command>
set -e

case "$1" in
  api)
    python scripts/migrate.py
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" \
      --workers "${API_WORKERS:-2}" --proxy-headers --forwarded-allow-ips="*"
    ;;
  worker)
    exec celery -A app.worker.celery_app worker -Q default,browser \
      --concurrency "${WORKER_CONCURRENCY:-2}" --max-tasks-per-child 50 --loglevel "${LOG_LEVEL:-INFO}"
    ;;
  beat)
    exec celery -A app.worker.celery_app beat --loglevel "${LOG_LEVEL:-INFO}" -s /data/celerybeat-schedule
    ;;
  worker-beat)
    # One small instance for both (the public demo, docs/DEPLOY.md). Run exactly one of these: two would
    # both schedule every scan and the nightly reset.
    exec celery -A app.worker.celery_app worker -B -Q default,browser \
      --concurrency "${WORKER_CONCURRENCY:-2}" --max-tasks-per-child 50 --loglevel "${LOG_LEVEL:-INFO}" \
      -s /data/celerybeat-schedule
    ;;
  all-in-one)
    # One container, one process, no Redis (the free deployment, docs/DEPLOY.md): the API runs its tasks in
    # background threads and the periodic jobs in a scheduler thread, so it fits a 512 MB free instance.
    # Without SECRET_KEY / ENCRYPTION_KEY set, it makes its own on first start-up and keeps them in /data
    # (fine for the demo's throwaway SQLite database; set both as secrets when DATABASE_URL is external).
    # On Render, PUBLIC_API_URL defaults to the service's own URL.
    export PUBLIC_API_URL="${PUBLIC_API_URL:-${RENDER_EXTERNAL_URL:-http://localhost:${PORT:-8000}}}"
    if [ -z "${SECRET_KEY:-}" ] || [ -z "${ENCRYPTION_KEY:-}" ]; then
      mkdir -p /data && touch /data/.keys && chmod 600 /data/.keys
      grep -q '^SECRET_KEY=' /data/.keys || python -c 'import secrets; print("SECRET_KEY=" + secrets.token_urlsafe(48))' >> /data/.keys
      grep -q '^ENCRYPTION_KEY=' /data/.keys \
        || python -c 'import base64, os; print("ENCRYPTION_KEY=" + base64.urlsafe_b64encode(os.urandom(32)).decode())' >> /data/.keys
      [ -n "${SECRET_KEY:-}" ] || SECRET_KEY="$(sed -n 's/^SECRET_KEY=//p' /data/.keys)"
      [ -n "${ENCRYPTION_KEY:-}" ] || ENCRYPTION_KEY="$(sed -n 's/^ENCRYPTION_KEY=//p' /data/.keys)"
      export SECRET_KEY ENCRYPTION_KEY
    fi
    export REDIS_URL="" CELERY_TASK_ALWAYS_EAGER=true RUN_SCHEDULER_IN_API=true
    python scripts/migrate.py
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" \
      --workers 1 --proxy-headers --forwarded-allow-ips="*"
    ;;
  migrate)
    exec python scripts/migrate.py
    ;;
  seed)
    shift
    exec python scripts/seed_db.py "$@"
    ;;
  *)
    exec "$@"
    ;;
esac
