"""The season in progress: reading the calendar, matching team names, downloading and storing."""

import hashlib
import json
import urllib.error
import urllib.request
from datetime import date, datetime, time

import pytest

from app.data import update as update_command
from app.data.live import (
    MANIFEST,
    MAX_DOWNLOAD_BYTES,
    CalendarMatch,
    build_live_league,
    copy_bundled_live,
    fetch,
    load_live_league,
    match_team_names,
    parse_calendar,
    read_manifest,
    season_years,
    update_live_data,
)
from app.data.models import Match, Outcome
from app.data.preprocessing import DataValidationError
from tests.conftest import CALENDAR_NAMES, LIVE_PLAYED, LIVE_SEASON, LIVE_TODAY

UPDATED = datetime(2008, 9, 10, 12, 0)


def calendar_bytes(*matches: dict) -> bytes:
    return json.dumps({"name": "test", "matches": list(matches)}).encode()


def entry(day: int, home: str, away: str, score: tuple[int, int] | None = None) -> CalendarMatch:
    return CalendarMatch(date(2008, 9, day), None, home, away, score)


def played(day: int, home: str, away: str, home_goals: int, away_goals: int) -> Match:
    return Match(
        competition="SP1",
        season=LIVE_SEASON,
        match_date=date(2008, 9, day),
        home_team=home,
        away_team=away,
        home_goals=home_goals,
        away_goals=away_goals,
        result=Outcome.from_score(home_goals, away_goals),
    )


def test_season_years_name_football_datas_folder():
    assert season_years("2026-27") == "2627"
    assert season_years("1999-00") == "9900"


# --- downloading one file (the network itself is replaced) ---


class Response:
    def __init__(self, data: bytes) -> None:
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *exception_info):
        return False

    def read(self, limit: int) -> bytes:
        return self.data[:limit]


def test_a_download_names_the_application_and_returns_the_bytes(monkeypatch):
    requests = []

    def urlopen(request, timeout, context):
        requests.append((request.full_url, request.get_header("User-agent"), timeout))
        return Response(b"Div,Date")

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    assert fetch("https://example.org/SP1.csv", timeout=5) == b"Div,Date"
    assert requests[0][0] == "https://example.org/SP1.csv"
    assert requests[0][1].startswith("PitchSense/")
    assert requests[0][2] == 5


def test_a_file_too_large_is_refused(monkeypatch):
    monkeypatch.setattr(
        urllib.request, "urlopen", lambda *_, **__: Response(b"x" * (MAX_DOWNLOAD_BYTES + 1))
    )

    with pytest.raises(DataValidationError, match="larger than"):
        fetch("https://example.org/big.csv")


def test_a_file_not_published_yet_is_explained(monkeypatch):
    def urlopen(request, timeout, context):
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)

    with pytest.raises(FileNotFoundError, match="is not published yet"):
        fetch("https://example.org/2627/SP1.csv")


# --- the calendar ---


