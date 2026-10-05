"""Charts of computed results, as matplotlib figures.

Every function receives finished results and only draws them; nothing is calculated from the
data here (the only arithmetic is arranging labels). The figures are built with
``matplotlib.figure.Figure`` instead of pyplot, so no global plotting state is involved and the
same figure can be embedded in the GUI or saved to a file.
"""

import math
from collections.abc import Mapping, Sequence
from datetime import date

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.text import Annotation
from matplotlib.transforms import Bbox

from app.evaluation.metrics import CalibrationBin
from app.services.teams import GROUP_NAMES, RatingSeason, SeasonGroups

OUTCOME_LABELS = ("Home win", "Draw", "Away win")
MODEL_COLOURS = ("tab:blue", "tab:orange", "tab:green", "tab:purple", "tab:brown")
GROUP_COLOURS = {0: "tab:red", 1: "tab:blue", 2: "tab:green", 3: "tab:gray"}
HIGHLIGHT_COLOUR = "tab:red"
BACKGROUND_COLOUR = "tab:blue"
SHOWN_GOALS = 6
FIGURE_SIZE = (6.4, 4.8)
TEAM_MARKER_SIZE = 40  # points squared, as matplotlib's scatter sizes
CENTRE_MARKER_SIZE = 140
CHOSEN_MARKER_SIZE = 180
# Where a team's name may go, tried in order: offset from its point in points, and alignment.
LABEL_PLACES = (
    (4, 3, "left"),
    (4, -10, "left"),
    (-4, 3, "right"),
    (-4, -10, "right"),
    (4, 10, "left"),
    (-4, 10, "right"),
    (4, -17, "left"),
    (-4, -17, "right"),
    (0, 12, "center"),
    (0, -19, "center"),
    (4, 17, "left"),
    (-4, 17, "right"),
    (4, -24, "left"),
    (-4, -24, "right"),
)
LABEL_GAP = 2  # pixels kept free around each name
# How bad it is for a name to cover each kind of obstacle, or to leave the axes.
MARKER_CLASH, LABEL_CLASH, OUTSIDE_CLASH = 1, 4, 16


def elo_history_chart(
    team: str,
    history: Sequence[RatingSeason],
    season: str | None = None,
    marked_date: date | None = None,
) -> Figure:
    """A team's Elo rating before each of its matches, one line per season.

    Separate lines leave gaps for summer breaks and for seasons the team spent outside the
    league. ``season``, when given, is drawn highlighted; ``marked_date`` is a vertical line.
    """
    if not history:
        raise ValueError("need at least one season of ratings")
    figure, axes = _figure()
    for rating_season in history:
        chosen = rating_season.season == season
        axes.plot(
            rating_season.dates,
            rating_season.ratings,
            color=HIGHLIGHT_COLOUR if chosen else BACKGROUND_COLOUR,
            linewidth=2.2 if chosen else 1.2,
            label=rating_season.season if chosen else f"_{rating_season.season}",
        )
    if marked_date is not None:
        axes.axvline(
            marked_date,
            color="black",
            linestyle=":",
            linewidth=1.2,
            label=f"Matches before {marked_date.isoformat()}",
        )
    axes.set_title(f"{team}: Elo rating before each match")
    axes.set_xlabel("Date")
    axes.set_ylabel("Elo rating")
    axes.grid(alpha=0.3)
    if marked_date is not None or any(s.season == season for s in history):
        axes.legend(loc="best")
    return figure


def score_heatmap(
    home_team: str, away_team: str, probabilities: np.ndarray, shown_goals: int = SHOWN_GOALS
) -> Figure:
    """The Poisson probability of every score from 0-0 to ``shown_goals`` goals per side.

    ``probabilities[i, j]`` is the probability that the home team scores i and the away team j.
    """
    if probabilities.ndim != 2 or min(probabilities.shape) < shown_goals + 1:
        raise ValueError(
            f"need a score table of at least {shown_goals + 1}x{shown_goals + 1}, "
            f"got shape {probabilities.shape}"
        )
    shown = probabilities[: shown_goals + 1, : shown_goals + 1]
    figure, axes = _figure()
    axes.imshow(shown, cmap="Blues", vmin=0)
    for (home_goals, away_goals), probability in np.ndenumerate(shown):
        axes.text(
            away_goals,
            home_goals,
            f"{probability:.1%}",
            ha="center",
            va="center",
            fontsize=7,
            color="white" if probability > shown.max() / 2 else "black",
        )
    goals = range(shown_goals + 1)
    axes.set_xticks(goals)
    axes.set_yticks(goals)
    axes.set_title(f"Poisson: probability of each score (0-{shown_goals} goals shown)")
    axes.set_xlabel(f"{away_team} goals (away)")
    axes.set_ylabel(f"{home_team} goals (home)")
    return figure


