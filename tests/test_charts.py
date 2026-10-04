"""The charts draw exactly the results they are given, and render without warnings."""

from datetime import date
from io import BytesIO

import numpy as np
import pytest

from app.algorithms.poisson import score_distribution
from app.evaluation.metrics import CalibrationBin
from app.services.teams import GROUP_NAMES, GroupCentre, GroupPoint, RatingSeason, SeasonGroups
from app.visualization.charts import (
    HIGHLIGHT_COLOUR,
    calibration_chart,
    confusion_chart,
    elo_history_chart,
    score_heatmap,
    team_groups_chart,
)


def render(figure):
    figure.savefig(BytesIO(), format="png")


def legend_texts(axes):
    return [text.get_text() for text in axes.get_legend().get_texts()]


# --- Elo history ---

HISTORY = (
    RatingSeason("2006-07", (date(2006, 9, 1), date(2006, 9, 8)), (1500.0, 1507.5)),
    RatingSeason("2007-08", (date(2007, 9, 2), date(2007, 9, 9)), (1510.0, 1498.0)),
)


def test_elo_history_draws_one_line_per_season_and_highlights_the_chosen_one():
    figure = elo_history_chart("Alpha", HISTORY, season="2007-08")
    axes = figure.axes[0]

    assert len(axes.lines) == 2
    for line, season in zip(axes.lines, HISTORY, strict=True):
        assert list(line.get_xdata()) == list(season.dates)
        assert list(line.get_ydata()) == list(season.ratings)
    assert axes.lines[1].get_color() == HIGHLIGHT_COLOUR
    assert axes.lines[1].get_linewidth() > axes.lines[0].get_linewidth()
    assert legend_texts(axes) == ["2007-08"]
    assert "Alpha" in axes.get_title()
    render(figure)


def test_elo_history_without_a_chosen_season_has_no_legend():
    axes = elo_history_chart("Alpha", HISTORY).axes[0]

    assert axes.get_legend() is None
    assert HIGHLIGHT_COLOUR not in {line.get_color() for line in axes.lines}


def test_elo_history_can_mark_a_date():
    axes = elo_history_chart("Alpha", HISTORY, "2007-08", marked_date=date(2007, 9, 5)).axes[0]

    marker = axes.lines[-1]
    assert list(marker.get_xdata()) == [date(2007, 9, 5)] * 2
    assert legend_texts(axes) == ["2007-08", "Matches before 2007-09-05"]


def test_elo_history_needs_ratings():
    with pytest.raises(ValueError, match="at least one season"):
        elo_history_chart("Alpha", ())


# --- score heatmap ---


def test_score_heatmap_shows_the_table_up_to_six_goals_with_percentages():
    probabilities = score_distribution(1.5, 1.0).probabilities

    figure = score_heatmap("Alpha", "Bravo", probabilities)
    axes = figure.axes[0]

    np.testing.assert_array_equal(axes.images[0].get_array(), probabilities[:7, :7])
    assert len(axes.texts) == 49
    cell = next(text for text in axes.texts if text.get_position() == (0, 1))  # 1-0
    assert cell.get_text() == f"{probabilities[1, 0]:.1%}"
    assert axes.get_xlabel().startswith("Bravo")
    assert axes.get_ylabel().startswith("Alpha")
    render(figure)


def test_score_heatmap_needs_a_large_enough_table():
    with pytest.raises(ValueError, match="at least 7x7"):
        score_heatmap("Alpha", "Bravo", np.full((3, 3), 1 / 9))


# --- calibration ---


def calibration_bin(lower, count, predicted=None, observed=None):
    return CalibrationBin(lower, lower + 0.5, count, predicted, observed)


