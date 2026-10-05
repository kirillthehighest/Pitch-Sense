"""The charts draw exactly the results they are given, and render without warnings."""

from datetime import date
from io import BytesIO

import numpy as np
import pytest
from matplotlib.backend_bases import ResizeEvent
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import to_rgba
from matplotlib.figure import Figure
from matplotlib.text import Text

from app.algorithms.poisson import score_distribution
from app.evaluation.leagues import LeagueCharacter, LeagueResults
from app.evaluation.metrics import CalibrationBin
from app.services.teams import GROUP_NAMES, GroupCentre, GroupPoint, RatingSeason, SeasonGroups
from app.visualization.charts import (
    _tick_labels,
    calibration_chart,
    confusion_chart,
    elo_history_chart,
    home_advantage_chart,
    score_heatmap,
    skill_chart,
    team_groups_chart,
)
from app.visualization.palette import (
    BASELINE_COLOUR,
    GOLD,
    GROUP_COLOURS,
    MODEL_COLOURS,
    SURFACE,
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
    assert axes.lines[1].get_color() == GOLD
    assert axes.lines[1].get_linewidth() > axes.lines[0].get_linewidth()
    assert legend_texts(axes) == ["2007/08"]
    assert "Alpha" in axes.get_title("left")
    render(figure)


def test_elo_history_without_a_chosen_season_has_no_legend():
    axes = elo_history_chart("Alpha", HISTORY).axes[0]

    assert axes.get_legend() is None
    assert GOLD not in {line.get_color() for line in axes.lines}


def test_elo_history_can_mark_a_date():
    axes = elo_history_chart("Alpha", HISTORY, "2007-08", marked_date=date(2007, 9, 5)).axes[0]

    marker = axes.lines[-1]
    assert list(marker.get_xdata()) == [date(2007, 9, 5)] * 2
    assert legend_texts(axes) == ["2007/08", "Meciuri până la 05.09.2007"]


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
    assert cell.get_text() == f"{probabilities[1, 0]:.1%}".replace(".", ",")
    assert axes.get_xlabel() == "Goluri Bravo (oaspeți)"
    assert axes.get_ylabel() == "Goluri Alpha (gazde)"
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
    assert legend_texts(axes) == ["Calibrare perfectă", "Elo", "Poisson"]
    assert (elo.get_color(), poisson.get_color()) == (
        MODEL_COLOURS["Elo"],
        MODEL_COLOURS["Poisson"],
    )
    assert "2 intervale" in axes.get_title("left")
    render(figure)


def test_the_reference_is_grey_and_dashed_and_the_models_solid():
    tables = {
        "Elo": [calibration_bin(0.0, 10, 0.3, 0.25)],
        "Past frequencies": [calibration_bin(0.0, 10, 0.35, 0.3)],
    }

    _, elo, reference = calibration_chart(tables).axes[0].lines

    assert (elo.get_color(), elo.get_linestyle()) == (MODEL_COLOURS["Elo"], "-")
    assert (reference.get_color(), reference.get_linestyle()) == (BASELINE_COLOUR, "--")
    assert reference.get_label() == "Frecvențele trecute"


def test_charts_are_dark_like_the_interface():
    figure = calibration_chart({"Elo": [calibration_bin(0.0, 10, 0.3, 0.25)]})

    assert to_rgba(figure.get_facecolor()) == to_rgba(SURFACE)
    assert to_rgba(figure.axes[0].get_facecolor()) == to_rgba(SURFACE)
    axes = figure.axes[0]
    title = next(
        child
        for child in axes.get_children()
        if isinstance(child, Text) and child.get_text() == axes.get_title("left")
    )
    assert title.get_fontfamily() == ["Barlow Condensed"]


def test_heatmap_numbers_stay_readable_on_light_and_dark_cells():
    probabilities = score_distribution(1.5, 1.0).probabilities
    axes = score_heatmap("Alpha", "Bravo", probabilities).axes[0]

    colours = {text.get_text(): text.get_color() for text in axes.texts}
    most_likely = f"{probabilities[:7, :7].max():.1%}".replace(".", ",")
    assert colours[most_likely] != colours["0,0%"]  # dark ink on the lightest cell


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
    labels = ["Victorie gazde", "Egal", "Victorie oaspeți"]
    assert [label.get_text() for label in axes.get_xticklabels()] == labels
    assert [label.get_text() for label in axes.get_yticklabels()] == labels
    assert (axes.get_xlabel(), axes.get_ylabel()) == ("Prezis", "Real")
    assert axes.get_title("left") == "Elo: matricea de confuzie"
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
    assert tuple(by_label[GROUP_NAMES[0]].get_facecolor()[0]) == to_rgba(GROUP_COLOURS[0])
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
        "Centrul grupului (toate sezoanele)",
    ]
    assert "2006/07" in axes.get_title("left")
    render(figure)


CROWDED = SeasonGroups(
    season="2006-07",
    teams=(
        GroupPoint("Alpha", 1.500, 1.200, 1),
        GroupPoint("Bravo", 1.505, 1.205, 1),
        GroupPoint("Charlie", 1.510, 1.195, 2),
        GroupPoint("Delta", 1.495, 1.200, 2),
        GroupPoint("Echo", 2.400, 0.800, 0),
    ),
    centres=GROUPS.centres,
)


