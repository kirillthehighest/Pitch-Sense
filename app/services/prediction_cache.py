"""Every league's computed predictions kept on disk, so a start of the server does not compute
them again (about 8 s a league on a Mac, 22 s on the Windows build machine).

A league's preparation (``PredictionService.preparation``) is a pure function of its matches, its
fixtures and the code. Its pickled result is saved under a key made of all three: the SHA-256 of
the code's fingerprint and of the job's arguments (their repr, which spells every match and
fixture). A start with the same data and code reads the result back in a few tenths of a second;
new data (an update of the season in progress) or new code gives a new key, and the league is
computed again, once.

The code's fingerprint is a hash of the application's Python sources. A package has no sources, so
the build writes the fingerprint next to the predictions it ships (``CODE_FILE``) and the packaged
server reads it from there.

The files are pickles, as the worker process already returns its results. They are read only
from the user's own folder, where only the application writes them, and from the read-only folder
inside the package; whatever could change those could as well change the application itself.

``python -m app.services.prediction_cache`` (run by ``packaging/build.py``) computes every
league's predictions into ``data/cache``, the folder a package ships.
"""

import hashlib
import os
import sys
import time
from collections.abc import Callable, Sequence
from functools import partial
from pathlib import Path
from typing import Any

from app import __version__
from app.data.paths import BUNDLED_CACHE_DIR, CACHE_DIR, PACKAGED
from app.services.processes import compute_here

FORMAT = 1  # raise when the file layout changes
CODE_FILE = "CODE"  # in a shipped cache: the fingerprint of the code that computed it
APP_DIR = Path(__file__).resolve().parents[1]


def source_fingerprint(root: Path = APP_DIR) -> str:
    """The SHA-256 of every Python source under ``root`` (path and content)."""
    digest = hashlib.sha256()
    for file in sorted(root.rglob("*.py")):
        digest.update(file.relative_to(root).as_posix().encode("utf-8") + b"\0")
        digest.update(file.read_bytes() + b"\0")
    return digest.hexdigest()


def code_fingerprint(packaged: bool = PACKAGED, shipped: Path = BUNDLED_CACHE_DIR) -> str:
    """The fingerprint of the running code: from its sources, or in a package the one its build
    wrote (the version, when it shipped no cache)."""
    if not packaged:
        return source_fingerprint()
    try:
        return (shipped / CODE_FILE).read_text(encoding="utf-8").strip()
    except OSError:
        return f"version {__version__}"


def job_key(job: partial, fingerprint: str) -> str:
    """The key of a preparation job: its function, its arguments and the code's fingerprint."""
    digest = hashlib.sha256()
    digest.update(f"{FORMAT}|{fingerprint}|{job.func.__module__}.{job.func.__qualname__}|".encode())
    digest.update(repr((job.args, sorted(job.keywords.items()))).encode("utf-8"))
    return digest.hexdigest()


class PredictionCache:
    """Pickled predictions by league: read from ``directory`` (written there) or from the
    read-only ``shipped`` folder of a package; a file whose key differs is not used."""

    def __init__(
        self, directory: Path, shipped: Path | None = None, fingerprint: str | None = None
    ) -> None:
        self.directory = directory
        self.shipped = shipped
        self.fingerprint = fingerprint or code_fingerprint()

    def key(self, job: partial) -> str:
        return job_key(job, self.fingerprint)

    def load(self, code: str, job: partial) -> bytes | None:
        """The saved result of ``job`` for league ``code``, or None."""
        expected = self.key(job).encode("ascii")
        folders = [self.directory]
        if self.shipped is not None and self.shipped != self.directory:
            folders.append(self.shipped)
        for folder in folders:
            try:
                key, _, data = (folder / f"{code}.pickle").read_bytes().partition(b"\n")
            except OSError:
                continue
            if key == expected:
                return data
        return None

    def save(self, code: str, job: partial, data: bytes) -> None:
        """Keep ``data``, the pickled result of ``job``, as league ``code``'s (replacing the
        previous one); written whole or not at all."""
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self.directory / f"{code}.pickle"
        partial_file = target.with_name(f"{target.name}.part")
        partial_file.write_bytes(self.key(job).encode("ascii") + b"\n" + data)
        os.replace(partial_file, target)


def server_cache() -> PredictionCache:
    """The cache of the server: the user's folder in a package (with the shipped predictions),
    ``data/cache`` from the source code."""
    return PredictionCache(CACHE_DIR, BUNDLED_CACHE_DIR)


def build_shipped_cache(
    competitions: Sequence[str],
    directory: Path = BUNDLED_CACHE_DIR,
    open_league: Callable[[str], Any] | None = None,
) -> PredictionCache:
    """Compute every league's predictions into ``directory``, with the fingerprint of these
    sources, as a package ships them."""
    if open_league is None:
        from app.services.registry import open_league
    fingerprint = source_fingerprint()
    cache = PredictionCache(directory, fingerprint=fingerprint)
    for code in competitions:
        started = time.perf_counter()
        job = open_league(code).predictions.preparation()
        cache.save(code, job, compute_here(job))
        print(f"{code}: predictions saved in {time.perf_counter() - started:.1f} s", flush=True)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / CODE_FILE).write_text(fingerprint + "\n", encoding="utf-8")
    return cache


def main() -> int:
    from app.services.catalog import available_competitions

    competitions = tuple(available_competitions())
    if not competitions:
        print(
            "The database holds no league. Run: python -m app.data.build_database", file=sys.stderr
        )
        return 1
    build_shipped_cache(competitions)
    return 0


if __name__ == "__main__":
    sys.exit(main())
