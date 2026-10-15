"""Charts of computed results, as matplotlib figures, in Romanian and in the PitchSense style.

Every function receives finished results and only draws them; nothing is calculated from the
data here (the only arithmetic is arranging labels). The figures are built with
``matplotlib.figure.Figure`` instead of pyplot, so no global plotting state is involved and the
same figure can be embedded in the GUI or saved to a file.

Style (``docs/brand.md``): dark cards like the rest of the interface, titles in the condensed
Barlow Condensed and text in Libre Franklin, light text, solid hairline grids, 2-pixel lines,
markers ringed in the card colour, a 2-pixel gap between heatmap cells, decimal commas. Colours do
one job each (``palette.py``): a model always has the same colour (the reference is grey and
dashed), the ordered K-Means groups go from bright (strongest) to deep blue, magnitudes use one
blue from the card's dark to light, and gold marks the one highlighted thing (the chosen season,
the chosen team).
"""

import math
from collections.abc import Callable, Mapping, Sequence
from datetime import date
from functools import cache, wraps

import numpy as np
from matplotlib import font_manager, rc_context
from matplotlib.axes import Axes
from matplotlib.axis import Axis
from matplotlib.colors import LinearSegmentedColormap, to_rgba, to_rgba_array
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.text import Annotation
from matplotlib.ticker import FuncFormatter, MaxNLocator
from matplotlib.transforms import Bbox

from app.data.competitions import COMPETITIONS
from app.data.paths import ASSETS_DIR
from app.evaluation.comparison import COMPARED_MODELS
from app.evaluation.leagues import LeagueCharacter, LeagueResults
from app.evaluation.metrics import CalibrationBin
from app.services.formatting import date_text, integer, number, percent, season_text
from app.services.labels import OUTCOME_LABELS, model_label
from app.services.teams import GROUP_NAMES, RatingSeason, SeasonGroups
from app.visualization.palette import (
    BACKGROUND,
    BASELINE_COLOUR,
    CLOSED_DOORS,
    GOLD,
    GRID,
    GROUP_COLOURS,
    LINE,
    MODEL_COLOURS,
    MUTED,
    SEQUENTIAL,
    SURFACE,
    TEXT,
    WITH_FANS,
)

FONT_FAMILY = "Libre Franklin"
DISPLAY_FAMILY = "Barlow Condensed"
SHOWN_GOALS = 6
FIGURE_SIZE = (6.4, 4.8)
ELO_COLOUR = MODEL_COLOURS["Elo"]
SEQUENTIAL_MAP = LinearSegmentedColormap.from_list("pitchsense-blue", SEQUENTIAL)
TEAM_MARKER_SIZE = 46  # points squared, as matplotlib's scatter sizes
CENTRE_MARKER_SIZE = 150
CHOSEN_MARKER_SIZE = 230
OUTCOME_ORDER = ("H", "D", "A")
# Where a team's name may go, tried in order: the offset of its baseline from its point (across
# in points, up in lines of the name's own height, so the places suit any typeface) and alignment.
LABEL_PLACES = (
    (4, 0.4, "left"),
    (4, -1.4, "left"),
    (-4, 0.4, "right"),
    (-4, -1.4, "right"),
    (4, 1.4, "left"),
    (-4, 1.4, "right"),
    (4, -2.4, "left"),
    (-4, -2.4, "right"),
    (0, 1.7, "center"),
    (0, -2.6, "center"),
    (4, 2.4, "left"),
    (-4, 2.4, "right"),
    (4, -3.3, "left"),
    (-4, -3.3, "right"),
    (10, -0.5, "left"),
    (-10, -0.5, "right"),
    (4, 3.3, "left"),
    (-4, 3.3, "right"),
    (4, -4.2, "left"),
    (-4, -4.2, "right"),
)
LABEL_GAP = 2  # pixels kept free around each name
# How bad it is for a name to cover each kind of obstacle, or to leave the axes.
MARKER_CLASH, LABEL_CLASH, OUTSIDE_CLASH = 1, 4, 16

