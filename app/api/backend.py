"""What the server keeps between requests: each league's services, opened once; the comparison
of the leagues; the user's preferences; and the preparation of every league's predictions: first
those saved by an earlier start (``app/services/prediction_cache.py``), then the others, one league
at a time in the worker process, the remembered league first."""

import pickle
import sys
import threading
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from app.services.catalog import available_competitions
from app.services.leagues import LeagueComparisonService
from app.services.prediction_cache import PredictionCache, server_cache
from app.services.preferences import Preferences
from app.services.processes import Computer, compute_in_process
from app.services.registry import LeagueServices, open_league
from app.services.updates import update_season


class Backend:
    """The server's state; every method is safe to call from the server's request threads."""

    def __init__(
        self,
        competitions: tuple[str, ...],
        open_league: Callable[[str], LeagueServices] = open_league,
        comparison: LeagueComparisonService | None = None,
        preferences: Preferences | None = None,
        compute: Computer = compute_in_process,
        update_data: Callable[[], Any] = update_season,
        today: Callable[[], date] = date.today,
        cache: PredictionCache | None = None,
    ) -> None:
        if not competitions:
            raise ValueError("no league to serve")
        self.competitions = competitions
        self._open_league = open_league
        self.comparison = comparison or LeagueComparisonService(competitions)
        self.preferences = preferences or Preferences()
        self.compute = compute
        self.update_data = update_data
        self.today = today
        self.cache = cache
        self._leagues: dict[str, LeagueServices] = {}
        self._lock = threading.RLock()
        self._preparing: str | None = None
        self._failures: dict[str, str] = {}
        self._worker: threading.Thread | None = None

    @classmethod
    def from_database(cls, preferences: Path | None = None) -> Backend:
        """The real data; raises FileNotFoundError when the database has not been built. The
        preferences are the user's, unless another file is given."""
        competitions = tuple(available_competitions())
        if not competitions:
            raise FileNotFoundError("The database holds no known league. Run the database build.")
        chosen = None if preferences is None else Preferences(preferences)
        return cls(competitions, preferences=chosen, cache=server_cache())

    def league(self, code: str) -> LeagueServices:
        """A league's services, opened the first time they are asked for."""
        if code not in self.competitions:
            raise KeyError(code)
        with self._lock:
            if code not in self._leagues:
                self._leagues[code] = self._open_league(code)
            return self._leagues[code]

    @property
    def first_league(self) -> str:
        remembered = self.preferences.competition
        return remembered if remembered in self.competitions else self.competitions[0]

    def is_prepared(self, code: str) -> bool:
        return self.league(code).predictions.is_prepared

    def preparing(self) -> str | None:
        """The league whose predictions are being computed now, if any."""
        return self._preparing

    def failure(self, code: str) -> str | None:
        """Why a league's predictions could not be computed, if they could not."""
        return self._failures.get(code)

    def prepare_all(self, wait: bool = False) -> None:
        """Compute the predictions of every league, the remembered one first, one at a time
        (in a background thread, unless ``wait``)."""
        with self._lock:
            if self._worker is None or not self._worker.is_alive():
                self._worker = threading.Thread(target=self._prepare_all, daemon=True)
                self._worker.start()
            worker = self._worker
        if wait:  # also when the preparation was already running
            worker.join()

    def _prepare_all(self) -> None:
        first = self.first_league
        order = (first, *(code for code in self.competitions if code != first))
        for code in order:  # what an earlier start saved, a few tenths of a second a league
            self._install_saved(code)
        for code in order:
            league = self.league(code)
            if league.predictions.is_prepared:
                continue
            self._preparing = code
            try:
                job = league.predictions.preparation()
                result = self.compute(job)
                league.predictions.install(pickle.loads(result))
                self._save(code, job, result)
            except Exception as error:  # reported per league, the others still prepared
                self._failures[code] = str(error)
            finally:
                self._preparing = None

    def _install_saved(self, code: str) -> None:
        """Install the league's saved predictions, when the cache has them for its data."""
        if self.cache is None:
            return
        predictions = self.league(code).predictions
        if predictions.is_prepared:
            return
        saved = self.cache.load(code, predictions.preparation())
        if saved is None:
            return
        try:
            predictions.install(pickle.loads(saved))
        except Exception as error:  # a damaged file: computed again, and saved over
            print(
                f"Saved predictions of {code} unreadable, computing them: {error}", file=sys.stderr
            )

    def _save(self, code: str, job: Any, result: bytes) -> None:
        if self.cache is None:
            return
        try:
            self.cache.save(code, job, result)
        except OSError as error:  # the next start computes them again
            print(f"Predictions of {code} not saved: {error}", file=sys.stderr)

    def reload(self) -> None:
        """Forget the opened leagues after an update, so they are read again with the new data,
        and prepare their predictions again."""
        if self._worker is not None:
            self._worker.join()
        with self._lock:
            self._leagues.clear()
            self._failures.clear()
        self.prepare_all()
