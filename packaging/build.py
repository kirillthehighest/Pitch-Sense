"""Build the PitchSense package for this operating system: ``python packaging/build.py``.

1. Rebuild the database and the prediction log of every league from ``data/raw``, and download
   the season in progress (``data/live``); they ship inside the package, which copies the season
   in progress to the user's folder, where the window can update it.
2. Draw the app icon files from the logo (``packaging/icons.py``).
3. Run PyInstaller with ``packaging/pitchsense.spec``.
4. Pack the result in ``dist/``: a ``.dmg`` disk image on macOS, a ``.zip`` folder on Windows.

PyInstaller does not cross-compile: build the macOS package on macOS and the Windows package on
Windows. The packages are not signed, so each system warns the first time they are opened.
"""

import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import __version__  # noqa: E402

DIST = ROOT / "dist"
BUILD = ROOT / "build"
NAME = "PitchSense"


def run(*command: str) -> None:
    print("$", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


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
    run(python, "-m", "app.data.update")
    run(python, str(ROOT / "packaging" / "icons.py"), str(BUILD / "icons"))
    run(python, "-m", "PyInstaller", "--noconfirm", "--clean", "--distpath", str(DIST),
        "--workpath", str(BUILD), str(ROOT / "packaging" / "pitchsense.spec"))  # fmt: skip

    stem = f"{NAME}-{__version__}-{{system}}-{platform.machine().lower()}"
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
