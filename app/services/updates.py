"""The update of the season in progress, as the interface starts it and describes it in Romanian."""

from pathlib import Path

from app.data.competitions import competition
from app.data.live import UpdateSummary, update_live_data
from app.data.paths import LIVE_DIR
from app.services.formatting import quantity, season_text


def update_season(target: Path = LIVE_DIR) -> UpdateSummary:
    """Download the season in progress of every league (network; a few seconds)."""
    return update_live_data(target)


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