STYLE = {
    "font.family": FONT_FAMILY,
    "font.size": 9.5,
    "text.color": TEXT,
    "axes.edgecolor": LINE,
    "axes.linewidth": 0.8,
    "axes.labelcolor": MUTED,
    "axes.titlecolor": TEXT,
    "axes.titlesize": 11,
    "axes.titleweight": "semibold",
    "axes.titlelocation": "left",
    "axes.titlepad": 10,
    "axes.facecolor": SURFACE,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": SURFACE,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "grid.linestyle": "-",
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "xtick.labelcolor": MUTED,
    "ytick.labelcolor": MUTED,
    "legend.frameon": False,
    "legend.fontsize": 8.5,
    "lines.linewidth": 2,
    "lines.solid_capstyle": "round",
}


def on_surface(
    figure: Figure,
    colour: str,
    previous: str = SURFACE,
    highlight: str | None = None,
    previous_highlight: str = GOLD,
) -> Figure:
    """Show ``figure`` on a card of another colour: its background becomes transparent, and every
    ring, edge and gap drawn in ``previous`` (the card colour it was built for) takes ``colour``.
    With ``highlight``, what was drawn in ``previous_highlight`` (the chosen season or team, gold
    when built) takes it: the accent of the league on screen.

    Returns the same figure, changed in place.
    """
    changes = [(np.array(to_rgba(previous)), to_rgba(colour))]
    if highlight is not None:
        changes.append((np.array(to_rgba(previous_highlight)), to_rgba(highlight)))
    backgrounds = {id(figure.patch), *(id(axes.patch) for axes in figure.axes)}
    figure.patch.set_alpha(0.0)
    for axes in figure.axes:
        axes.patch.set_alpha(0.0)
    for artist in figure.findobj():
        if id(artist) in backgrounds:
            continue
        for name in ("edgecolor", "facecolor", "markeredgecolor", "color"):
            getter = getattr(artist, f"get_{name}", None)
            setter = getattr(artist, f"set_{name}", None)
            if getter is None or setter is None:
                continue
            try:
                colours = to_rgba_array(getter())
            except TypeError, ValueError:
                continue  # not a colour (a colour map, for instance)
            changed = False
            for old, new in changes:
                same = np.all(np.abs(colours - old) < 1 / 255, axis=1)
                if same.any():
                    colours[same] = new
                    changed = True
                    break  # one change per colour: a new colour is never changed again
            if changed:
                setter(new if len(colours) == 1 else colours)
    return figure


@cache
def register_fonts() -> None:
    """Make the bundled typefaces available to matplotlib (once)."""
    for path in sorted((ASSETS_DIR / "fonts").glob("*.ttf")):
        font_manager.fontManager.addfont(str(path))


def _branded[**P](build: Callable[P, Figure]) -> Callable[P, Figure]:
    """Build the figure inside the PitchSense style, without changing matplotlib's defaults."""

    @wraps(build)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Figure:
        register_fonts()
        with rc_context(STYLE):
            return build(*args, **kwargs)

    return wrapper


@_branded
def elo_history_chart(
    team: str,
    history: Sequence[RatingSeason],
    season: str | None = None,
    marked_date: date | None = None,
) -> Figure:
    """A team's Elo rating before each of its matches, one line per season.

    Separate lines leave gaps for summer breaks and for seasons the team spent outside the
    league. ``season``, when given, is drawn in orange; ``marked_date`` is a vertical line.
    """
    if not history:
        raise ValueError("need at least one season of ratings")
    figure, axes = _figure()
    for rating_season in history:
        chosen = rating_season.season == season
        axes.plot(
            rating_season.dates,
            rating_season.ratings,
            color=GOLD if chosen else ELO_COLOUR,
            linewidth=2.6 if chosen else 1.6,
            label=season_text(rating_season.season) if chosen else f"_{rating_season.season}",
            zorder=3 if chosen else 2,
        )
    if marked_date is not None:
        axes.axvline(
            marked_date,
            color=TEXT,
            linewidth=1,
            label=f"Meciuri până la {date_text(marked_date)}",
        )
    _title(axes, f"{team}: ratingul Elo înaintea fiecărui meci")
    axes.set_xlabel("Data")
    axes.set_ylabel("Rating Elo")
    axes.yaxis.set_major_formatter(FuncFormatter(lambda value, _: integer(round(value))))
    axes.grid(axis="y")
    if marked_date is not None or any(s.season == season for s in history):
        axes.legend(loc="best")
    return figure


