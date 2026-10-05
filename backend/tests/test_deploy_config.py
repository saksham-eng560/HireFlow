"""Deployment settings (docs/DEPLOY.md): hosted providers' URLs work as they're copied from their dashboards."""

from __future__ import annotations

from typing import Any

import pytest
from celery import Celery

from app.config import Settings


@pytest.mark.parametrize("url", ["postgres://u:p@ep-x.aws.neon.tech/hireflow?sslmode=require",
                                 "postgresql://u:p@ep-x.aws.neon.tech/hireflow?sslmode=require"])
def test_a_neon_url_opens_with_psycopg_3(url: str) -> None:
    assert Settings(DATABASE_URL=url).DATABASE_URL == "postgresql+psycopg://u:p@ep-x.aws.neon.tech/hireflow?sslmode=require"


def test_other_database_urls_are_left_alone() -> None:
    for url in ("postgresql+psycopg://u:p@db/hireflow", "sqlite:///data/hireflow.db"):
        assert Settings(DATABASE_URL=url).DATABASE_URL == url


def test_an_upstash_tls_url_works_for_celery() -> None:
    url = "rediss://default:secret@eu1-x.upstash.io:6379"
    settings = Settings(REDIS_URL=url)
    assert settings.celery_broker == settings.celery_backend == f"{url}?ssl_cert_reqs=required"
    with pytest.raises(ValueError, match="ssl_cert_reqs"):  # what Celery does with the URL as copied
        _ = Celery("raw", broker=url, backend=url).backend
    backend = Celery("fixed", broker=settings.celery_broker, backend=settings.celery_backend).backend
    assert backend.connparams["ssl_cert_reqs"] == 2  # ssl.CERT_REQUIRED: the certificate is verified


def test_a_tls_url_that_already_says_how_to_verify_is_kept() -> None:
    url = "rediss://x:6379/0?ssl_cert_reqs=none"
    assert Settings(REDIS_URL=url).celery_broker == url
    assert Settings(REDIS_URL="redis://localhost:6379/0").celery_broker == "redis://localhost:6379/0"


def test_sentry_reports_the_deployed_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    import sentry_sdk

    from app.config import settings
    from app.core import logging_config

    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(sentry_sdk, "init", lambda **kw: calls.append(kw))
    monkeypatch.setattr(settings, "SENTRY_DSN", "https://key@o0.ingest.sentry.io/1")
    monkeypatch.setattr(logging_config, "_configured", False)
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abc1234")
    logging_config.configure_logging()
    assert calls and calls[0]["release"] == "abc1234" and calls[0]["send_default_pii"] is False
