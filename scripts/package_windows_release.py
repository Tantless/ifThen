from __future__ import annotations

import json
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DESKTOP_DIR = REPO_ROOT / "desktop"
PACKAGE_JSON = DESKTOP_DIR / "package.json"
WIN_UNPACKED_DIR = DESKTOP_DIR / "release" / "win-unpacked"


def load_package_metadata() -> tuple[str, str]:
    payload = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    version = str(payload.get("version", "0.0.0")).strip() or "0.0.0"
    product_name = str(payload.get("productName") or "If Then").strip() or "If Then"
    return product_name, version


def main() -> None:
    if not WIN_UNPACKED_DIR.exists():
        raise SystemExit(f"Missing staged app directory: {WIN_UNPACKED_DIR}")

    product_name, version = load_package_metadata()
    archive_base = DESKTOP_DIR / "release" / f"{product_name}-{version}-x64"
    archive_path = Path(f"{archive_base}.zip")

    if archive_path.exists():
        archive_path.unlink()

    shutil.make_archive(
        base_name=str(archive_base),
        format="zip",
        root_dir=str(WIN_UNPACKED_DIR.parent),
        base_dir=WIN_UNPACKED_DIR.name,
    )

    print(f"Packaged Windows release: {archive_path}")


if __name__ == "__main__":
    main()
