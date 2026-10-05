# HireFlow's public demo API in one container: the API, its scheduler and Chromium in one process, no Redis
# (the all-in-one role). It fits a 512 MB instance. Build from the repository root:
#   docker build -f deploy/Dockerfile -t hireflow-demo .
# Used by Render's free plan (render.yaml, which sets PORT) and by a Hugging Face Space (scripts/deploy_space.py
# copies it to the Space's root). See docs/DEPLOY.md, "Free deployment". Same base as backend/Dockerfile.
ARG PLAYWRIGHT_VERSION=1.56.0
FROM mcr.microsoft.com/playwright/python:v${PLAYWRIGHT_VERSION}-noble

ARG PLAYWRIGHT_VERSION
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PROMPTS_DIR=/app/prompts \
    HOME=/data/home \
    PORT=7860 \
    ENVIRONMENT=production \
    DEMO_MODE=true \
    COOKIE_SECURE=true \
    DATABASE_URL=sqlite:////data/hireflow.db \
    STORAGE_BACKEND=local \
    LOCAL_STORAGE_PATH=/data/storage

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install -r requirements.txt "playwright==${PLAYWRIGHT_VERSION}"

COPY backend/ /app/
COPY prompts/ /app/prompts/
COPY scripts/ /app/scripts/

# Runs as user 1000 (what Hugging Face Spaces require); the disk is wiped on every restart (the demo resets anyway)
RUN mkdir -p /data/storage /data/home \
    && chmod +x /app/docker-entrypoint.sh \
    && chown -R 1000:1000 /app /data

USER 1000
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD curl -fsS http://localhost:7860/health || exit 1
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["all-in-one"]
