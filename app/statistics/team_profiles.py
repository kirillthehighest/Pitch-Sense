"""Statistical profiles of teams over a whole season, the points that K-Means groups.

A profile describes a completed season, so it is descriptive: it may only describe that season
or serve as information for later seasons, never as input for predicting matches of the same
season.
"""

from dataclasses import dataclass
from datetime import date, timedelta

from app.statistics.team_statistics import (
    MatchHistory,
    Venue,
    team_match_statistics,
    team_statistics,
)

PROFILE_FEATURES = (
    "goals_scored_per_match",
    "goals_conceded_per_match",
    "shots_on_target_per_match",
    "shots_on_target_conceded_per_match",
    "points_per_match",
    "home_minus_away_points_per_match",
)


@dataclass(frozen=True, slots=True)
class TeamSeasonProfile:
    """One team's profile over one season, in the order of PROFILE_FEATURES."""

    team: str
    season: str
    matches: int
    values: tuple[float, ...]


def seasons_in(history: MatchHistory) -> list[str]:
    """Return the season labels of a history in chronological order."""
    return sorted({match.season for match in history.league_matches_before(date.max)})


def season_profiles(history: MatchHistory, season: str) -> list[TeamSeasonProfile]:
    """Return the profile of every team over all matches of ``season``, sorted by team.

    Every team must have recorded shot statistics, because two of the features need them.
    """
    season_matches = history.league_matches_before(date.max, season=season)
    if not season_matches:
        raise ValueError(f"no matches in season {season!r}")
    after_season = season_matches[-1].match_date + timedelta(days=1)
    teams = sorted({team for m in season_matches for team in (m.home_team, m.away_team)})
    return [_profile(history, team, season, after_season) for team in teams]


def _profile(history: MatchHistory, team: str, season: str, after: date) -> TeamSeasonProfile:
    record = team_statistics(history, team, after, season=season)
    home = team_statistics(history, team, after, season=season, venue=Venue.HOME)
    away = team_statistics(history, team, after, season=season, venue=Venue.AWAY)
    shots = team_match_statistics(history, team, after, season=season)
    if shots.matches_with_statistics == 0:
        raise ValueError(f"{team} has no shot statistics in season {season}")
    if not home.played or not away.played:
        raise ValueError(f"{team} needs home and away matches in season {season}")
    return TeamSeasonProfile(
        team=team,
        season=season,
        matches=record.played,
        values=(
            record.goals_for_per_match,
            record.goals_against_per_match,
            shots.shots_on_target,
            shots.opponent_shots_on_target,
            record.points_per_match,
            home.points_per_match - away.points_per_match,
        ),
    )
