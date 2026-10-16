"""What the server keeps between requests: each league's services, opened once; the comparison
of the leagues; the user's preferences; and the preparation of every league's predictions, one
league at a time in the worker process, the remembered league first."""

import pickle
import threading
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

from app.services.catalog import available_competitions
from app.services.leagues import LeagueComparisonService
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
        return cls(competitions, preferences=chosen)

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
            if self._worker is not None and self._worker.is_alive():
                return
            self._worker = threading.Thread(target=self._prepare_all, daemon=True)
            self._worker.start()
        if wait:
            self._worker.join()

    def _prepare_all(self) -> None:
        first = self.first_league
        for code in (first, *(code for code in self.competitions if code != first)):
            league = self.league(code)
            if league.predictions.is_prepared:
                continue
            self._preparing = code
            try:
                result = self.compute(league.predictions.preparation())
                league.predictions.install(pickle.loads(result))
            except Exception as error:  # reported per league, the others still prepared
                self._failures[code] = str(error)
            finally:
                self._preparing = None

    def reload(self) -> None:
        """Forget the opened leagues after an update, so they are read again with the new data,
        and prepare their predictions again."""
        if self._worker is not None:
            self._worker.join()
        with self._lock:
            self._leagues.clear()
            self._failures.clear()
        self.prepare_all()