def test_calibration_draws_the_diagonal_and_every_model_without_empty_bins():
    tables = {
        "Elo": [calibration_bin(0.0, 10, 0.3, 0.25), calibration_bin(0.5, 4, 0.7, 0.75)],
        "Poisson": [calibration_bin(0.0, 14, 0.4, 0.35), calibration_bin(0.5, 0)],
    }

    figure = calibration_chart(tables)
    axes = figure.axes[0]

    diagonal, elo, poisson = axes.lines
    assert list(diagonal.get_xdata()) == list(diagonal.get_ydata()) == [0, 1]
    assert (list(elo.get_xdata()), list(elo.get_ydata())) == ([0.3, 0.7], [0.25, 0.75])
    assert (list(poisson.get_xdata()), list(poisson.get_ydata())) == ([0.4], [0.35])
    assert legend_texts(axes) == ["Perfect calibration", "Elo", "Poisson"]
    assert "2 bins" in axes.get_title()
    render(figure)


def test_calibration_needs_a_model():
    with pytest.raises(ValueError, match="at least one model"):
        calibration_chart({})


# --- confusion matrix ---


def test_confusion_chart_shows_every_count_with_outcome_labels():
    matrix = np.array([[50, 10, 5], [20, 8, 7], [10, 5, 30]])

    figure = confusion_chart("Elo", matrix)
    axes = figure.axes[0]

    np.testing.assert_array_equal(axes.images[0].get_array(), matrix)
    assert [text.get_text() for text in axes.texts] == [str(count) for count in matrix.ravel()]
    labels = ["Home win", "Draw", "Away win"]
    assert [label.get_text() for label in axes.get_xticklabels()] == labels
    assert [label.get_text() for label in axes.get_yticklabels()] == labels
    assert (axes.get_xlabel(), axes.get_ylabel()) == ("Predicted", "Actual")
    render(figure)


def test_confusion_chart_needs_a_three_by_three_matrix():
    with pytest.raises(ValueError, match="3x3"):
        confusion_chart("Elo", np.zeros((2, 2)))


# --- team groups ---

GROUPS = SeasonGroups(
    season="2006-07",
    teams=(
        GroupPoint("Alpha", 2.1, 0.8, 0),
        GroupPoint("Bravo", 1.6, 1.1, 1),
        GroupPoint("Charlie", 1.5, 1.2, 1),
        GroupPoint("Delta", 1.0, 1.4, 2),
    ),
    centres=tuple(GroupCentre(group, 2.0 - 0.3 * group, 0.9 + 0.2 * group) for group in range(4)),
)


def test_team_groups_colour_teams_by_group_and_mark_the_centres():
    figure = team_groups_chart(GROUPS, team="Bravo")
    axes = figure.axes[0]

    by_label = {collection.get_label(): collection for collection in axes.collections}
    np.testing.assert_array_equal(by_label[GROUP_NAMES[1]].get_offsets(), [[1.6, 1.1], [1.5, 1.2]])
    assert GROUP_NAMES[3] not in by_label  # no team of that group this season
    np.testing.assert_array_equal(
        by_label["_group centres"].get_offsets(),
        [[centre.goals_scored, centre.goals_conceded] for centre in GROUPS.centres],
    )
    np.testing.assert_array_equal(by_label["_chosen team"].get_offsets(), [[1.6, 1.1]])
    names = {text.get_text(): text for text in axes.texts}
    assert set(names) == {"Alpha", "Bravo", "Charlie", "Delta"}
    assert names["Bravo"].get_fontweight() == "bold"
    assert legend_texts(axes) == [
        *(GROUP_NAMES[group] for group in (0, 1, 2)),
        "Group centre (all seasons)",
    ]
    assert "2006-07" in axes.get_title()
    render(figure)


def test_team_groups_without_a_chosen_team_circle_nobody():
    axes = team_groups_chart(GROUPS).axes[0]

    assert "_chosen team" not in {collection.get_label() for collection in axes.collections}


def test_team_groups_need_teams():
    with pytest.raises(ValueError, match="at least one team"):
        team_groups_chart(SeasonGroups("2006-07", (), GROUPS.centres))
