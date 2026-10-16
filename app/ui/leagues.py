"""Ligi: the five leagues side by side, their character and how the models do in each."""

from collections.abc import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.data.competitions import COMPETITIONS
from app.evaluation.comparison import COMPARED_MODELS, PairedDifference
from app.services.formatting import integer, number, percent, quantity, signed
from app.services.labels import country_label, model_label
from app.services.leagues import LeaguesOverview
from app.ui.brand import flag_pixmap
from app.ui.context import AppContext, LeagueServices
from app.ui.widgets import (
    ChartView,
    PageTabs,
    ReflowGrid,
    card,
    fill_table,
    label,
    make_table,
    unreadable_log_text,
)
from app.visualization.charts import home_advantage_chart, skill_chart

VIEWS = ("Tabele", "Grafice")
REFERENCE = "Past frequencies"
CHART_HEIGHT = 420
CARD_WIDTH = 210  # the league cards: five in a row when each can be this wide


def league_name(code: str) -> str:
    return COMPETITIONS[code].name if code in COMPETITIONS else code


def difference_text(difference: PairedDifference) -> str:
    winner = model_label(difference.better) if difference.better else "nicio diferență reală"
    return f"{signed(difference.mean)} · {winner}"


class LeagueCard(QFrame):
    """One league in a few numbers; a click opens it. The league on screen has a frame in its
    accent."""

    clicked = Signal(str)

    def __init__(self, code: str) -> None:
        super().__init__()
        self.code = code
        self.setProperty("role", "card")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        flag = QLabel()
        flag.setPixmap(flag_pixmap(code, 26))
        self.name_label = label(league_name(code), "section")
        heading = QHBoxLayout()
        heading.setSpacing(10)
        heading.addWidget(flag)
        heading.addWidget(self.name_label, stretch=1)
        self.value_label = label("–", "stat")
        self.goals_label = label(country_label(code), "caption")
        self.best_label = label("–", "strong")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(2)
        layout.addLayout(heading)
        layout.addSpacing(6)
        layout.addWidget(self.value_label)
        layout.addWidget(label("VICTORII ALE GAZDELOR", "overline"))
        layout.addSpacing(8)
        layout.addWidget(self.goals_label)
        layout.addWidget(label("Cel mai mic scor Brier:", "caption"))
        layout.addWidget(self.best_label)
        layout.addStretch()

    def set_current(self, current: bool) -> None:
        self.setProperty("role", "current" if current else "card")
        self.style().unpolish(self)
        self.style().polish(self)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.code)
        super().mouseReleaseEvent(event)


