"""Acasă: the league in four numbers, the model with the lowest Brier score, "your team" and the
models' results."""

from collections.abc import Callable

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.evaluation.comparison import COMPARED_MODELS, Measure
from app.services.evaluation import EvaluationResults
from app.services.formatting import integer, number, percent, quantity, season_text
from app.services.labels import model_label
from app.services.preferences import FavouriteTeam
from app.ui.brand import team_badge
from app.ui.context import AppContext, LeagueServices
from app.ui.widgets import (
    FormStrip,
    StatTile,
    card,
    fill_table,
    label,
    make_table,
    unreadable_log_text,
)

TILES = ("Meciuri", "Sezoane", "Echipe", "Meciuri evaluate")
BADGE_SIZE = 64


class HomePage(QWidget):
    """The first screen: what is loaded, which model does best, and the user's team."""

    title = "Acasă"
    subtitle = (
        "Cinci campionate, patru algoritmi scriși de noi: Elo, Poisson, regresie logistică și "
        "K‑Means. Fiecare predicție folosește doar meciurile jucate înaintea ei."
    )

    def __init__(self, context: AppContext, choose_favourite: Callable[[], None]) -> None:
        super().__init__()
        self._context = context
        self._league: LeagueServices | None = None

        self.stat_tiles = {name: StatTile(name) for name in TILES}
        tiles = QHBoxLayout()
        tiles.setSpacing(16)
        for tile in self.stat_tiles.values():
            tiles.addWidget(tile, stretch=1)

        best_card, best_layout = card()
        best_layout.addWidget(label("CEL MAI MIC SCOR BRIER", "eyebrow"))
        self.best_label = label("–", "hero", wrap=True)
        self.best_caption = label(role="caption", wrap=True)
        best_layout.addWidget(self.best_label)
        best_layout.addWidget(self.best_caption)
        best_layout.addStretch()

        favourite_card, favourite_layout = card(role="favourite")
        favourite_layout.addWidget(label("ECHIPA TA", "eyebrow"))
        self.favourite_badge = QLabel()
        self.favourite_label = label("–", "hero", wrap=True)
        self.favourite_caption = label(role="caption", wrap=True)
        identity = QGridLayout()
        identity.setHorizontalSpacing(16)
        identity.setVerticalSpacing(2)
        identity.addWidget(self.favourite_badge, 0, 0, 2, 1)
        identity.addWidget(self.favourite_label, 0, 1)
        identity.addWidget(self.favourite_caption, 1, 1)
        identity.setColumnStretch(1, 1)
        favourite_layout.addLayout(identity)
        self.favourite_form = FormStrip()
        self.favourite_detail = label(role="caption", wrap=True)
        form = QHBoxLayout()
        form.setSpacing(12)
        form.addWidget(self.favourite_form)
        form.addWidget(self.favourite_detail, stretch=1)
        favourite_layout.addLayout(form)
        favourite_layout.addStretch()
        self.favourite_button = QPushButton("Alege echipa ta")
        self.favourite_button.clicked.connect(choose_favourite)
        favourite_layout.addWidget(self.favourite_button)

        cards = QHBoxLayout()
        cards.setSpacing(16)
        cards.addWidget(best_card, stretch=1)
        cards.addWidget(favourite_card, stretch=1)

        results_card, results_layout = card("Rezultatele modelelor")
        self.results_label = label(role="caption", wrap=True)
        self.results_table = make_table(
            ["Model", "Acuratețe", "Scor Brier", "Pierdere logaritmică"], stretch_column=0
        )
        self.backtest_button = QPushButton("Rulează backtestul")
        self.backtest_button.setProperty("role", "primary")
        self.backtest_button.clicked.connect(self._run_backtest)
        results_layout.addWidget(self.results_label)
        results_layout.addWidget(self.results_table)
        results_layout.addWidget(self.backtest_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addLayout(tiles)
        layout.addLayout(cards)
        layout.addWidget(results_card)
        layout.addStretch()

    def show_league(self, league: LeagueServices) -> None:
        self._league = league
        summary = league.catalog.summary()
        self.stat_tiles["Meciuri"].set_value(integer(summary.matches))
        self.stat_tiles["Sezoane"].set_value(integer(summary.seasons))
        self.stat_tiles["Echipe"].set_value(integer(summary.teams))
        self.stat_tiles["Meciuri evaluate"].set_value("–")
        self.refresh()
        self.show_favourite()

    def refresh(self) -> None:
        """Show the league's results, or offer to run its backtest when there is no log."""
        if self._league is None:
            return
        evaluation = self._league.evaluation
        if not evaluation.has_log:
            self._without_results(
                f"Nu există încă un jurnal al predicțiilor pentru {self._league.name}. "
                "Rulează backtestul (aproximativ 10 secunde) ca să vezi rezultatele."
            )
            return
        self.backtest_button.hide()
        self._context.run_task(
            evaluation.results,
            self._show_results,
            lambda details: self._without_results(unreadable_log_text(details)),
        )

    def show_favourite(self) -> None:
        favourite = self._context.preferences.favourite
        if favourite is None:
            self.favourite_badge.clear()
            self.favourite_label.setText("–")
            self.favourite_caption.setText(
                "Alege echipa pe care o urmărești: va fi evidențiată în clasamente."
            )
            self.favourite_form.set_results(())
            self.favourite_detail.clear()
            self.favourite_button.setText("Alege echipa ta")
            return
        self.favourite_badge.setPixmap(team_badge(favourite.team, BADGE_SIZE, highlighted=True))
        self.favourite_label.setText(favourite.team)
        self.favourite_button.setText("Schimbă echipa")
        self._show_favourite_season(favourite)

    def _show_favourite_season(self, favourite: FavouriteTeam) -> None:
        league = self._context.league(favourite.competition)
        seasons = [s for s in league.catalog.seasons() if favourite.team in league.catalog.teams(s)]
        if not seasons:
            self.favourite_caption.setText(f"{league.name}: echipa nu apare în date.")
            self.favourite_form.set_results(())
            self.favourite_detail.clear()
            return
        season = seasons[-1]
        overview = league.teams.overview(season, favourite.team)
        rating = league.teams.elo_history(favourite.team)[-1].ratings[-1]
        teams = len(league.catalog.teams(season))
        self.favourite_caption.setText(
            f"{league.name}, {season_text(season)}: locul {overview.position} din {teams}, "
            f"{quantity(overview.record.points, 'punct', 'puncte')}."
        )
        self.favourite_form.set_results([result.value for result in overview.form])
        self.favourite_detail.setText(
            f"Ultimele 5 meciuri · rating Elo înaintea ultimului meci: {integer(round(rating))}"
        )

    def _show_results(self, results: EvaluationResults) -> None:
        self.stat_tiles["Meciuri evaluate"].set_value(integer(results.matches))
        self.results_label.setText(
            f"{quantity(results.matches, 'meci', 'meciuri')} din sezoanele "
            f"{season_text(results.first_season)}–{season_text(results.last_season)}, "
            "fiecare prezis doar din meciurile de dinainte. Scorul Brier și pierderea "
            "logaritmică: mai mic înseamnă mai bine."
        )
        fill_table(
            self.results_table,
            [
                [
                    model_label(e.model),
                    percent(e.accuracy.value),
                    number(e.brier.value if e.brier else None),
                    number(e.log_loss.value if e.log_loss else None),
                ]
                for e in results.evaluations
            ],
            fit=True,
        )
        self.results_table.show()
        compared = sorted(
            (e for e in results.evaluations if e.model in COMPARED_MODELS),
            key=lambda e: e.brier.value,
        )
        best, runner_up = compared[0], compared[1]
        lead = next(
            d
            for d in results.differences
            if d.measure == Measure.BRIER and {d.first, d.second} == {best.model, runner_up.model}
        )
        verdict = (
            "un avantaj real (intervalul de 95% nu conține 0)"
            if lead.significant
            else "diferența nu este reală (intervalul de 95% conține 0)"
        )
        self.best_label.setText(model_label(best.model))
        self.best_caption.setText(
            f"{number(best.brier.value)} în {self._league.name}, acuratețe "
            f"{percent(best.accuracy.value)}. Următorul, {model_label(runner_up.model)}: "
            f"{number(runner_up.brier.value)}; {verdict}."
        )

    def _without_results(self, message: str) -> None:
        # Shown in place rather than in a dialog: every change of screen would repeat a dialog.
        self.results_label.setText(message)
        self.results_table.hide()
        self.backtest_button.show()
        self.best_label.setText("–")
        self.best_caption.setText("Apare după backtest.")

    def _run_backtest(self) -> None:
        self.backtest_button.setEnabled(False)
        self.results_label.setText("Backtestul rulează…")
        self._context.run_task(self._league.evaluation.build_log, self._built, self._failed)

    def _built(self, _: object) -> None:
        self.backtest_button.setEnabled(True)
        self.refresh()

    def _failed(self, message: str) -> None:
        self.backtest_button.setEnabled(True)
        self._context.report_error(message)
        self.refresh()
