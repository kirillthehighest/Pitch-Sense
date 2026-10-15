"""The command line of the application: the window, the self-test and the update."""

import pytest

from app import __main__ as entry
from app.data import update
from app.ui import main_window, self_test


@pytest.fixture
def calls(monkeypatch):
    called = []
    monkeypatch.setattr(main_window, "main", lambda: called.append("window") or 0)
    monkeypatch.setattr(self_test, "run_self_test", lambda: called.append("self-test") or 0)
    monkeypatch.setattr(update, "main", lambda: called.append("update") or 3)
    monkeypatch.setattr(entry, "use_persistent_matplotlib_cache", lambda: None)
    return called


def test_the_window_opens_by_default(calls):
    assert entry.run([]) == 0
    assert calls == ["window"]


def test_the_self_test_runs_on_request(calls):
    assert entry.run(["--self-test"]) == 0
    assert calls == ["self-test"]


def test_the_update_runs_without_the_window_and_returns_its_exit_code(calls):
    assert entry.run(["--update"]) == 3
    assert calls == ["update"]
