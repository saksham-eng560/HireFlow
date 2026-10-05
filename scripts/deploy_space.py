#!/usr/bin/env python3
"""Deploy the demo API to a free Hugging Face Space (docs/DEPLOY.md, "Free deployment").

    HF_TOKEN=... python scripts/deploy_space.py --frontend-url https://<dashboard>.vercel.app [--space you/hireflow]

Creates the Space (Docker) if needed, points it at the dashboard, uploads backend/, prompts/, scripts/ and
deploy/huggingface/ (its Dockerfile and card), then waits until it's running and its /health/ready answers.
`.github/workflows/deploy-space.yml` runs this after CI passes on main. Needs `huggingface_hub`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SPACE_FILES = Path("deploy/huggingface")
SOURCES = ("backend", "prompts", "scripts")
# Never uploaded: local state, caches, tests and anything that could hold a secret
IGNORE = shutil.ignore_patterns(
    ".venv", "venv", "__pycache__", "*.pyc", ".pytest_cache", ".ruff_cache", ".mypy_cache", "htmlcov", ".coverage*",
    "data", "storage", "demo-storage", "tests", ".env", ".env.*", "*.db", "*.db-*", "*.sqlite*", "celerybeat-schedule*",
)


def space_host(space_id: str) -> str:
    """The Space's own URL, e.g. ``Some_User/HireFlow`` -> ``https://some-user-hireflow.hf.space``."""
    owner, _, name = space_id.partition("/")
    slug = re.sub(r"[^a-z0-9]+", "-", f"{owner}-{name}".lower()).strip("-")
    return f"https://{slug}.hf.space"


def build_bundle(dest: Path) -> list[str]:
    """Lay the Space's files out in ``dest``: Dockerfile and README.md at the root, the sources beside them."""
    for name in SOURCES:
        shutil.copytree(ROOT / name, dest / name, ignore=IGNORE)
    for item in (ROOT / SPACE_FILES).iterdir():
        shutil.copy2(item, dest / item.name)
    return sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file())


def space_variables(frontend_url: str, api_url: str) -> dict[str, str]:
    """Non-secret settings the Space needs to know where it lives (secrets are made in the container)."""
    frontend_url = frontend_url.rstrip("/")
    return {
        "FRONTEND_URL": frontend_url,
        "CORS_ORIGINS": frontend_url,
        "PUBLIC_API_URL": api_url,
    }


def wait_until_ready(api: Any, space_id: str, url: str, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    stage = ""
    while time.monotonic() < deadline:
        runtime = api.get_space_runtime(space_id)
        if runtime.stage != stage:
            stage = runtime.stage
            print(f"  Space: {stage}", flush=True)
        if stage in {"BUILD_ERROR", "RUNTIME_ERROR", "CONFIG_ERROR", "NO_APP_FILE"}:
            return False
        if stage == "RUNNING":
            try:
                with urllib.request.urlopen(f"{url}/health/ready", timeout=20) as response:
                    checks = json.loads(response.read()).get("checks", {})
                print(f"  /health/ready: {checks}")
                return True
            except (urllib.error.URLError, TimeoutError, ValueError):
                pass  # running, but the API is still migrating or starting
        time.sleep(15)
    print("  timed out waiting for the Space", file=sys.stderr)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--frontend-url", default="", help="the dashboard's public URL (Vercel); required to deploy")
    parser.add_argument("--space", default="", help="owner/name (default: <your Hugging Face user>/hireflow)")
    parser.add_argument("--timeout", type=float, default=1800, help="seconds to wait for the build (default 1800)")
    parser.add_argument("--dry-run", action="store_true", help="only list the files that would be uploaded")
    parser.add_argument("--bundle-dir", type=Path, help="only lay the Space's files out here (CI builds the image from it)")
    args = parser.parse_args()

    if args.bundle_dir:
        args.bundle_dir.mkdir(parents=True, exist_ok=False)
        print(f"{len(build_bundle(args.bundle_dir))} files in {args.bundle_dir}")
        return 0

    if args.dry_run:
        with tempfile.TemporaryDirectory() as tmp:
            files = build_bundle(Path(tmp))
        print("\n".join(files))
        print(f"{len(files)} files")
        return 0

    if not args.frontend_url:
        parser.error("--frontend-url is required to deploy")
    from huggingface_hub import HfApi

    token = os.environ.get("HF_TOKEN", "")
    if not token:
        print("HF_TOKEN is not set: create a write token at https://huggingface.co/settings/tokens", file=sys.stderr)
        return 2
    api = HfApi(token=token)
    space_id = args.space or f"{api.whoami()['name']}/hireflow"
    url = space_host(space_id)
    print(f"Space {space_id} -> {url}")

    api.create_repo(space_id, repo_type="space", space_sdk="docker", exist_ok=True)
    for key, value in space_variables(args.frontend_url, url).items():
        api.add_space_variable(space_id, key, value)
    with tempfile.TemporaryDirectory() as tmp:
        files = build_bundle(Path(tmp))
        print(f"Uploading {len(files)} files…")
        api.upload_folder(
            repo_id=space_id, repo_type="space", folder_path=tmp,
            delete_patterns=[f"{name}/*" for name in SOURCES],  # files removed from the repo go from the Space too
            commit_message=f"Deploy {os.environ.get('GITHUB_SHA', 'local')[:12]}",
        )
    ok = wait_until_ready(api, space_id, url, args.timeout)
    print(f"API {'is up' if ok else 'did not start'}: {url}  (logs: https://huggingface.co/spaces/{space_id}?logs=container)")
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as out:
            out.write(f"api_url={url}\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
