"""The update of the season in progress, as the window starts it and describes it in Romanian."""

from datetime import datetime
from pathlib import Path

from app.data.competitions import competition
from app.data.live import UpdateSummary, update_live_data
from app.data.paths import LIVE_DIR
from app.services.formatting import date_text, quantity, season_text


def update_season(target: Path = LIVE_DIR) -> UpdateSummary:
    """Download the season in progress of every league (network; a few seconds)."""
    return update_live_data(target)


def updated_text(updated_at: datetime) -> str:
    """When the data was downloaded, in the computer's time zone: 15.10.2026, 16:01."""
    local = updated_at.astimezone()
    return f"{date_text(local.date())}, {local:%H:%M}"


def summary_text(summary: UpdateSummary) -> str:
    """What an update brought, in one or two sentences."""
    played = sum(len(league.matches) for league in summary.leagues)
    fixtures = sum(len(league.fixtures) for league in summary.leagues)
    text = (
        f"Sezonul {season_text(summary.season)}: "
        f"{quantity(played, 'meci jucat', 'meciuri jucate')} și "
        f"{quantity(fixtures, 'meci programat', 'meciuri programate')} în "
        f"{quantity(len(summary.leagues), 'ligă', 'ligi')}."
    )
    unmatched = [
        f"{competition(league.competition).name} ({', '.join(league.unmatched_teams)})"
        for league in summary.leagues
        if league.unmatched_teams
    ]
    if unmatched:
        text += (
            " Echipe din calendar care nu au putut fi recunoscute, cu meciurile lor lăsate "
            f"deoparte: {'; '.join(unmatched)}."
        )
    return text


def unmatched_text(teams: tuple[str, ...]) -> str:
    """Why some scheduled matches are missing from a league."""
    return (
        "Meciurile programate ale acestor echipe lipsesc, pentru că numele lor din calendar nu au "
        f"putut fi potrivite cu siguranță: {', '.join(teams)}."
    )
