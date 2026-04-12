from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DESKTOP_DIR = REPO_ROOT / "desktop"
STAGING_ROOT = DESKTOP_DIR / ".release"
BACKEND_DIST_ROOT = STAGING_ROOT / "backend"
PYINSTALLER_WORK_ROOT = STAGING_ROOT / "pyinstaller-work"
PYINSTALLER_SPEC_ROOT = STAGING_ROOT / "pyinstaller-spec"
PROJECT_SRC = REPO_ROOT / "src"

PYINSTALLER_PACKAGES = (
    "fastapi",
    "starlette",
    "pydantic",
    "sqlalchemy",
    "uvicorn",
    "httpx",
)

SERVICES = (
    {
        "kind": "api",
        "entrypoint": REPO_ROOT / "scripts" / "run_api.py",
        "executable": "if-then-api",
    },
    {
        "kind": "worker",
        "entrypoint": REPO_ROOT / "scripts" / "run_worker.py",
        "executable": "if-then-worker",
    },
)


def reset_dir(target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)


def ensure_pyinstaller_available() -> None:
    try:
        import PyInstaller  # noqa: F401
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "PyInstaller is required for Windows release builds. "
            "Install it with `pip install -e .[release]` or `pip install pyinstaller`."
        ) from exc


def build_service(kind: str, entrypoint: Path, executable: str) -> None:
    dist_dir = BACKEND_DIST_ROOT / kind
    work_dir = PYINSTALLER_WORK_ROOT / kind
    spec_dir = PYINSTALLER_SPEC_ROOT / kind

    reset_dir(dist_dir)
    reset_dir(work_dir)
    reset_dir(spec_dir)

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        executable,
        "--distpath",
        str(dist_dir),
        "--workpath",
        str(work_dir),
        "--specpath",
        str(spec_dir),
        "--paths",
        str(PROJECT_SRC),
    ]

    for package in PYINSTALLER_PACKAGES:
        command.extend(["--collect-all", package])

    command.append(str(entrypoint))

    subprocess.run(command, cwd=REPO_ROOT, check=True)

    built_executable = dist_dir / f"{executable}.exe"
    if not built_executable.exists():
        raise RuntimeError(f"PyInstaller did not produce {built_executable}")


def main() -> None:
    ensure_pyinstaller_available()
    STAGING_ROOT.mkdir(parents=True, exist_ok=True)
    reset_dir(BACKEND_DIST_ROOT)

    for service in SERVICES:
        build_service(
            kind=str(service["kind"]),
            entrypoint=Path(service["entrypoint"]),
            executable=str(service["executable"]),
        )

    print(f"Bundled backend executables written to {BACKEND_DIST_ROOT}")


if __name__ == "__main__":
    main()