@_branded
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
    axes.imshow(shown, cmap=SEQUENTIAL_MAP, vmin=0)
    for (home_goals, away_goals), probability in np.ndenumerate(shown):
        axes.text(
            away_goals,
            home_goals,
            percent(probability),
            ha="center",
            va="center",
            fontsize=7.5,
            color=_ink(SEQUENTIAL_MAP(probability / shown.max())),
        )
    _cell_gaps(axes, shown.shape)
    goals = range(shown_goals + 1)
    axes.set_xticks(goals)
    axes.set_yticks(goals)
    _title(axes, f"Probabilitatea fiecărui scor (Poisson, 0–{shown_goals} goluri)")
    axes.set_xlabel(f"Goluri {away_team} (oaspeți)")
    axes.set_ylabel(f"Goluri {home_team} (gazde)")
    return figure


@_branded
def calibration_chart(tables: Mapping[str, Sequence[CalibrationBin]]) -> Figure:
    """Predicted probability against observed frequency for each model; empty bins are skipped.

    Points on the diagonal mean that "p%" happened p% of the time. Models are keyed by their
    log names; each keeps its own colour, the reference is grey.
    """
    if not tables:
        raise ValueError("need at least one model's calibration table")
    figure, axes = _figure()
    axes.plot([0, 1], [0, 1], color=MUTED, linewidth=0.9, label="Calibrare perfectă", zorder=1)
    for model, table in tables.items():
        filled = [bin_ for bin_ in table if bin_.count]
        axes.plot(
            [bin_.mean_predicted for bin_ in filled],
            [bin_.observed_frequency for bin_ in filled],
            marker="o",
            markersize=6.5,
            markeredgecolor=SURFACE,
            markeredgewidth=1.5,
            color=MODEL_COLOURS.get(model, BASELINE_COLOUR),
            linestyle="-" if model in MODEL_COLOURS else "--",
            label=model_label(model),
            zorder=3,
        )
    bins = len(next(iter(tables.values())))
    axes.set_xlim(0, 1)
    axes.set_ylim(0, 1)
    axes.set_aspect("equal")
    _tick_labels(axes.xaxis, 100, "%")
    _tick_labels(axes.yaxis, 100, "%")
    _title(axes, f"Calibrare: toate rezultatele, {bins} intervale")
    axes.set_xlabel("Probabilitatea prezisă")
    axes.set_ylabel("Frecvența observată")
    axes.grid()
    axes.legend(loc="upper left")
    return figure


@_branded
def confusion_chart(model: str, matrix: np.ndarray) -> Figure:
    """Match counts by actual result (rows) and predicted result (columns)."""
    if matrix.shape != (3, 3):
        raise ValueError(f"a confusion matrix is 3x3, got shape {matrix.shape}")
    figure, axes = _figure()
    axes.imshow(matrix, cmap=SEQUENTIAL_MAP, vmin=0)
    for (actual, predicted), count in np.ndenumerate(matrix):
        axes.text(
            predicted,
            actual,
            integer(int(count)),
            ha="center",
            va="center",
            color=_ink(SEQUENTIAL_MAP(count / max(matrix.max(), 1))),
        )
    _cell_gaps(axes, matrix.shape)
    labels = [OUTCOME_LABELS[code] for code in OUTCOME_ORDER]
    axes.set_xticks(range(3), labels=labels)
    axes.set_yticks(range(3), labels=labels)
    _title(axes, f"{model_label(model)}: matricea de confuzie")
    axes.set_xlabel("Prezis")
    axes.set_ylabel("Real")
    return figure