def test_a_calendar_gives_dates_kickoffs_teams_and_known_scores():
    data = calendar_bytes(
        {
            "date": "2008-09-01",
            "time": "18:30",
            "team1": "A",
            "team2": "B",
            "score": {"ft": [2, 1]},
        },
        {"date": "2008-09-02", "team1": "B", "team2": "A", "score": {"ht": [0, 0]}},
        {"date": "2008-09-03", "time": "20:45 UTC+2", "team1": "A", "team2": "C"},
        {"date": "2008-09-04", "team1": "C", "team2": "A", "score": [0, 0]},
    )

    calendar = parse_calendar(data, LIVE_SEASON, "test")

    assert calendar == [
        CalendarMatch(date(2008, 9, 1), time(18, 30), "A", "B", (2, 1)),
        CalendarMatch(date(2008, 9, 2), None, "B", "A", None),
        CalendarMatch(date(2008, 9, 3), time(20, 45), "A", "C", None),
        CalendarMatch(date(2008, 9, 4), None, "C", "A", (0, 0)),
    ]


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"<html>", "not a calendar"),
        (json.dumps({"name": "x"}).encode(), "no list of matches"),
        (calendar_bytes({"date": "2008-09-01", "team1": "A"}), "match 1"),
        (calendar_bytes({"date": "2008-09-01", "team1": "A", "team2": "A"}), "itself"),
        (calendar_bytes({"date": "2009-09-01", "team1": "A", "team2": "B"}), "outside season"),
        (calendar_bytes({"date": "1.9.2008", "team1": "A", "team2": "B"}), "match 1"),
        (
            calendar_bytes(
                {"date": "2008-09-01", "team1": "A", "team2": "B", "score": {"ft": [1, -1]}}
            ),
            "two goal counts",
        ),
        (
            calendar_bytes({"date": "2008-09-01", "team1": "A", "team2": "B", "score": "1-0"}),
            "two goal counts",
        ),
        (
            calendar_bytes(
                {"date": "2008-09-01", "team1": "A", "team2": "B"},
                {"date": "2008-09-08", "team1": "A", "team2": "B"},
            ),
            "A hosts B 2 times",
        ),
    ],
)
def test_a_damaged_calendar_is_refused(data, message):
    with pytest.raises(DataValidationError, match=message):
        parse_calendar(data, LIVE_SEASON, "test")


# --- matching the team names ---


def test_names_are_matched_through_the_matches_both_sources_have_played():
    calendar = [
        entry(1, "Alpha CF", "Bravo United", (1, 0)),
        entry(2, "Bravo United", "Alpha CF", (2, 2)),
        entry(9, "Alpha CF", "Real Charlie"),  # not played: no vote
    ]
    matches = [played(1, "Alpha", "Bravo", 1, 0), played(2, "Bravo", "Alpha", 2, 2)]

    names, unmatched = match_team_names(calendar, matches)

    assert names == {"Alpha CF": "Alpha", "Bravo United": "Bravo"}
    assert unmatched == ("Real Charlie",)


def test_a_date_one_day_apart_still_matches():
    calendar = [entry(1, "A1", "B1", (1, 0)), entry(3, "B1", "A1", (0, 3))]
    matches = [played(2, "A", "B", 1, 0), played(4, "B", "A", 0, 3)]

    assert match_team_names(calendar, matches) == ({"A1": "A", "B1": "B"}, ())


def test_one_shared_match_is_not_enough():
    names, unmatched = match_team_names([entry(1, "A1", "B1", (1, 0))], [played(1, "A", "B", 1, 0)])

    assert names == {}
    assert unmatched == ("A1", "B1")


def test_an_ambiguous_match_gives_no_vote():
    # Two matches end 1-0 on the same day, so the calendar's 1-0 cannot tell which one it is.
    calendar = [entry(1, "A1", "B1", (1, 0)), entry(2, "A1", "B1", (1, 0))]
    matches = [played(1, "A", "B", 1, 0), played(1, "C", "D", 1, 0), played(2, "A", "B", 1, 0)]

    names, _ = match_team_names(calendar, matches)

    assert names == {}  # one vote each, from day 2 only


def test_two_calendar_names_cannot_take_the_same_team():
    calendar = [
        entry(1, "A1", "B1", (1, 0)),
        entry(2, "B1", "A1", (2, 0)),
        entry(3, "A2", "B1", (3, 0)),
        entry(4, "B1", "A2", (4, 0)),
    ]
    matches = [
        played(1, "A", "B", 1, 0),
        played(2, "B", "A", 2, 0),
        played(3, "A", "B", 3, 0),
        played(4, "B", "A", 4, 0),
    ]

    names, unmatched = match_team_names(calendar, matches)

    assert names == {"B1": "B"}
    assert unmatched == ("A1", "A2")


