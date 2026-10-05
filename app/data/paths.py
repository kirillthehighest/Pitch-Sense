"""Locations of the project's data files. Every data path is resolved through this module.

Run from the source code, the paths are relative to the project folder, so they work wherever
the project is cloned. In a packaged application (PyInstaller, Phase 14) the database and the
prediction log built before packaging travel inside the package, which must stay read-only;
results the application writes go to the user's application-data folder instead, and
``copy_bundled_results`` puts the shipped log there on first start.
"""

import os
import shutil
import sys
from collections.abc import Mapping, MutableMapping
from pathlib import Path

APP_NAME = "PitchSense"
PACKAGED = bool(getattr(sys, "frozen", False))  # set by PyInstaller in a packaged application


def user_data_dir(
    platform: str = sys.platform,
    environ: Mapping[str, str] = os.environ,
    home: Path | None = None,
) -> Path:
    """The folder where each operating system keeps an application's data for the user."""
    home = home or Path.home()
    if platform == "darwin":
        return home / "Library" / "Application Support" / APP_NAME
    if platform == "win32":
        base = environ.get("LOCALAPPDATA")
        return (Path(base) if base else home / "AppData" / "Local") / APP_NAME
    base = environ.get("XDG_DATA_HOME")
    return (Path(base) if base else home / ".local" / "share") / APP_NAME


PROJECT_ROOT = Path(__file__).resolve().parents[2]
# PyInstaller unpacks the files bundled with a packaged application under sys._MEIPASS.
BASE_DIR = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT)) if PACKAGED else PROJECT_ROOT
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
DATABASE_PATH = DATA_DIR / "pitchsense.db"
BUNDLED_RESULTS_DIR = DATA_DIR / "results"  # in a package: the read-only results shipped in it
# Generated evaluation outputs, rebuilt by commands or by the application.
RESULTS_DIR = user_data_dir() / "results" if PACKAGED else BUNDLED_RESULTS_DIR


def copy_bundled_results(
    source: Path = BUNDLED_RESULTS_DIR, target: Path = RESULTS_DIR
) -> list[Path]:
    """Copy the result files shipped in a package to the writable results folder.

    Files already in ``target`` are kept, so a log the user rebuilt is never replaced. Run from
    the source code both folders are the same and nothing is copied. Returns the copied files.
    """
    if not source.is_dir() or source.resolve() == target.resolve():
        return []
    copied = []
    for file in sorted(source.iterdir()):
        destination = target / file.name
        if file.is_file() and not destination.exists():
            target.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(file, destination)
            copied.append(destination)
    return copied


def use_persistent_matplotlib_cache(environ: MutableMapping[str, str] = os.environ) -> None:
    """In a packaged application, keep matplotlib's font cache from one start to the next.

    PyInstaller points matplotlib at a new temporary folder on every start (needed for one-file
    builds, which unpack to a new place each time), so the font cache, about 20 s to build, would
    be rebuilt at every start. Our package is a folder that never moves, so the cache can stay in
    the user's application-data folder. Must run before matplotlib is imported.
    """
    if PACKAGED:
        environ["MPLCONFIGDIR"] = str(user_data_dir() / "matplotlib")