@_branded
def team_groups_chart(groups: SeasonGroups, team: str | None = None) -> Figure:
    """One season's teams by goals scored and conceded per match, coloured by K-Means group.

    The groups come from all six profile values, so a team can sit closer to another group's
    centre on these two axes. ``team``, when given, is ringed in orange.
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
                edgecolors=SURFACE,
                linewidths=1.2,
                label=name,
                zorder=3,
            )
    axes.scatter(
        [centre.goals_scored for centre in groups.centres],
        [centre.goals_conceded for centre in groups.centres],
        color=[GROUP_COLOURS[centre.group] for centre in groups.centres],
        marker="X",
        s=CENTRE_MARKER_SIZE,
        edgecolors=TEXT,
        linewidths=0.8,
        label="_group centres",
        zorder=2,
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
                xytext=(0, 0),  # placed by _place_labels
                textcoords="offset points",
                fontsize=9 if chosen else 7.5,
                fontweight="bold" if chosen else "normal",
                color=TEXT if chosen else MUTED,
            )
        )
        markers.append((*position, TEAM_MARKER_SIZE, MARKER_CLASH))
        if chosen:
            axes.scatter(
                *position,
                s=CHOSEN_MARKER_SIZE,
                facecolors="none",
                edgecolors=GOLD,
                linewidths=2,
                label="_chosen team",
                zorder=4,
            )
            markers.append((*position, CHOSEN_MARKER_SIZE, MARKER_CLASH))
    handles, _ = axes.get_legend_handles_labels()
    centre_handle = Line2D(
        [], [], marker="X", linestyle="none", color=TEXT, label="Centrul grupului (toate sezoanele)"
    )
    axes.legend(handles=[*handles, centre_handle], loc="best")
    _title(axes, f"Grupurile echipelor, {season_text(groups.season)} (K-Means pe șase valori)")
    axes.set_xlabel("Goluri marcate pe meci")
    axes.set_ylabel("Goluri primite pe meci")
    _tick_labels(axes.xaxis)
    _tick_labels(axes.yaxis)
    axes.grid()
    _place_labels(axes, labels, markers)
    # A window shows the figure at its own size; the names are placed again for every new size.
    figure.canvas.mpl_connect("resize_event", lambda _: _place_labels(axes, labels, markers))
    return figure


@_branded
def skill_chart(results: Sequence[LeagueResults]) -> Figure:
    """How much of the reference's error each model removes, league by league (Brier skill)."""
    if not results:
        raise ValueError("need at least one league")
    figure, axes = _figure()
    names = [_league_name(r.competition) for r in results]
    band = 0.24  # one bar's thickness in a league's row of three
    for index, model in enumerate(COMPARED_MODELS):
        positions = [row + (index - 1) * (band + 0.04) for row in range(len(results))]
        axes.barh(
            positions,
            [r.skill[model] for r in results],
            height=band,
            color=MODEL_COLOURS[model],
            label=model_label(model),
            zorder=2,
        )
    axes.set_yticks(range(len(results)), labels=names)
    axes.invert_yaxis()  # leagues read top to bottom
    _tick_labels(axes.xaxis, 100, "%")
    _title(axes, "Cât elimină fiecare model din eroarea referinței (abilitate Brier)")
    axes.set_xlabel("Partea din scorul Brier al frecvențelor trecute eliminată de model")
    axes.grid(axis="x")
    axes.tick_params(axis="y", length=0)
    figure.legend(loc="outside lower center", ncols=3)  # below the axis title, never over bars
    return figure


