"""Build the PitchSense package for this operating system: ``python packaging/build.py``.

1. Rebuild the database and the prediction log from ``data/raw``; both ship inside the package.
2. Run PyInstaller with ``packaging/pitchsense.spec``.
3. Pack the result in ``dist/``: a ``.dmg`` disk image on macOS, a ``.zip`` folder on Windows.

PyInstaller does not cross-compile: build the macOS package on macOS and the Windows package on
Windows. The packages are not signed, so each system warns the first time they are opened.
"""

import platform
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
NAME = "PitchSense"


def run(*command: str) -> None:
    print("$", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def version() -> str:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    return project["version"]


def disk_image(application: Path, target: Path) -> Path:
    """A compressed macOS disk image with the application and a link to Applications."""
    with tempfile.TemporaryDirectory() as folder:
        staging = Path(folder)
        shutil.copytree(application, staging / application.name, symlinks=True)
        (staging / "Applications").symlink_to("/Applications")
        target.unlink(missing_ok=True)
        run("hdiutil", "create", "-volname", NAME, "-srcfolder", str(staging), "-ov",
            "-format", "UDZO", str(target))  # fmt: skip
    return target


def main() -> int:
    python = sys.executable
    run(python, "-m", "app.data.build_database")
    run(python, "-m", "app.evaluation.backtesting")
    run(python, "-m", "PyInstaller", "--noconfirm", "--clean", "--distpath", str(DIST),
        "--workpath", str(BUILD), str(ROOT / "packaging" / "pitchsense.spec"))  # fmt: skip

    stem = f"{NAME}-{version()}-{{system}}-{platform.machine().lower()}"
    if sys.platform == "darwin":
        package = disk_image(DIST / f"{NAME}.app", DIST / (stem.format(system="macOS") + ".dmg"))
    elif sys.platform == "win32":
        base = DIST / stem.format(system="Windows")
        package = Path(shutil.make_archive(str(base), "zip", DIST, NAME))
    else:
        print(f"Application folder: {DIST / NAME} (no archive on this system)")
        return 0
    print(f"Package: {package} ({package.stat().st_size / 1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
