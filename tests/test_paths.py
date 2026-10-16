"""Data locations from the source code and in a packaged application."""

from pathlib import Path

import pytest

from app.data import paths

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


@pytest.fixture
def shipped(tmp_path):
    folder = tmp_path / "package" / "results"
    folder.mkdir(parents=True)
    (folder / "backtest_SP1.csv").write_text("shipped", encoding="utf-8")
    (folder / "backtest_XX.csv").write_text("other", encoding="utf-8")
    return folder


def test_the_shipped_logs_are_copied_once_and_a_rebuilt_log_is_kept(shipped, tmp_path):
    user = tmp_path / "user" / "results"

    copied = paths.copy_bundled_results(shipped, user, "0.2.0")

    assert copied == [user / "backtest_SP1.csv", user / "backtest_XX.csv"]
    assert (user / "backtest_SP1.csv").read_text(encoding="utf-8") == "shipped"
    assert (user / paths.VERSION_FILE).read_text(encoding="utf-8") == "0.2.0\n"
    (user / "backtest_SP1.csv").write_text("rebuilt", encoding="utf-8")
    assert paths.copy_bundled_results(shipped, user, "0.2.0") == []
    assert (user / "backtest_SP1.csv").read_text(encoding="utf-8") == "rebuilt"


def test_a_missing_log_is_copied_again_within_a_version(shipped, tmp_path):
    user = tmp_path / "user" / "results"
    paths.copy_bundled_results(shipped, user, "0.2.0")
    (user / "backtest_XX.csv").unlink()

    assert paths.copy_bundled_results(shipped, user, "0.2.0") == [user / "backtest_XX.csv"]


@pytest.mark.parametrize("old_version", [None, "0.1.0"])
def test_an_update_replaces_the_logs_of_the_older_version(shipped, tmp_path, old_version):
    user = tmp_path / "user" / "results"
    user.mkdir(parents=True)
    (user / "backtest_SP1.csv").write_text("built by 0.1.0", encoding="utf-8")
    (user / "notes.txt").write_text("the user's own file", encoding="utf-8")
    if old_version is not None:
        (user / paths.VERSION_FILE).write_text(old_version, encoding="utf-8")

    copied = paths.copy_bundled_results(shipped, user, "0.2.0")

    assert copied == [user / "backtest_SP1.csv", user / "backtest_XX.csv"]
    assert (user / "backtest_SP1.csv").read_text(encoding="utf-8") == "shipped"
    assert (user / "notes.txt").read_text(encoding="utf-8") == "the user's own file"
    assert (user / paths.VERSION_FILE).read_text(encoding="utf-8") == "0.2.0\n"


def test_nothing_is_copied_without_shipped_results(tmp_path):
    assert paths.copy_bundled_results(tmp_path / "missing", tmp_path / "user") == []
    assert not (tmp_path / "user").exists()


def test_from_the_source_code_nothing_is_copied(shipped):
    assert paths.copy_bundled_results(shipped, shipped) == []
    assert not (shipped / paths.VERSION_FILE).exists()