def assert_names_apart_and_inside(figure):
    figure.draw_without_rendering()
    axes = figure.axes[0]
    boxes = [text.get_window_extent() for text in axes.texts]
    assert not any(a.overlaps(b) for i, a in enumerate(boxes) for b in boxes[i + 1 :])
    area = axes.get_window_extent()
    assert all(
        area.x0 <= b.x0 and b.x1 <= area.x1 and area.y0 <= b.y0 and b.y1 <= area.y1 for b in boxes
    )


def test_names_of_teams_that_sit_close_together_do_not_overlap():
    figure = team_groups_chart(CROWDED, team="Alpha")

    assert_names_apart_and_inside(figure)
    render(figure)


def test_names_are_placed_again_when_a_window_resizes_the_figure():
    # Six names in a row fit side by side at the default size but not in a small window.
    row = SeasonGroups(
        season="2006-07",
        teams=(
            *(
                GroupPoint(name, 1.0 + 0.06 * index, 1.2, 1)
                for index, name in enumerate(
                    ("Alpha", "Bravo", "Charlie", "Delta", "Foxtrot", "Golf")
                )
            ),
            GroupPoint("Echo", 2.4, 0.8, 0),
        ),
        centres=GROUPS.centres,
    )
    figure = team_groups_chart(row)
    canvas = FigureCanvasAgg(figure)  # a window gives the figure its own canvas

    figure.set_size_inches(3.5, 3.0)
    canvas.callbacks.process("resize_event", ResizeEvent("resize_event", canvas))

    assert_names_apart_and_inside(figure)


def test_team_groups_without_a_chosen_team_circle_nobody():
    axes = team_groups_chart(GROUPS).axes[0]

    assert "_chosen team" not in {collection.get_label() for collection in axes.collections}


def test_team_groups_need_teams():
    with pytest.raises(ValueError, match="at least one team"):
        team_groups_chart(SeasonGroups("2006-07", (), GROUPS.centres))


# --- leagues ---


def character(code, closed_doors=None, other_seasons=None):
    return LeagueCharacter(code, 380, 0.46, 0.26, 0.28, 2.6, 0.4, closed_doors, other_seasons)


def results(code, skills):
    models = ("Elo", "Poisson", "Logistic regression")
    return LeagueResults(code, character(code), (), dict(zip(models, skills, strict=True)), ())


def test_skill_chart_draws_one_bar_per_model_and_league_in_the_model_colours():
    leagues = [results("E0", (0.05, 0.04, 0.06)), results("SP1", (0.07, 0.05, 0.065))]

    figure = skill_chart(leagues)
    axes = figure.axes[0]

    bars = {container.get_label(): container for container in axes.containers}
    assert list(bars) == ["Elo", "Poisson", "Regresie logistică"]
    assert [bar.get_width() for bar in bars["Poisson"]] == [0.04, 0.05]
    assert (
        to_rgba(MODEL_COLOURS["Logistic regression"])
        == bars["Regresie logistică"][0].get_facecolor()
    )
    assert [label.get_text() for label in axes.get_yticklabels()] == ["Premier League", "La Liga"]
    assert BASELINE_COLOUR not in {bar.get_facecolor() for c in axes.containers for bar in c}
    assert [text.get_text() for text in figure.legends[0].get_texts()] == list(bars)
    render(figure)


def test_skill_chart_needs_a_league():
    with pytest.raises(ValueError, match="at least one league"):
        skill_chart([])


def test_home_advantage_chart_skips_leagues_without_the_closed_doors_season():
    characters = [character("E0", 0.38, 0.46), character("F1"), character("SP1", 0.43, 0.47)]

    figure = home_advantage_chart(characters)
    axes = figure.axes[0]

    with_fans, closed_doors = axes.collections
    np.testing.assert_array_equal(with_fans.get_offsets(), [[0.46, 0], [0.47, 1]])
    np.testing.assert_array_equal(closed_doors.get_offsets(), [[0.38, 0], [0.43, 1]])
    assert [label.get_text() for label in axes.get_yticklabels()] == ["Premier League", "La Liga"]
    assert [text.get_text() for text in figure.legends[0].get_texts()] == [
        "Celelalte sezoane",
        "2020/21",
    ]
    render(figure)


def test_home_advantage_chart_needs_a_league_with_the_closed_doors_season():
    with pytest.raises(ValueError, match="2020/21"):
        home_advantage_chart([character("F1")])


@pytest.mark.parametrize(
    ("low", "high", "scale", "suffix", "decimals"),
    [(0.7, 2.6, 1, "", 1), (0.0, 0.12, 100, "%", 0), (0.30, 0.34, 100, "%", 1)],
)
def test_tick_labels_are_exact_with_a_decimal_comma(low, high, scale, suffix, decimals):
    figure = Figure()
    axes = figure.add_subplot()
    axes.set_xlim(low, high)
    _tick_labels(axes.xaxis, scale, suffix)
    figure.draw_without_rendering()

    for location, label in zip(axes.get_xticks(), axes.get_xticklabels(), strict=True):
        text = label.get_text().removesuffix(suffix)
        assert "." not in text
        assert len(text.partition(",")[2]) == decimals
        assert float(text.replace(",", ".").replace("−", "-")) == pytest.approx(location * scale)