def calibration_chart(tables: Mapping[str, Sequence[CalibrationBin]]) -> Figure:
    """Predicted probability against observed frequency for each model; empty bins are skipped.

    Points on the diagonal mean that "p%" happened p% of the time.
    """
    if not tables:
        raise ValueError("need at least one model's calibration table")
    figure, axes = _figure()
    axes.plot(
        [0, 1], [0, 1], linestyle="--", color="black", linewidth=1, label="Perfect calibration"
    )
    for index, (model, table) in enumerate(tables.items()):
        filled = [bin_ for bin_ in table if bin_.count]
        axes.plot(
            [bin_.mean_predicted for bin_ in filled],
            [bin_.observed_frequency for bin_ in filled],
            marker="o",
            color=MODEL_COLOURS[index % len(MODEL_COLOURS)],
            label=model,
        )
    bins = len(next(iter(tables.values())))
    axes.set_xlim(0, 1)
    axes.set_ylim(0, 1)
    axes.set_aspect("equal")
    axes.set_title(f"Calibration: all outcomes, {bins} bins")
    axes.set_xlabel("Predicted probability")
    axes.set_ylabel("Observed frequency")
    axes.grid(alpha=0.3)
    axes.legend(loc="upper left")
    return figure


def confusion_chart(model: str, matrix: np.ndarray) -> Figure:
    """Match counts by actual result (rows) and predicted result (columns)."""
    if matrix.shape != (3, 3):
        raise ValueError(f"a confusion matrix is 3x3, got shape {matrix.shape}")
    figure, axes = _figure()
    axes.imshow(matrix, cmap="Blues", vmin=0)
    for (actual, predicted), count in np.ndenumerate(matrix):
        axes.text(
            predicted,
            actual,
            str(count),
            ha="center",
            va="center",
            color="white" if count > matrix.max() / 2 else "black",
        )
    axes.set_xticks(range(3), labels=OUTCOME_LABELS)
    axes.set_yticks(range(3), labels=OUTCOME_LABELS)
    axes.set_title(f"{model}: confusion matrix")
    axes.set_xlabel("Predicted")
    axes.set_ylabel("Actual")
    return figure


