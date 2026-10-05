"""Deployment settings (docs/DEPLOY.md): hosted providers' URLs work as they're copied from their dashboards."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest
import yaml
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
    show = _all_in_one_prelude(tmp_path) + 'echo "$SECRET_KEY|$ENCRYPTION_KEY"\n'
    env = {"PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin"}  # `python` is this interpreter
    first = subprocess.run(["sh", "-c", show], capture_output=True, text=True, check=True, env=env)
    again = subprocess.run(["sh", "-c", show], capture_output=True, text=True, check=True, env=env)
    secret, key = first.stdout.strip().split("|")
    assert len(secret) >= 32 and len(key) == 44 and first.stdout == again.stdout
    assert oct((tmp_path / ".keys").stat().st_mode & 0o777) == "0o600"


def _all_in_one_prelude(tmp_path: Path) -> str:
    script = (ROOT / "backend" / "docker-entrypoint.sh").read_text()
    return script.split("  all-in-one)\n", 1)[1].split("    export REDIS_URL", 1)[0].replace("/data", str(tmp_path))


def test_on_render_the_api_knows_its_own_url(tmp_path: Path) -> None:
    """Render tells a service its URL (RENDER_EXTERNAL_URL); the demo careers site and links are built from it."""
    show = _all_in_one_prelude(tmp_path) + 'echo "$PUBLIC_API_URL"\n'
    env = {"PATH": f"{Path(sys.executable).parent}:/usr/bin:/bin"}
    out = subprocess.run(["sh", "-c", show], capture_output=True, text=True, check=True,
                         env={**env, "RENDER_EXTERNAL_URL": "https://hireflow-api.onrender.com"})
    assert out.stdout.strip() == "https://hireflow-api.onrender.com"
    out = subprocess.run(["sh", "-c", show], capture_output=True, text=True, check=True,
                         env={**env, "RENDER_EXTERNAL_URL": "https://x.onrender.com", "PUBLIC_API_URL": "https://api.example"})
    assert out.stdout.strip() == "https://api.example"  # an explicit setting wins


def test_the_free_render_blueprint_deploys_in_one_click() -> None:
    blueprint = yaml.safe_load((ROOT / "render.yaml").read_text())
    (service,) = blueprint["services"]
    assert service["plan"] == "free" and service["runtime"] == "docker" and service["healthCheckPath"] == "/health"
    assert (ROOT / service["dockerfilePath"]).is_file() and "all-in-one" in (ROOT / service["dockerfilePath"]).read_text()
    env = {e["key"]: e for e in service["envVars"]}
    assert env["FRONTEND_URL"]["value"] == env["CORS_ORIGINS"]["value"] == "https://hireflow-three-woad.vercel.app"
    assert env["SECRET_KEY"].get("generateValue") and env["ENCRYPTION_KEY"].get("generateValue")
    assert not [k for k, e in env.items() if e.get("sync") is False], "a value to type in would break the one-click deploy"
    paid = yaml.safe_load((ROOT / "deploy" / "render-always-on.yaml").read_text())
    assert all((ROOT / s["dockerfilePath"]).is_file() for s in paid["services"])


def test_the_scheduler_can_run_inside_the_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """RUN_SCHEDULER_IN_API: the periodic jobs run in a thread of the API process, and one failing job stops nothing."""
    from app.worker import dispatch, local_scheduler

    ran: list[str] = []

    def boom() -> None:
        ran.append("boom")
        raise RuntimeError("a job failed")

    monkeypatch.setattr(local_scheduler, "SCHEDULE", [("boom", 3600, True), ("ok", 3600, True)])
    monkeypatch.setattr(local_scheduler, "FIRST_RUN_DELAY", 0.0)
    monkeypatch.setattr(local_scheduler, "TICK", 0.05)
    monkeypatch.setattr(dispatch, "_load_registry", lambda: None)
    monkeypatch.setitem(dispatch._registry, "boom", boom)
    monkeypatch.setitem(dispatch._registry, "ok", lambda: ran.append("ok"))
    stop = local_scheduler.start_in_background()
    deadline = time.monotonic() + 5
    while len(ran) < 2 and time.monotonic() < deadline:
        time.sleep(0.02)
    stop.set()
    assert ran == ["boom", "ok"]
    deadline = time.monotonic() + 2
    while any(t.name == "local-scheduler" for t in threading.enumerate()) and time.monotonic() < deadline:
        time.sleep(0.02)
    assert not any(t.name == "local-scheduler" for t in threading.enumerate())


def test_the_api_starts_and_stops_its_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    from fastapi.testclient import TestClient

    from app.config import settings
    from app.main import app
    from app.worker import local_scheduler

    events: list[threading.Event] = []
    monkeypatch.setattr(settings, "RUN_SCHEDULER_IN_API", True)
    monkeypatch.setattr(local_scheduler, "start_in_background", lambda: events.append(threading.Event()) or events[-1])
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert len(events) == 1 and not events[0].is_set()
    assert events[0].is_set()


def test_readiness_says_redis_is_not_used_rather_than_down(client: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "REDIS_URL", "")
    checks = client.get("/health/ready").json()["checks"]
    assert checks["redis"] == "not used (in-process tasks)"
