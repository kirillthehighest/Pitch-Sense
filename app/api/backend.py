"""What the server keeps between requests: each league's services, opened once; the comparison
of the leagues; the user's preferences; the preparation of every league's predictions: first
those saved by an earlier start (``app/services/prediction_cache.py``), then the others, one league
at a time in the worker process, the remembered league first; and the update of the season in
progress, asked by the user or started on its own when the data is older than
``AUTO_UPDATE_AFTER`` (Phase 24). After an update every league is read again and its new
predictions prepared aside: the previous ones answer until then, so no screen goes empty."""

import pickle
import sys
import threading
import time
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from app.services.catalog import available_competitions
from app.services.leagues import LeagueComparisonService
from app.services.prediction_cache import PredictionCache, server_cache
from app.services.preferences import Preferences
from app.services.processes import Computer, compute_in_process
from app.services.registry import LeagueServices, open_league
from app.services.updates import update_season

AUTO_UPDATE_AFTER = timedelta(hours=3)  # Football-Data adds results a few times a day at most
AUTO_UPDATE_CHECK_SECONDS = 600  # how often the age of the data is looked at
AUTO_UPDATE_RETRY = timedelta(hours=1)  # after a failed automatic update (offline, say)


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
        self._update_lock = threading.Lock()  # one update at a time, the user's or the automatic
        self._next_automatic: datetime | None = None  # no automatic update before then
        self.version = 0  # grows each time a league's data is replaced (the interface re-reads)
        self.automatic_problem: str | None = None  # why the last automatic update failed

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
        self._prepare({code: self.league(code) for code in self._order()}, replace=False)

    def _order(self) -> tuple[str, ...]:
        first = self.first_league
        return (first, *(code for code in self.competitions if code != first))

    def _prepare(self, leagues: dict[str, LeagueServices], replace: bool) -> None:
        """Prepare the predictions of ``leagues`` (in order): first those saved, then the
        others. With ``replace`` each league is served once prepared, in place of the one
        served until then; one that fails is reported and the previous one goes on."""
        for code, league in leagues.items():  # what was saved, a few tenths of a second a league
            if self._install_saved(code, league) and replace:
                self._serve(code, league)
        for code, league in leagues.items():
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
                continue
            finally:
                self._preparing = None
            if replace:
                self._serve(code, league)

    def _serve(self, code: str, league: LeagueServices) -> None:
        with self._lock:
            self._leagues[code] = league
            self._failures.pop(code, None)
            self.version += 1

    def _install_saved(self, code: str, league: LeagueServices) -> bool:
        """Install the league's saved predictions, when the cache has them for its data;
        returns whether the league is prepared."""
        predictions = league.predictions
        if self.cache is None or predictions.is_prepared:
            return predictions.is_prepared
        saved = self.cache.load(code, predictions.preparation())
        if saved is None:
            return False
        try:
            predictions.install(pickle.loads(saved))
        except Exception as error:  # a damaged file: computed again, and saved over
            print(
                f"Saved predictions of {code} unreadable, computing them: {error}", file=sys.stderr
            )
        return predictions.is_prepared

    def _save(self, code: str, job: Any, result: bytes) -> None:
        if self.cache is None:
            return
        try:
            self.cache.save(code, job, result)
        except OSError as error:  # the next start computes them again
            print(f"Predictions of {code} not saved: {error}", file=sys.stderr)

    def reload(self) -> None:
        """Read every league again after an update and prepare its new predictions in the
        background; each league's new data is served once its predictions are ready, and the
        previous data answers until then."""
        with self._lock:
            previous = self._worker

            def refresh() -> None:
                if previous is not None:
                    previous.join()  # the preparation already running finishes first
                self._prepare({code: self._open_league(code) for code in self._order()}, True)

            self._worker = threading.Thread(target=refresh, daemon=True)
            self._worker.start()

    def update(self) -> Any:
        """Download the season in progress and read every league again (the user's update);
        waits for an automatic update running. Returns what the update downloaded."""
        with self._update_lock:
            summary = self.update_data()
            self.reload()
            self.automatic_problem = None
            return summary

    @property
    def updating(self) -> bool:
        """Whether an update (the user's or the automatic one) is downloading now."""
        return self._update_lock.locked()

    def data_updated_at(self) -> datetime | None:
        """When the season in progress being served was downloaded; None when it never was."""
        times = [self.league(code).catalog.updated_at for code in self.competitions]
        known = [moment for moment in times if moment is not None]
        return max(known) if known else None

    def automatic_update(self, now: datetime | None = None) -> bool:
        """Update the data when it is older than ``AUTO_UPDATE_AFTER`` (or was never
        downloaded), unless an update runs or the last automatic one failed less than
        ``AUTO_UPDATE_RETRY`` ago. A failure (offline, a source down) is kept in
        ``automatic_problem``, never raised: the data served stays. Returns whether it updated."""
        now = now or datetime.now(UTC)
        updated_at = self.data_updated_at()
        if updated_at is not None and now - updated_at < AUTO_UPDATE_AFTER:
            return False
        if self._next_automatic is not None and now < self._next_automatic:
            return False
        if not self._update_lock.acquire(blocking=False):
            return False  # the user's update is running
        try:
            self.update_data()
            self.reload()
        except Exception as error:  # any failure leaves the data as it was
            self._next_automatic = now + AUTO_UPDATE_RETRY
            self.automatic_problem = str(error)
            print(f"Automatic update failed, trying again later: {error}", file=sys.stderr)
            return False
        finally:
            self._update_lock.release()
        self._next_automatic = None
        self.automatic_problem = None
        return True

    def start_automatic_updates(self, every: float = AUTO_UPDATE_CHECK_SECONDS) -> threading.Thread:
        """Look at the age of the data now and every ``every`` seconds, in a background thread
        that ends with the server."""

        def watch() -> None:
            while True:
                self.automatic_update()
                time.sleep(every)

        watcher = threading.Thread(target=watch, name="automatic-update", daemon=True)
        watcher.start()
        return watcher
