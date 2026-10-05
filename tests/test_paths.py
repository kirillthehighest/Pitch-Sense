"""Data locations from the source code and in a packaged application."""

from pathlib import Path

import pytest

from app.data import paths
from app.ui import main_window

HOME = Path("/home/someone")


@pytest.mark.parametrize(
    ("platform", "environ", "expected"),
    [
        ("darwin", {}, HOME / "Library" / "Application Support" / "PitchSense"),
        ("win32", {"LOCALAPPDATA": "C:/Users/someone/AppData/Local"}, None),
        ("win32", {}, HOME / "AppData" / "Local" / "PitchSense"),
        ("linux", {"XDG_DATA_HOME": "/data"}, Path("/data") / "PitchSense"),
        ("linux", {}, HOME / ".local" / "share" / "PitchSense"),
    ],
    ids=["macOS", "Windows", "Windows without LOCALAPPDATA", "Linux", "Linux default"],
)
def test_user_data_folder_of_each_operating_system(platform, environ, expected):
    if expected is None:
        expected = Path(environ["LOCALAPPDATA"]) / "PitchSense"

    assert paths.user_data_dir(platform, environ, HOME) == expected


def test_from_the_source_code_everything_lives_in_the_project_data_folder():
    assert not paths.PACKAGED
    assert paths.DATA_DIR == paths.PROJECT_ROOT / "data"
    assert paths.DATABASE_PATH.parent == paths.RESULTS_DIR.parent == paths.DATA_DIR
    assert paths.RESULTS_DIR == paths.BUNDLED_RESULTS_DIR
    assert paths.copy_bundled_results() == []


def test_a_package_keeps_the_matplotlib_cache_in_the_user_folder(monkeypatch):
    environ = {"MPLCONFIGDIR": "/tmp/pyinstaller-temporary"}

    paths.use_persistent_matplotlib_cache(environ)
    assert environ["MPLCONFIGDIR"] == "/tmp/pyinstaller-temporary"  # source code: unchanged
    monkeypatch.setattr(paths, "PACKAGED", True)
    paths.use_persistent_matplotlib_cache(environ)

    assert environ["MPLCONFIGDIR"] == str(paths.user_data_dir() / "matplotlib")


def test_the_shipped_log_is_copied_once_and_a_rebuilt_log_is_kept(tmp_path):
    shipped = tmp_path / "package" / "results"
    shipped.mkdir(parents=True)
    (shipped / "backtest_SP1.csv").write_text("shipped", encoding="utf-8")
    (shipped / "backtest_XX.csv").write_text("other", encoding="utf-8")
    user = tmp_path / "user" / "results"

    copied = paths.copy_bundled_results(shipped, user)

    assert copied == [user / "backtest_SP1.csv", user / "backtest_XX.csv"]
    assert (user / "backtest_SP1.csv").read_text(encoding="utf-8") == "shipped"
    (user / "backtest_SP1.csv").write_text("rebuilt", encoding="utf-8")
    assert paths.copy_bundled_results(shipped, user) == []
    assert (user / "backtest_SP1.csv").read_text(encoding="utf-8") == "rebuilt"


def test_nothing_is_copied_without_shipped_results(tmp_path):
    assert paths.copy_bundled_results(tmp_path / "missing", tmp_path / "user") == []
    assert not (tmp_path / "user").exists()


def test_start_up_copies_the_shipped_results_before_loading(application, monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(main_window, "copy_bundled_results", lambda: calls.append("copy"))

    def load():
        calls.append("load")
        raise FileNotFoundError("Database not found")

    class MessageBox:
        @staticmethod
        def critical(parent, title, text):
            calls.append("message")

    monkeypatch.setattr(main_window, "default_context", load)
    monkeypatch.setattr(main_window, "QMessageBox", MessageBox)

    assert main_window.main() == 1
    assert calls == ["copy", "load", "message"]


def test_a_failed_copy_is_reported_and_start_up_goes_on(application, monkeypatch):
    calls = []

    def copy():
        raise PermissionError("read-only folder")

    class MessageBox:
        @staticmethod
        def warning(parent, title, text):
            calls.append(text)

        @staticmethod
        def critical(parent, title, text):
            calls.append("stopped: " + text)

    def load():
        raise FileNotFoundError("no database")

    monkeypatch.setattr(main_window, "copy_bundled_results", copy)
    monkeypatch.setattr(main_window, "default_context", load)
    monkeypatch.setattr(main_window, "QMessageBox", MessageBox)

    assert main_window.main() == 1
    assert calls == ["Could not copy the prediction log: read-only folder", "stopped: no database"]