def test_fixtures_are_the_calendar_matches_nobody_has_played():
    calendar = [
        entry(1, "A1", "B1", (1, 0)),
        entry(2, "B1", "A1", (0, 2)),
        entry(3, "A1", "C1"),  # played: Football-Data has it, the calendar has no score yet
        entry(9, "C1", "A1"),
        entry(10, "C1", "X1"),  # X1 is unknown, so this fixture is left out
    ]
    matches = [
        played(1, "A", "B", 1, 0),
        played(2, "B", "A", 0, 2),
        played(3, "A", "C", 1, 1),
        played(4, "C", "B", 2, 1),
    ]
    calendar += [entry(4, "C1", "B1", (2, 1)), entry(5, "B1", "C1", (0, 0))]
    matches += [played(5, "B", "C", 0, 0)]

    league = build_live_league("SP1", LIVE_SEASON, matches, calendar, UPDATED)

    assert [(f.match_date.day, f.home_team, f.away_team) for f in league.fixtures] == [
        (9, "C", "A")
    ]
    assert league.unmatched_teams == ("X1",)
    assert league.matches[0].match_date == date(2008, 9, 1)


# --- downloading and reading ---


def test_an_update_stores_both_files_and_describes_them(live_dir, live_files):
    manifest = read_manifest(live_dir)

    assert manifest["season"] == LIVE_SEASON
    assert manifest["leagues"] == ["SP1"]
    assert sorted(path.name for path in live_dir.iterdir()) == ["SP1.csv", "SP1.json", MANIFEST]
    for name, source in manifest["sources"].items():
        data = (live_dir / name).read_bytes()
        assert data == live_files[source["url"]]
        assert source["sha256"] == hashlib.sha256(data).hexdigest()


def test_the_league_in_progress_is_read_in_football_datas_names(live_dir):
    league = load_live_league("SP1", live_dir)

    assert league.season == LIVE_SEASON
    assert len(league.matches) == LIVE_PLAYED
    teams = {team for f in league.fixtures for team in (f.home_team, f.away_team)}
    assert teams == set(CALENDAR_NAMES)
    assert len(league.fixtures) == 12 - LIVE_PLAYED  # the 7th was played, without a calendar score
    played_pairs = {(m.home_team, m.away_team) for m in league.matches}
    assert not played_pairs & {(f.home_team, f.away_team) for f in league.fixtures}
    assert all(f.kickoff_time == time(18, 30) for f in league.fixtures)
    assert league.unmatched_teams == ()


def test_a_league_never_downloaded_is_none(tmp_path, live_dir):
    assert load_live_league("SP1", tmp_path / "nothing") is None
    assert load_live_league("E0", live_dir) is None


def test_damaged_files_are_refused(live_dir):
    (live_dir / "SP1.csv").write_text("Div,Date\nSP1,32/13/08\n", encoding="utf-8")

    with pytest.raises(DataValidationError, match="missing required columns"):
        load_live_league("SP1", live_dir)


def test_a_damaged_description_is_refused(live_dir):
    (live_dir / MANIFEST).write_text("{}", encoding="utf-8")

    with pytest.raises(DataValidationError, match="not a valid update description"):
        load_live_league("SP1", live_dir)


def test_results_that_cannot_be_a_season_in_progress_are_refused(live_dir):
    rows = (live_dir / "SP1.csv").read_text(encoding="utf-8").splitlines()
    repeated = rows[1].replace("01/09/08", "20/09/08")  # Alpha hosts Bravo a second time
    (live_dir / "SP1.csv").write_text("\n".join([*rows, repeated]) + "\n", encoding="utf-8")

    with pytest.raises(DataValidationError, match="Alpha hosted Bravo 2 times"):
        load_live_league("SP1", live_dir)


def test_the_season_comes_from_the_day_of_the_update(tmp_path, fake_fetch, four_team_league):
    with pytest.raises(urllib.error.URLError, match="mmz4281/0910/SP1.csv"):
        update_live_data(
            tmp_path / "live",
            ("SP1",),
            today=date(2009, 7, 1),
            fetch=fake_fetch,
            competitions=four_team_league,
        )