@_branded
def home_advantage_chart(characters: Sequence[LeagueCharacter]) -> Figure:
    """Home wins with fans (other seasons) and in 2020/21, mostly behind closed doors."""
    shown = [c for c in characters if c.closed_doors_home_win is not None]
    if not shown:
        raise ValueError("need at least one league with 2020/21 and other seasons")
    figure, axes = _figure()
    rows = range(len(shown))
    for row, character in zip(rows, shown, strict=True):
        axes.plot(
            [character.other_seasons_home_win, character.closed_doors_home_win],
            [row, row],
            color=LINE,
            linewidth=3,
            zorder=1,
        )
    for values, colour, label in (
        ([c.other_seasons_home_win for c in shown], WITH_FANS, "Celelalte sezoane"),
        ([c.closed_doors_home_win for c in shown], CLOSED_DOORS, "2020/21"),
    ):
        axes.scatter(values, list(rows), s=80, color=colour, edgecolors=SURFACE, linewidths=2,
                     label=label, zorder=3)  # fmt: skip
    axes.set_yticks(list(rows), labels=[_league_name(c.competition) for c in shown])
    axes.invert_yaxis()
    _tick_labels(axes.xaxis, 100, "%")
    _title(axes, "Victoriile gazdelor: cu spectatori și în 2020/21 (în mare parte fără)")
    axes.set_xlabel("Meciuri câștigate de gazde")
    axes.grid(axis="x")
    axes.tick_params(axis="y", length=0)
    figure.legend(loc="outside lower center", ncols=2)
    return figure


def _tick_labels(axis: Axis, scale: float = 1, suffix: str = "") -> None:
    """Ticks 1, 2 or 5 units apart (times a power of ten), each labelled with just enough decimals
    to show it exactly, with a decimal comma (``scale`` 100 and suffix "%" for shares)."""
    axis.set_major_locator(MaxNLocator(steps=[1, 2, 5, 10]))

    def text(value: float, _: int) -> str:
        locations = axis.get_majorticklocs()
        step = float(np.min(np.diff(locations))) * scale if len(locations) > 1 else 1.0
        digits = max(0, -math.floor(math.log10(step) + 1e-9))
        return number(value * scale, digits) + suffix

    axis.set_major_formatter(FuncFormatter(text))


def _title(axes: Axes, text: str) -> None:
    """A chart title in the condensed display face, like the titles of the interface."""
    axes.set_title(text, fontfamily=DISPLAY_FAMILY, fontsize=14, fontweight="bold")


def _ink(cell: tuple[float, float, float, float]) -> str:
    """Text colour for a heatmap cell: dark on light cells, light on dark ones."""
    red, green, blue = (
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in cell[:3]
    )
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    return BACKGROUND if luminance > 0.3 else TEXT


def _league_name(code: str) -> str:
    return COMPETITIONS[code].name if code in COMPETITIONS else code


def _cell_gaps(axes: Axes, shape: tuple[int, int]) -> None:
    """A 2-pixel white gap between the cells of a heatmap, instead of borders."""
    rows, columns = shape
    axes.set_xticks(np.arange(-0.5, columns, 1), minor=True)
    axes.set_yticks(np.arange(-0.5, rows, 1), minor=True)
    axes.grid(which="minor", color=SURFACE, linewidth=2)
    axes.tick_params(which="minor", length=0)
    axes.tick_params(which="major", length=0)
    for spine in axes.spines.values():
        spine.set_visible(False)


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
        line = label.get_window_extent().height / pixels_per_point  # the name's height in points
        best: tuple[int, tuple[float, float, str]] | None = None
        for place in LABEL_PLACES:
            _put(label, place, line)
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
        _put(label, best[1], line)
        obstacles.append((None, label.get_window_extent(), LABEL_CLASH))


def _put(label: Annotation, place: tuple[float, float, str], line: float) -> None:
    across, up, alignment = place
    label.xyann = (across, up * line)
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
