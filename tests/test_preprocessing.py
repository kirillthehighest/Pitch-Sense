from dataclasses import replace
from datetime import date, time

import pandas as pd
import pytest

from app.data.models import Match, MatchStatistics, Outcome
from app.data.preprocessing import (
    STATISTICS_COLUMNS,
    DataValidationError,
    in_progress_season_problems,
    local_kickoff,
    matches_from_frame,
    parse_match_date,
    parse_season_label,
    season_date_window,
    season_of,
    season_structure_problems,
    sort_chronologically,
)


def parse(rows: list[dict[str, str]], season: str = "2006-07") -> list[Match]:
    return matches_from_frame(pd.DataFrame(rows, dtype=str), season, source="test.csv")


def make_match(match_date: date, home_team: str, kickoff_time: time | None = None) -> Match:
    return Match(
        competition="SP1",
        season="2006-07",
        match_date=match_date,
        home_team=home_team,
        away_team="Opponent",
        home_goals=1,
        away_goals=0,
        result=Outcome.HOME_WIN,
        kickoff_time=kickoff_time,
    )


# --- dates and season labels ---


def test_parse_match_date_accepts_two_and_four_digit_years():
    assert parse_match_date("27/08/06") == date(2006, 8, 27)
    assert parse_match_date("18/08/2018") == date(2018, 8, 18)


@pytest.mark.parametrize("text", ["2006-08-27", "31/02/2020", "08/27/06", ""])
def test_parse_match_date_rejects_other_formats(text):
    with pytest.raises(DataValidationError):
        parse_match_date(text)


def test_parse_season_label():
    assert parse_season_label("2006-07") == (2006, 2007)
    assert parse_season_label("1999-00") == (1999, 2000)


@pytest.mark.parametrize("label", ["2006-08", "2006/07", "06-07", "2006-7", "season"])
def test_parse_season_label_rejects_malformed_labels(label):
    with pytest.raises(DataValidationError):
        parse_season_label(label)


def test_season_window_covers_seasons_that_finished_in_july_or_august():
    # La Liga 2019/20 ended in July 2020, Serie A 2019/20 on 2 August 2020 (COVID-19).
    assert season_date_window("2019-20") == (date(2019, 7, 1), date(2020, 8, 31))


# --- converting rows ---


def test_valid_rows_become_matches(raw_season_rows):
    matches = parse(raw_season_rows)

    assert len(matches) == 12
    assert matches[0] == Match(
        competition="SP1",
        season="2006-07",
        match_date=date(2006, 9, 1),
        home_team="Alpha",
        away_team="Bravo",
        home_goals=0,
        away_goals=1,
        result=Outcome.AWAY_WIN,
        kickoff_time=None,
        statistics=MatchStatistics(*[0] * 12),
    )


def test_kickoff_time_is_read_in_the_league_s_own_time(raw_season_rows):
    # Football-Data writes UK time: La Liga's 20:00 is 21:00 in Spain
    for row in raw_season_rows:
        row["Time"] = "20:00"
    raw_season_rows[1]["Time"] = ""

    matches = parse(raw_season_rows)

    assert matches[0].kickoff_time == time(21, 0)
    assert matches[1].kickoff_time is None


def test_premier_league_kickoffs_stay_as_written(raw_season_rows):
    for row in raw_season_rows:
        row["Div"], row["Time"] = "E0", "15:00"

    assert parse(raw_season_rows)[0].kickoff_time == time(15, 0)


@pytest.mark.parametrize(
    ("uk_time", "hours", "local"),
    [
        (time(20, 0), 1, time(21, 0)),
        (time(12, 30), 0, time(12, 30)),
        (time(22, 59), 1, time(23, 59)),
    ],
)
def test_a_uk_kickoff_in_local_time(uk_time, hours, local):
    assert local_kickoff(uk_time, hours) == local


def test_a_kickoff_after_local_midnight_is_refused():
    with pytest.raises(DataValidationError, match="after midnight"):
        local_kickoff(time(23, 30), 1)


def test_statistics_are_optional(raw_season_rows):
    for row in raw_season_rows:
        for column in STATISTICS_COLUMNS:
            del row[column]

    matches = parse(raw_season_rows)

    assert len(matches) == 12
    assert all(match.statistics is None for match in matches)


def test_a_blank_statistic_drops_only_that_matchs_statistics(raw_season_rows):
    raw_season_rows[3]["HC"] = ""

    matches = parse(raw_season_rows)

    assert matches[3].statistics is None
    assert matches[4].statistics is not None


def test_team_names_are_stripped(raw_season_rows):
    raw_season_rows[0]["HomeTeam"] = "  Alpha "

    assert parse(raw_season_rows)[0].home_team == "Alpha"


def test_blank_rows_are_ignored(raw_season_rows):
    raw_season_rows.append(dict.fromkeys(raw_season_rows[0], ""))

    assert len(parse(raw_season_rows)) == 12


def test_missing_required_column_is_reported(raw_season_rows):
    for row in raw_season_rows:
        del row["FTR"]

    with pytest.raises(DataValidationError, match="missing required columns: FTR"):
        parse(raw_season_rows)


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("FTHG", "-1"),
        ("FTHG", "1.5"),
        ("FTR", "X"),
        ("FTR", "H"),  # row 4 ends 1-1, so H contradicts the score
        ("HomeTeam", ""),
        ("AwayTeam", "Bravo"),  # row 4 is hosted by Bravo
        ("Date", "2006-09-05"),
        ("Date", "05/09/05"),  # outside the 2006-07 season
        ("HS", "-2"),
    ],
)
def test_invalid_row_is_reported_with_its_line_number(raw_season_rows, column, value):
    raw_season_rows[4][column] = value

    with pytest.raises(DataValidationError, match="line 6"):
        parse(raw_season_rows)