def test_a_failed_download_keeps_the_previous_data(live_dir, live_files, four_team_league):
    before = {path.name: path.read_bytes() for path in live_dir.iterdir()}

    def fetch(url):
        if url.endswith(".json"):
            raise urllib.error.URLError("network down")
        return live_files[url]

    with pytest.raises(urllib.error.URLError):
        update_live_data(
            live_dir, ("SP1",), today=LIVE_TODAY, fetch=fetch, competitions=four_team_league
        )

    assert {path.name: path.read_bytes() for path in live_dir.iterdir()} == before
    assert sorted(path.name for path in live_dir.parent.iterdir() if "live" in path.name) == [
        "live"
    ]


def test_a_damaged_download_keeps_the_previous_data(live_dir, live_files, four_team_league):
    before = {path.name: path.read_bytes() for path in live_dir.iterdir()}

    def fetch(url):
        return b"<html>maintenance</html>" if url.endswith(".json") else live_files[url]

    with pytest.raises(DataValidationError, match="not a calendar"):
        update_live_data(
            live_dir, ("SP1",), today=LIVE_TODAY, fetch=fetch, competitions=four_team_league
        )

    assert {path.name: path.read_bytes() for path in live_dir.iterdir()} == before


def test_a_league_needs_a_calendar_source(tmp_path, fake_fetch):
    from app.data.competitions import Competition

    with pytest.raises(DataValidationError, match="no calendar source"):
        update_live_data(
            tmp_path / "live",
            ("SP1",),
            today=LIVE_TODAY,
            fetch=fake_fetch,
            competitions={"SP1": Competition("SP1", "La Liga", teams=4)},
        )


# --- the snapshot shipped in a package ---


def test_the_shipped_snapshot_is_copied_when_the_user_has_none(live_dir, tmp_path):
    target = tmp_path / "user" / "live"

    assert copy_bundled_live(live_dir, target) is True
    assert read_manifest(target) == read_manifest(live_dir)


def test_a_newer_download_of_the_user_is_kept(live_dir, tmp_path):
    target = tmp_path / "user" / "live"
    copy_bundled_live(live_dir, target)
    manifest = read_manifest(target)
    manifest["updated_at"] = "2099-01-01T00:00:00+00:00"
    (target / MANIFEST).write_text(json.dumps(manifest), encoding="utf-8")

    assert copy_bundled_live(live_dir, target) is False
    assert read_manifest(target)["updated_at"] == "2099-01-01T00:00:00+00:00"


def test_an_older_or_damaged_copy_is_replaced(live_dir, tmp_path):
    target = tmp_path / "user" / "live"
    target.mkdir(parents=True)
    (target / MANIFEST).write_text("not json", encoding="utf-8")

    assert copy_bundled_live(live_dir, target) is True
    assert read_manifest(target) == read_manifest(live_dir)


def test_nothing_is_copied_from_the_source_folder_or_without_a_snapshot(live_dir, tmp_path):
    assert copy_bundled_live(live_dir, live_dir) is False
    assert copy_bundled_live(tmp_path / "missing", tmp_path / "user") is False
    assert not (tmp_path / "user").exists()


# --- the command ---


def test_the_update_command_prints_what_it_downloaded(
    tmp_path, fake_fetch, four_team_league, monkeypatch, capsys
):
    def update(target):
        return update_live_data(
            target, ("SP1",), today=LIVE_TODAY, fetch=fake_fetch, competitions=four_team_league
        )

    monkeypatch.setattr(update_command, "update_live_data", update)

    assert update_command.main(tmp_path / "live") == 0
    printed = capsys.readouterr().out
    assert printed.startswith("Season 2008-09, downloaded ")
    assert "  SP1: 7 matches played, 5 to play\n" in printed
    assert read_manifest(tmp_path / "live")["season"] == LIVE_SEASON


def test_a_failed_update_command_says_the_data_is_kept(tmp_path, monkeypatch, capsys):
    def update(target):
        raise urllib.error.URLError("network down")

    monkeypatch.setattr(update_command, "update_live_data", update)

    assert update_command.main(tmp_path / "live") == 1
    assert "Update failed, the previous data is kept" in capsys.readouterr().err
