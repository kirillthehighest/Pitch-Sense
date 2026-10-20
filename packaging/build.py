"""Build the PitchSense package for this operating system: ``python packaging/build.py``.

1. Rebuild the database and the prediction log of every league from ``data/raw``, download the
   season in progress (``data/live``) and compute every league's predictions for these data
   (``data/cache``, ``app/services/prediction_cache.py``); they ship inside the package, which
   copies the season in progress to the user's folder, where the application can update it, and
   starts with the shipped predictions instead of computing them.
2. Run PyInstaller with ``packaging/server.spec``: the local server, ``dist/pitchsense-server``.
3. Build the window (Tauri, ``web/src-tauri``) with the web interface and the server as a
   resource, the version of ``app/__init__.py`` and, on macOS, the app and its ``.dmg``; on
   Windows an installer (NSIS). Both land in ``dist/``.

Neither PyInstaller nor Tauri cross-compiles: build the macOS package on macOS and the Windows
package on Windows. The packages have no developer certificate, so each system warns the first
time they are opened. On macOS the app is signed ad hoc as a whole and its signature checked:
Tauri signs only the main program, and macOS calls such an app, once downloaded, "damaged" and
offers no way to open it. The window needs Node (``web/package.json``) and Rust
(``web/src-tauri/Cargo.toml``).
"""

import argparse
import json
import os
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
WEB = ROOT / "web"
BUNDLES = WEB / "src-tauri" / "target" / "release" / "bundle"
NAME = "PitchSense"
SERVER = "pitchsense-server"


def run(*command: str, cwd: Path = ROOT) -> None:
    print("$", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def tool(name: str) -> str:
    """A Node tool by its name on this system (npm.cmd on Windows)."""
    return f"{name}.cmd" if sys.platform == "win32" else name


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


def package_name(system: str, suffix: str) -> Path:
    return DIST / f"{NAME}-{__version__}-{system}-{platform.machine().lower()}{suffix}"


def build_data() -> None:
    python = sys.executable
    run(python, "-m", "app.data.build_database")
    run(python, "-m", "app.evaluation.backtesting")
    run(python, "-m", "app.data.update")
    shutil.rmtree(ROOT / "data" / "cache", ignore_errors=True)  # only these data's predictions
    run(python, "-m", "app.services.prediction_cache")


def sign_ad_hoc(application: Path) -> None:
    """Seal the whole app with an ad-hoc signature and check it (macOS)."""
    run("codesign", "--force", "--deep", "--sign", "-", str(application))
    run("codesign", "--verify", "--deep", "--strict", "--verbose=2", str(application))


def tauri_config() -> Path:
    """The package's additions to web/src-tauri/tauri.conf.json: the version of the code and
    the server as a resource, in the folder the window looks in (server/)."""
    config = {
        "version": __version__,
        "bundle": {"resources": {str(DIST / SERVER) + os.sep: "server/"}},
    }
    path = BUILD / "tauri.package.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return path


def build_web() -> Path:
    run(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--distpath", str(DIST),
        "--workpath", str(BUILD / "server"), str(ROOT / "packaging" / "server.spec"))  # fmt: skip
    run(tool("npm"), "ci", cwd=WEB)
    bundles = "app" if sys.platform == "darwin" else "nsis"
    run(tool("npx"), "tauri", "build", "--config", str(tauri_config()), "--bundles", bundles,
        cwd=WEB)  # fmt: skip
    if sys.platform == "darwin":
        shutil.rmtree(DIST / f"{NAME}.app", ignore_errors=True)
        shutil.copytree(BUNDLES / "macos" / f"{NAME}.app", DIST / f"{NAME}.app", symlinks=True)
        sign_ad_hoc(DIST / f"{NAME}.app")
        return disk_image(DIST / f"{NAME}.app", package_name("macOS", ".dmg"))
    if sys.platform == "win32":
        installer = next((BUNDLES / "nsis").glob("*.exe"))
        target = package_name("Windows", "-setup.exe")
        shutil.copyfile(installer, target)
        return target
    raise SystemExit("The window is packaged on macOS and Windows only.")


def main(arguments: list[str]) -> int:
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args(arguments)
    build_data()
    package = build_web()
    print(f"Package: {package} ({package.stat().st_size / 1e6:.0f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
