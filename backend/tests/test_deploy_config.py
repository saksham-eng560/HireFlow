"""Deployment settings (docs/DEPLOY.md): hosted providers' URLs work as they're copied from their dashboards."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from celery import Celery

from app.config import Settings

ROOT = Path(__file__).resolve().parents[2]


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


def _deploy_space() -> Any:
    spec = importlib.util.spec_from_file_location("deploy_space", ROOT / "scripts" / "deploy_space.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_free_space_gets_its_own_url_and_points_at_the_dashboard() -> None:
    ds = _deploy_space()
    assert ds.space_host("saksham-eng560/hireflow") == "https://saksham-eng560-hireflow.hf.space"
    assert ds.space_host("Some_User/Hire.Flow") == "https://some-user-hire-flow.hf.space"
    assert ds.space_variables("https://hireflow-three-woad.vercel.app/", "https://x-hireflow.hf.space") == {
        "FRONTEND_URL": "https://hireflow-three-woad.vercel.app",
        "CORS_ORIGINS": "https://hireflow-three-woad.vercel.app",
        "PUBLIC_API_URL": "https://x-hireflow.hf.space",
    }


def test_the_space_upload_holds_the_app_and_nothing_private(tmp_path: Path) -> None:
    files = _deploy_space().build_bundle(tmp_path)
    assert {"Dockerfile", "README.md", "backend/docker-entrypoint.sh", "backend/app/main.py",
            "scripts/migrate.py", "scripts/local_scheduler.py"} <= set(files)
    assert any(f.startswith("prompts/") for f in files)
    private = [f for f in files if f.startswith(("backend/tests/", "backend/.venv/", "backend/data/"))
               or "/.env" in f or f.endswith((".db", ".pyc"))]
    assert private == []
    card = (tmp_path / "README.md").read_text()
    assert "sdk: docker" in card and "app_port: 7860" in card
    assert "CMD [\"all-in-one\"]" in (tmp_path / "Dockerfile").read_text()


def test_the_all_in_one_container_makes_and_keeps_its_own_keys(tmp_path: Path) -> None:
    """Without SECRET_KEY / ENCRYPTION_KEY the container makes them once and reuses them after a restart."""
    script = (ROOT / "backend" / "docker-entrypoint.sh").read_text()
    block = script.split("  all-in-one)\n", 1)[1].split("    export REDIS_URL", 1)[0].replace("/data", str(tmp_path))
    show = block + 'echo "$SECRET_KEY|$ENCRYPTION_KEY"\n'
    env = {"PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin"}  # `python` is this interpreter
    first = subprocess.run(["sh", "-c", show], capture_output=True, text=True, check=True, env=env)
    again = subprocess.run(["sh", "-c", show], capture_output=True, text=True, check=True, env=env)
    secret, key = first.stdout.strip().split("|")
    assert len(secret) >= 32 and len(key) == 44 and first.stdout == again.stdout
    assert oct((tmp_path / ".keys").stat().st_mode & 0o777) == "0o600"


def test_readiness_says_redis_is_not_used_rather_than_down(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "REDIS_URL", "")
    checks = client.get("/health/ready").json()["checks"]
    assert checks["redis"] == "not used (in-process tasks)"