def test_all_invalid_rows_are_reported_together(raw_season_rows):
    raw_season_rows[0]["FTR"] = "X"
    raw_season_rows[7]["FTAG"] = ""

    with pytest.raises(DataValidationError) as error:
        parse(raw_season_rows)

    assert "2 problem(s)" in str(error.value)
    assert "line 2" in str(error.value)
    assert "line 9" in str(error.value)


def test_duplicate_match_is_rejected(raw_season_rows):
    raw_season_rows.append(dict(raw_season_rows[0]))

    with pytest.raises(DataValidationError, match="duplicate match: Alpha vs Bravo"):
        parse(raw_season_rows)


def test_rows_from_different_competitions_are_rejected(raw_season_rows):
    raw_season_rows[0]["Div"] = "E0"

    with pytest.raises(DataValidationError, match="mix competitions"):
        parse(raw_season_rows)


# --- season structure ---


def test_complete_double_round_robin_has_no_problems(raw_season_rows):
    assert season_structure_problems(parse(raw_season_rows), team_count=4) == []


def test_missing_match_is_detected(raw_season_rows):
    problems = season_structure_problems(parse(raw_season_rows)[:-1], team_count=4)

    assert "expected 12 matches, found 11" in problems
    assert "Delta played 5 matches, expected 6" in problems


def test_wrong_number_of_teams_is_detected(raw_season_rows):
    problems = season_structure_problems(parse(raw_season_rows), team_count=20)

    assert "expected 20 teams, found 4" in problems


def test_repeated_fixture_is_detected(raw_season_rows):
    raw_season_rows[-1].update(HomeTeam="Alpha", AwayTeam="Bravo", FTHG="1", FTAG="0", FTR="H")

    problems = season_structure_problems(parse(raw_season_rows), team_count=4)

    assert "Alpha hosted Bravo 2 times" in problems


def test_a_season_stopped_early_needs_exactly_the_matches_played(raw_season_rows):
    played = parse(raw_season_rows)[:-2]

    assert season_structure_problems(played, team_count=4, stopped_after=10) == []
    assert season_structure_problems(played[:-1], team_count=4, stopped_after=10) == [
        "expected 10 matches, found 9"
    ]


def test_a_season_stopped_early_still_rejects_repeated_fixtures(raw_season_rows):
    raw_season_rows[-3].update(HomeTeam="Alpha", AwayTeam="Bravo", FTHG="1", FTAG="0", FTR="H")

    problems = season_structure_problems(
        parse(raw_season_rows)[:-2], team_count=4, stopped_after=10
    )

    assert "Alpha hosted Bravo 2 times" in problems


def test_team_count_must_allow_a_match():
    with pytest.raises(ValueError):
        season_structure_problems([], team_count=1)


# --- the season in progress ---


def test_a_season_in_progress_may_have_any_matches_so_far(raw_season_rows):
    assert in_progress_season_problems(parse(raw_season_rows)[:5], team_count=4) == []
    assert in_progress_season_problems([], team_count=20) == []
    assert in_progress_season_problems(parse(raw_season_rows), team_count=4) == []


def test_a_season_in_progress_cannot_go_beyond_a_double_round_robin(raw_season_rows):
    matches = parse(raw_season_rows)

    assert in_progress_season_problems(matches, team_count=3) == [
        "expected at most 3 teams, found 4",
        "Alpha played 6 matches, more than a season (4)",
        "Bravo played 6 matches, more than a season (4)",
        "Charlie played 6 matches, more than a season (4)",
        "Delta played 6 matches, more than a season (4)",
    ]


def test_a_season_in_progress_rejects_repeated_fixtures_and_mixed_seasons(raw_season_rows):
    raw_season_rows[5].update(HomeTeam="Alpha", AwayTeam="Bravo")
    matches = parse(raw_season_rows[:6])
    later = replace(make_match(date(2007, 9, 1), "Alpha"), season="2007-08")

    assert in_progress_season_problems(matches, team_count=4) == ["Alpha hosted Bravo 2 times"]
    assert in_progress_season_problems([*matches[:2], later], team_count=4) == [
        "matches come from several seasons: 2006-07, 2007-08"
    ]


def test_a_season_in_progress_needs_a_league_of_two_teams():
    with pytest.raises(ValueError):
        in_progress_season_problems([], team_count=1)


@pytest.mark.parametrize(
    ("day", "season"),
    [
        (date(2026, 10, 15), "2026-27"),
        (date(2026, 7, 1), "2026-27"),
        (date(2026, 6, 30), "2025-26"),
        (date(2027, 3, 1), "2026-27"),
        (date(1999, 8, 1), "1999-00"),
    ],
)
def test_seasons_start_on_the_first_of_july(day, season):
    assert season_of(day) == season


# --- ordering ---


def test_sort_orders_by_date_then_kickoff_then_home_team():
    same_day = date(2020, 9, 12)
    evening = make_match(same_day, "Zeta", time(21, 0))
    unknown_time = make_match(same_day, "Beta")
    afternoon = make_match(same_day, "Alpha", time(16, 0))
    day_before = make_match(date(2020, 9, 11), "Omega", time(21, 0))

    ordered = sort_chronologically([evening, unknown_time, afternoon, day_before])

    assert ordered == [day_before, unknown_time, afternoon, evening]
    assert sort_chronologically(reversed(ordered)) == ordered
