"""The saved predictions (app/services/prediction_cache.py): a result comes back only for the same
data and code, from the user's folder or the one a package ships, and the server installs it
without computing."""

import pickle
from functools import partial

import pytest

from app import __version__
from app.services.prediction_cache import (
    CODE_FILE,
    PredictionCache,
    build_shipped_cache,
    code_fingerprint,
    job_key,
    source_fingerprint,
)


def square(value: int) -> int:
    return value * value


def test_a_saved_result_comes_back_for_the_same_job(tmp_path):
    cache = PredictionCache(tmp_path, fingerprint="code")

    cache.save("SP1", partial(square, 3), b"nine")

    assert cache.load("SP1", partial(square, 3)) == b"nine"
    assert cache.load("SP1", partial(square, 4)) is None  # other data
    assert cache.load("E0", partial(square, 3)) is None  # another league
    assert (
        PredictionCache(tmp_path, fingerprint="other code").load("SP1", partial(square, 3)) is None
    )
    assert [file.name for file in tmp_path.iterdir()] == ["SP1.pickle"]  # no partial file left


def test_a_new_result_replaces_the_league_s_old_one(tmp_path):
    cache = PredictionCache(tmp_path, fingerprint="code")
    cache.save("SP1", partial(square, 3), b"nine")

    cache.save("SP1", partial(square, 4), b"sixteen")

    assert cache.load("SP1", partial(square, 3)) is None
    assert cache.load("SP1", partial(square, 4)) == b"sixteen"


def test_the_user_s_folder_comes_before_the_shipped_one(tmp_path):
    user, shipped = tmp_path / "user", tmp_path / "shipped"
    PredictionCache(shipped, fingerprint="code").save("SP1", partial(square, 3), b"shipped")
    cache = PredictionCache(user, shipped, fingerprint="code")

    assert cache.load("SP1", partial(square, 3)) == b"shipped"
    cache.save("SP1", partial(square, 3), b"computed")
    assert cache.load("SP1", partial(square, 3)) == b"computed"
    assert (
        PredictionCache(shipped, fingerprint="code").load("SP1", partial(square, 3)) == b"shipped"
    )


def test_a_missing_folder_or_file_is_no_result(tmp_path):
    cache = PredictionCache(tmp_path / "nowhere", tmp_path / "neither", fingerprint="code")

    assert cache.load("SP1", partial(square, 3)) is None


def test_the_key_spells_the_job_and_the_code():
    key = job_key(partial(square, 3), "code")

    assert key == job_key(partial(square, 3), "code")
    assert len({key, job_key(partial(square, 4), "code"), job_key(partial(square, 3), "new")}) == 3


def test_the_fingerprint_follows_the_sources(tmp_path):
    (tmp_path / "module.py").write_text("x = 1\n", encoding="utf-8")
    before = source_fingerprint(tmp_path)

    (tmp_path / "module.py").write_text("x = 2\n", encoding="utf-8")

    assert source_fingerprint(tmp_path) != before
    assert code_fingerprint(packaged=False) == source_fingerprint()


def test_a_package_uses_the_fingerprint_its_build_wrote(tmp_path):
    (tmp_path / CODE_FILE).write_text("written by the build\n", encoding="utf-8")

    assert code_fingerprint(packaged=True, shipped=tmp_path) == "written by the build"
    assert code_fingerprint(packaged=True, shipped=tmp_path / "none") == f"version {__version__}"


def test_the_build_ships_every_league_s_predictions(tmp_path, make_backend, two_league_database):
    backend = make_backend(two_league_database, ("E0", "SP1"))

    built = build_shipped_cache(("E0", "SP1"), tmp_path, open_league=backend.league)

    fingerprint = (tmp_path / CODE_FILE).read_text(encoding="utf-8").strip()
    assert fingerprint == source_fingerprint() == built.fingerprint
    packaged = PredictionCache(tmp_path / "user", tmp_path, fingerprint=fingerprint)
    for code in ("E0", "SP1"):
        predictions = backend.league(code).predictions
        saved = pickle.loads(packaged.load(code, predictions.preparation()))
        assert len(saved.results) == len(predictions.preparation()().results)


def never(job) -> bytes:
    raise AssertionError("the saved predictions should have been used")


def test_a_start_with_saved_predictions_computes_nothing(
    make_backend, two_league_database, tmp_path
):
    cache = PredictionCache(tmp_path / "cache", fingerprint="code")
    first = make_backend(two_league_database, ("E0", "SP1"))
    first.cache = cache
    first.prepare_all(wait=True)
    assert sorted(file.name for file in (tmp_path / "cache").iterdir()) == [
        "E0.pickle",
        "SP1.pickle",
    ]

    second = make_backend(two_league_database, ("E0", "SP1"), compute=never)
    second.cache = cache
    second.prepare_all(wait=True)

    for code in ("E0", "SP1"):
        assert second.is_prepared(code) and second.failure(code) is None
        assert (
            second.league(code).predictions.match_days()
            == first.league(code).predictions.match_days()
        )


def test_damaged_saved_predictions_are_computed_again_and_saved_over(
    make_backend, two_league_database, tmp_path, capsys
):
    cache = PredictionCache(tmp_path / "cache", fingerprint="code")
    first = make_backend(two_league_database, ("SP1",))
    first.cache = cache
    first.prepare_all(wait=True)
    saved = tmp_path / "cache" / "SP1.pickle"
    key = saved.read_bytes().partition(b"\n")[0]
    saved.write_bytes(key + b"\nnot a pickle")

    second = make_backend(two_league_database, ("SP1",))
    second.cache = cache
    second.prepare_all(wait=True)

    assert second.is_prepared("SP1") and second.failure("SP1") is None
    assert "unreadable" in capsys.readouterr().err
    assert pickle.loads(saved.read_bytes().partition(b"\n")[2])  # a good file again


@pytest.mark.parametrize("problem", [PermissionError("read-only"), OSError("disk full")])
def test_a_cache_that_cannot_be_written_only_costs_the_next_start(
    make_backend, two_league_database, tmp_path, capsys, problem
):
    class ReadOnly(PredictionCache):
        def save(self, code, job, data):
            raise problem

    backend = make_backend(two_league_database, ("SP1",))
    backend.cache = ReadOnly(tmp_path, fingerprint="code")

    backend.prepare_all(wait=True)

    assert backend.is_prepared("SP1") and backend.failure("SP1") is None
    assert "not saved" in capsys.readouterr().err
