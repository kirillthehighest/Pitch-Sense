"""The automatic update of the season in progress (Phase 24): when the data is old enough, the
server downloads it on its own, reads every league again and keeps serving the previous data
until the new predictions are ready; a failure never stops the server and is retried later."""

import urllib.error
from datetime import UTC, datetime, timedelta

import pytest

from app.api.backend import AUTO_UPDATE_AFTER, AUTO_UPDATE_RETRY
from app.data.live import UpdateSummary

NOW = datetime(2008, 9, 10, 12, 0, tzinfo=UTC)


def counting(updates: list[datetime]):
    def update_data() -> UpdateSummary:
        updates.append(NOW)
        return UpdateSummary("2008-09", NOW, ())

    return update_data


def test_data_never_downloaded_is_updated_at_once(make_backend, two_league_database):
    backend = make_backend(two_league_database, ("E0", "SP1"))
    backend.prepare_all(wait=True)
    updates: list[datetime] = []
    backend.update_data = counting(updates)

    assert backend.data_updated_at() is None
    assert backend.automatic_update(NOW) is True

    backend.prepare_all(wait=True)  # the leagues read again, with their predictions
    assert len(updates) == 1 and backend.version == 2
    assert backend.automatic_problem is None


def test_recent_data_is_left_alone_and_old_data_updated(
    make_backend, two_league_database, live_dir, monkeypatch
):
    backend = make_backend(two_league_database, ("SP1",), live_dir=live_dir)
    backend.prepare_all(wait=True)
    downloaded = backend.data_updated_at()
    updates: list[datetime] = []
    backend.update_data = counting(updates)

    assert downloaded is not None
    assert backend.automatic_update(downloaded + AUTO_UPDATE_AFTER - timedelta(minutes=1)) is False
    assert backend.automatic_update(downloaded + AUTO_UPDATE_AFTER) is True
    assert len(updates) == 1


def test_a_failed_automatic_update_keeps_the_data_and_waits_before_trying_again(
    make_backend, two_league_database
):
    backend = make_backend(two_league_database, ("SP1",))  # its update_data has no network
    backend.prepare_all(wait=True)
    served = backend.league("SP1")

    assert backend.automatic_update(NOW) is False

    assert "network" in backend.automatic_problem
    assert backend.league("SP1") is served and backend.is_prepared("SP1")
    updates: list[datetime] = []
    backend.update_data = counting(updates)
    assert backend.automatic_update(NOW + AUTO_UPDATE_RETRY - timedelta(minutes=1)) is False
    assert updates == []  # too soon after the failure
    assert backend.automatic_update(NOW + AUTO_UPDATE_RETRY) is True
    assert backend.automatic_problem is None


def test_no_automatic_update_while_the_user_s_update_runs(make_backend, two_league_database):
    backend = make_backend(two_league_database, ("SP1",))
    backend.prepare_all(wait=True)
    updates: list[datetime] = []
    backend.update_data = counting(updates)

    with backend._update_lock:  # the user's update is downloading
        assert backend.updating
        assert backend.automatic_update(NOW) is False

    assert updates == [] and not backend.updating


def test_the_user_s_update_reports_its_failure(make_backend, two_league_database):
    backend = make_backend(two_league_database, ("SP1",))

    with pytest.raises(urllib.error.URLError, match="network"):
        backend.update()

    assert not backend.updating