def team_groups_chart(groups: SeasonGroups, team: str | None = None) -> Figure:
    """One season's teams by goals scored and conceded per match, coloured by K-Means group.

    The groups come from all six profile values, so a team can sit closer to another group's
    centre on these two axes. ``team``, when given, is circled.
    """
    if not groups.teams:
        raise ValueError("need at least one team")
    figure, axes = _figure()
    for group, name in GROUP_NAMES.items():
        members = [point for point in groups.teams if point.group == group]
        if members:
            axes.scatter(
                [point.goals_scored for point in members],
                [point.goals_conceded for point in members],
                color=GROUP_COLOURS[group],
                s=TEAM_MARKER_SIZE,
                label=name,
            )
    axes.scatter(
        [centre.goals_scored for centre in groups.centres],
        [centre.goals_conceded for centre in groups.centres],
        color=[GROUP_COLOURS[centre.group] for centre in groups.centres],
        marker="X",
        s=CENTRE_MARKER_SIZE,
        edgecolors="black",
        linewidths=0.8,
        label="_group centres",
    )
    markers = [
        (c.goals_scored, c.goals_conceded, CENTRE_MARKER_SIZE, LABEL_CLASH) for c in groups.centres
    ]
    labels = []
    for point in sorted(groups.teams, key=lambda p: p.team != team):  # the chosen team first
        chosen = point.team == team
        position = (point.goals_scored, point.goals_conceded)
        labels.append(
            axes.annotate(
                point.team,
                position,
                xytext=LABEL_PLACES[0][:2],
                textcoords="offset points",
                fontsize=9 if chosen else 7,
                fontweight="bold" if chosen else "normal",
            )
        )
        markers.append((*position, TEAM_MARKER_SIZE, MARKER_CLASH))
        if chosen:
            axes.scatter(
                *position,
                s=CHOSEN_MARKER_SIZE,
                facecolors="none",
                edgecolors="black",
                linewidths=1.5,
                label="_chosen team",
            )
            markers.append((*position, CHOSEN_MARKER_SIZE, MARKER_CLASH))
    handles, _ = axes.get_legend_handles_labels()
    centre_handle = Line2D(
        [], [], marker="X", linestyle="none", color="black", label="Group centre (all seasons)"
    )
    axes.legend(handles=[*handles, centre_handle], loc="best", fontsize=8)
    axes.set_title(f"Team groups in {groups.season} (K-Means on six season values)")
    axes.set_xlabel("Goals scored per match")
    axes.set_ylabel("Goals conceded per match")
    axes.grid(alpha=0.3)
    _place_labels(axes, labels, markers)
    # A window shows the figure at its own size; the names are placed again for every new size.
    figure.canvas.mpl_connect("resize_event", lambda _: _place_labels(axes, labels, markers))
    return figure


def _place_labels(
    axes: Axes,
    labels: Sequence[Annotation],
    markers: Sequence[tuple[float, float, float, int]],
) -> None:
    """Move each label to the first of LABEL_PLACES where it overlaps nothing placed so far.

    The obstacles are the markers (x, y, size in points squared, clash weight) other than the
    label's own, the legend and the labels already placed; a label must also stay inside the
    axes. A label that fits nowhere takes the place where the clashes weigh least (covering a
    team's marker is better than covering text or a group centre). Places depend on the figure's
    size, so they are found again whenever the figure is resized.
    """
    figure = axes.get_figure()
    for label in labels:
        label.set_in_layout(False)  # otherwise moving a label would resize the axes afterwards
    figure.draw_without_rendering()  # settles the layout, the axis limits and the legend
    pixels_per_point = figure.dpi / 72
    # (owner point or None, box, weight)
    obstacles: list[tuple[tuple[float, float] | None, Bbox, int]] = [
        (None, axes.get_legend().get_window_extent(), LABEL_CLASH)
    ]
    for x, y, size, weight in markers:
        centre_x, centre_y = axes.transData.transform((x, y))
        radius = math.sqrt(size) / 2 * pixels_per_point
        box = Bbox.from_extents(
            centre_x - radius, centre_y - radius, centre_x + radius, centre_y + radius
        )
        obstacles.append(((x, y), box, weight))
    area = axes.get_window_extent()
    for label in labels:
        best: tuple[int, tuple[float, float, str]] | None = None
        for place in LABEL_PLACES:
            _put(label, place)
            box = label.get_window_extent().padded(LABEL_GAP)
            clashes = sum(
                weight
                for owner, other, weight in obstacles
                if owner != label.xy and box.overlaps(other)
            ) + OUTSIDE_CLASH * (not _contains(area, box))
            if best is None or clashes < best[0]:
                best = (clashes, place)
            if clashes == 0:
                break
        _put(label, best[1])
        obstacles.append((None, label.get_window_extent(), LABEL_CLASH))


def _put(label: Annotation, place: tuple[float, float, str]) -> None:
    *offset, alignment = place
    label.xyann = tuple(offset)
    label.set_horizontalalignment(alignment)


def _contains(outer: Bbox, inner: Bbox) -> bool:
    return (
        outer.x0 <= inner.x0
        and inner.x1 <= outer.x1
        and outer.y0 <= inner.y0
        and inner.y1 <= outer.y1
    )


def _figure() -> tuple[Figure, Axes]:
    figure = Figure(figsize=FIGURE_SIZE, layout="constrained")
    return figure, figure.add_subplot()