class LeaguesTab(QWidget):
    """Compares all leagues; offers to backtest the leagues that have no log yet."""

    title = "Ligi"
    subtitle = "Cele cinci campionate comparate: cum arată fotbalul și cât de bine prezic modelele."

    def __init__(self, context: AppContext, choose_league: Callable[[str], None]) -> None:
        super().__init__()
        self._context = context
        self._league: LeagueServices | None = None
        self.cards = {code: LeagueCard(code) for code in context.competitions}
        for league_card in self.cards.values():
            league_card.clicked.connect(choose_league)
        self._overview: LeaguesOverview | None = None

        self.summary_label = label(role="caption", wrap=True)
        self.backtest_button = QPushButton("Rulează backtestul ligilor care lipsesc")
        self.backtest_button.setProperty("role", "primary")
        self.backtest_button.clicked.connect(self._run_backtests)
        self.character_table = make_table(
            [
                "Ligă",
                "Meciuri",
                "Victorii gazde",
                "Egaluri",
                "Victorii oaspeți",
                "Goluri pe meci",
                "Marja gazdelor",
                "Gazde 2020/21",
                "Gazde, alte sezoane",
            ],
            stretch_column=0,
        )
        self.models_table = make_table(
            [
                "Ligă",
                *(f"{model_label(m)} (Brier)" for m in COMPARED_MODELS),
                f"{model_label(REFERENCE)} (Brier)",
                "Cel mai mic scor",
                "Abilitatea lui",
            ],
            stretch_column=0,
        )
        self.differences_table = make_table(
            [
                "Ligă",
                "Elo – Regresie logistică",
                "Elo – Poisson",
                "Regresie logistică – Poisson",
            ],
            stretch_column=0,
        )
        self.pooled_label = label(role="caption", wrap=True)
        self.skill_chart = ChartView("Graficul abilității apare când toate ligile au backtest.")
        self.home_chart = ChartView("Graficul avantajului gazdelor apare aici.")

        tables = QWidget()
        tables_layout = QVBoxLayout(tables)
        tables_layout.setContentsMargins(0, 8, 0, 0)
        tables_layout.setSpacing(12)
        for title, widget in (
            ("Caracterul ligilor, în sezoanele de evaluare 2010/11–2025/26", self.character_table),
            ("Modelele în fiecare ligă (scor Brier: mai mic e mai bine)", self.models_table),
            ("Care model e mai bun, meci cu meci (diferența scorului Brier)",
             self.differences_table),
            (None, self.pooled_label),
        ):  # fmt: skip
            if title:
                tables_layout.addWidget(label(title, "section"))
            tables_layout.addWidget(widget)
        charts_page = QWidget()
        charts_layout = QVBoxLayout(charts_page)
        charts_layout.setContentsMargins(0, 8, 0, 0)
        charts_layout.setSpacing(16)
        for chart in (self.skill_chart, self.home_chart):
            chart.setMinimumHeight(CHART_HEIGHT)
            charts_layout.addWidget(chart)
        charts_layout.addStretch()

        content, content_layout = card()
        content_layout.addWidget(self.summary_label)
        content_layout.addWidget(self.backtest_button)
        self.views = PageTabs()
        self.views.addTab(tables, VIEWS[0])
        self.views.addTab(charts_page, VIEWS[1])
        content_layout.addWidget(self.views)
        cards = ReflowGrid(CARD_WIDTH)
        for league_card in self.cards.values():
            cards.add(league_card)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(cards)
        layout.addWidget(content)
        layout.addStretch()  # the card ends with its content

    def show_league(self, league: LeagueServices) -> None:
        """The league on screen is highlighted in the cards and the tables."""
        self._league = league
        for code, league_card in self.cards.items():
            league_card.set_current(code == league.code)
        if self._overview is not None:
            self._show(self._overview)
        else:
            self.refresh()

    def refresh(self) -> None:
        comparison = self._context.comparison
        missing = comparison.missing()
        if missing:
            names = ", ".join(league_name(code) for code in missing)
            self.summary_label.setText(
                f"Lipsesc jurnalele predicțiilor pentru: {names}. Rulează backtestul lor "
                "(aproximativ 10 secunde pentru fiecare ligă) ca să vezi comparația."
            )
            self.backtest_button.show()
            return
        self.backtest_button.hide()
        self._context.run_task(comparison.overview, self._show, self._overview_failed)

    def _show(self, overview: LeaguesOverview) -> None:
        self._overview = overview
        for result in overview.results:
            league_card = self.cards.get(result.competition)
            if league_card is not None:
                league_card.value_label.setText(percent(result.character.home_win))
                league_card.goals_label.setText(
                    f"{number(result.character.goals, 2)} goluri pe meci"
                )
                league_card.best_label.setText(model_label(result.best))
        current = {
            index for index, r in enumerate(overview.results)
            if self._league is not None and r.competition == self._league.code
        }  # fmt: skip
        self.summary_label.setText(
            f"{quantity(len(overview.results), 'ligă', 'ligi')}, "
            f"{quantity(overview.matches, 'meci', 'meciuri')} de evaluare. Fiecare ligă are "
            "propriii parametri, aleși pe sezoanele ei de calibrare. Liga aleasă este evidențiată."
        )
        fill_table(
            self.character_table,
            [
                [
                    league_name(r.competition),
                    integer(r.character.matches),
                    percent(r.character.home_win),
                    percent(r.character.draw),
                    percent(r.character.away_win),
                    number(r.character.goals, 2),
                    signed(r.character.home_margin, 2),
                    _optional_percent(r.character.closed_doors_home_win),
                    _optional_percent(r.character.other_seasons_home_win),
                ]
                for r in overview.results
            ],
            fit=True,
            highlight=current,
        )
        rows = []
        for r in overview.results:
            brier = {e.model: e.brier.value for e in r.evaluations if e.brier is not None}
            rows.append(
                [
                    league_name(r.competition),
                    *(number(brier[model]) for model in (*COMPARED_MODELS, REFERENCE)),
                    model_label(r.best),
                    percent(r.skill[r.best]),
                ]
            )
        fill_table(self.models_table, rows, fit=True, highlight=current)
        fill_table(
            self.differences_table,
            [
                [league_name(r.competition), *(difference_text(d) for d in r.differences)]
                for r in overview.results
            ]
            + [["Toate ligile", *(difference_text(d) for d in overview.pooled)]],
            fit=True,
            highlight=current,
        )
        self.pooled_label.setText(
            "O diferență negativă înseamnă că primul model e mai bun; după diferență este modelul "
            "real mai bun (intervalul de 95% nu conține 0). „Toate ligile” compară modelele pe "
            "toate meciurile la un loc."
        )
        self.skill_chart.show_figure(skill_chart(overview.results))
        try:
            self.home_chart.show_figure(
                home_advantage_chart([r.character for r in overview.results])
            )
        except ValueError:  # no league has both 2020/21 and other seasons in its log
            self.home_chart.show_message("Nicio ligă nu are atât sezonul 2020/21, cât și altele.")

    def _overview_failed(self, message: str) -> None:
        self.summary_label.setText(unreadable_log_text(message))
        self.backtest_button.show()

    def _run_backtests(self) -> None:
        self.backtest_button.setEnabled(False)
        self.summary_label.setText("Backtesturile rulează…")
        self._context.run_task(
            self._context.comparison.build_missing_logs, self._built, self._failed
        )

    def _built(self, _: object) -> None:
        self.backtest_button.setEnabled(True)
        self.refresh()

    def _failed(self, message: str) -> None:
        self.backtest_button.setEnabled(True)
        self._context.report_error(message)
        self.refresh()


def _optional_percent(value: float | None) -> str:
    return "–" if value is None else percent(value)
