# HireFlow's public demo API as one free Hugging Face Space (Docker): API + scheduler + Chromium, no Redis.
# scripts/deploy_space.py copies this file to the Space's root next to backend/, prompts/ and scripts/;
# see docs/DEPLOY.md ("Free deployment"). Same base as backend/Dockerfile.
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

# Spaces run the container as user 1000, and its disk is wiped on every restart (the demo resets anyway)
RUN mkdir -p /data/storage /data/home \
    && chmod +x /app/docker-entrypoint.sh \
    && chown -R 1000:1000 /app /data

USER 1000
EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD curl -fsS http://localhost:7860/health || exit 1
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["all-in-one"]
