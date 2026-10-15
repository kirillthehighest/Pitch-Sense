"""A match's page (Phase 19): both clubs on a card in the league's colours, what each model
expects and why, the likely scores of the Poisson model and how both teams came into the match.

``HypotheticalDialog`` asks for any two teams of a season and a day, the "Orice meci" of earlier
phases, and opens the answer on the same page.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

from PySide6.QtCore import QDate, QRectF, Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.data.competitions import competition
from app.data.preprocessing import season_date_window
from app.prediction.outputs import ModelName
from app.services.formatting import date_text, number, percent, season_text
from app.services.labels import model_label, outcome_label
from app.services.predictions import MatchForecast, forecast_of, summarize
from app.services.teams import TeamOverview
from app.ui.brand import flag_pixmap, team_badge
from app.ui.context import AppContext, LeagueServices
from app.ui.themes import Theme, theme_for
from app.ui.widgets import (
    BarRow,
    ChartView,
    FormStrip,
    ProbabilityBars,
    card,
    fill_table,
    label,
    make_table,
    paint_head_card,
)
from app.visualization.charts import score_heatmap

CREST_SIZE = 96
# What each model looks at, in a sentence anyone can follow (the details: Analiză).
MODEL_EXPLANATIONS = {
    ModelName.ELO: (
        "Puterea fiecărei echipe, din toate rezultatele ei: o victorie contra unui adversar "
        "puternic urcă ratingul mai mult."
    ),
    ModelName.POISSON: (
        "Câte goluri marchează și primește fiecare echipă, acasă și în deplasare; din ele, "
        "șansa fiecărui scor."
    ),
    ModelName.LOGISTIC_REGRESSION: (
        "A învățat din meciurile trecute cât contează diferența de rating, punctele, golurile, "
        "forma și șuturile pe poartă."
    ),
}
NO_POISSON = "Nu există o predicție Poisson pentru acest meci."


@dataclass(frozen=True, eq=False)
class MatchContext:
    """How both teams came into the match: their season so far and their Elo ratings."""

    home: TeamOverview
    away: TeamOverview
    home_rating: float
    away_rating: float
    teams: int


def status_text(forecast: MatchForecast) -> str:
    """What happened or will happen, under the score."""
    if forecast.played is not None:
        return "Final"
    if forecast.hypothetical:
        return "Meci ipotetic"
    if forecast.postponed:
        return "Amânat"
    return "Programat"


def knowledge_text(forecast: MatchForecast) -> str:
    """Which matches the predictions use."""
    if forecast.played is not None:
        return (
            f"Predicțiile au fost făcute din meciurile jucate înainte de "
            f"{date_text(forecast.match_date)}, fără să știe rezultatul."
        )
    as_of = forecast.as_of or forecast.match_date
    if forecast.hypothetical:
        return (
            f"Meci ipotetic: predicțiile folosesc meciurile jucate înainte de {date_text(as_of)}."
        )
    text = (
        "Predicțiile folosesc toate meciurile jucate până acum (ultimele pe "
        f"{date_text(as_of - timedelta(days=1))})."
    )
    if forecast.postponed:
        text += (
            " Data din calendar a trecut, dar rezultatul lipsește: meci amânat sau încă "
            "neînregistrat."
        )
    return text


def verdict_text(forecast: MatchForecast) -> str:
    """For a played match: the result and which models expected it."""
    played = forecast.played
    right = [
        model_label(str(model))
        for model, prediction in forecast.predictions.items()
        if prediction.probabilities.most_likely == played.result
    ]
    wrong = [
        model_label(str(model))
        for model, prediction in forecast.predictions.items()
        if prediction.probabilities.most_likely != played.result
    ]
    text = (
        f"Rezultat: {played.home_goals}–{played.away_goals} ({outcome_label(played.result.value)})."
    )
    if right:
        text += f" L-au anticipat: {', '.join(right)}."
    if wrong:
        text += f" Nu l-au anticipat: {', '.join(wrong)}."
    return text


class MatchHero(QFrame):
    """The head of a match: a card lit by the league's deep colour, both crests, the score and
    the state of the match in a pill."""

    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(240)
        self.theme: Theme | None = None  # the palette of the match's league
        self.eyebrow = label(role="hero-eyebrow")
        self.eyebrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.home_badge, self.away_badge = QLabel(), QLabel()
        self.home_name = label(role="team", wrap=True)
        self.away_name = label(role="team", wrap=True)
        self.score = label("VS", "score")
        self.status = label(role="status")
        for widget in (
            self.home_badge,
            self.away_badge,
            self.home_name,
            self.away_name,
            self.score,
            self.status,
        ):
            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(6)
        grid.addWidget(self.home_badge, 0, 0)
        grid.addWidget(self.score, 0, 1)
        grid.addWidget(self.away_badge, 0, 2)
        grid.addWidget(self.home_name, 1, 0)
        grid.addWidget(self.status, 1, 1, alignment=Qt.AlignmentFlag.AlignHCenter)
        grid.addWidget(self.away_name, 1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(2, 1)
        grid.setColumnMinimumWidth(1, 200)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 22)
        layout.setSpacing(12)
        layout.addWidget(self.eyebrow)
        layout.addLayout(grid)

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt's name)
        painter = QPainter(self)
        paint_head_card(painter, QRectF(self.rect()), theme=self.theme)
        painter.end()


class TeamColumn(QWidget):
    """One team's way into the match: place, record, form and Elo rating."""

    def __init__(self, open_team: Callable[[str], None]) -> None:
        super().__init__()
        self._open_team = open_team
        self.team: str | None = None
        self.name_button = QPushButton()
        self.name_button.setProperty("role", "link")
        self.name_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.name_button.clicked.connect(lambda: self.team and self._open_team(self.team))
        self.place = label(role="caption", wrap=True)
        self.form = FormStrip()
        self.rating = label(role="caption")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.name_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.place)
        layout.addWidget(self.form)
        layout.addWidget(self.rating)

    def show_team(self, overview: TeamOverview, rating: float, teams: int) -> None:
        self.team = overview.team
        self.name_button.setText(f"{overview.team} ›")
        record = overview.record
        self.place.setText(
            f"Locul {overview.position} din {teams} · {record.played} meciuri, "
            f"{record.points} puncte, goluri {record.goals_for}–{record.goals_against}"
        )
        self.form.set_results([result.value for result in overview.form])
        self.rating.setText(f"Rating Elo: {number(rating, 0)}")


class MatchDetail(QWidget):
    """Everything about one match; ``back_button`` returns to the list."""

    def __init__(self, context: AppContext, open_team: Callable[..., None]) -> None:
        super().__init__()
        self._context = context
        self._open_team = open_team
        self.forecast: MatchForecast | None = None
        self.back_button = QPushButton("‹ Înapoi la meciuri")
        self.back_button.setProperty("role", "link")
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.hero = MatchHero()

        models_card, models_layout = card("Ce spun modelele")
        self.bars = ProbabilityBars()
        models_layout.addWidget(self.bars)
        self.explanations = {}
        for model, text in MODEL_EXPLANATIONS.items():
            row = label(f"{model_label(str(model))}: {text}", "caption", wrap=True)
            self.explanations[model] = row
            models_layout.addWidget(row)
        self.verdict = label(role="strong", wrap=True)
        self.knowledge = label(role="caption", wrap=True)
        models_layout.addWidget(self.verdict)
        models_layout.addWidget(self.knowledge)
        models_layout.addStretch()

        teams_card, teams_layout = card("Cum vin echipele")
        self.home_column = TeamColumn(self._open)
        self.away_column = TeamColumn(self._open)
        columns = QHBoxLayout()
        columns.setSpacing(24)
        columns.addWidget(self.home_column, stretch=1)
        columns.addWidget(self.away_column, stretch=1)
        teams_layout.addLayout(columns)
        self.teams_note = label(role="caption", wrap=True)
        teams_layout.addWidget(self.teams_note)
        teams_layout.addStretch()

        poisson_card, poisson_layout = card("Scoruri probabile (Poisson)")
        self.goals_label = label(wrap=True)
        self.scores_table = make_table(["Scor", "Probabilitate"], stretch_column=0)
        self.scores_table.setFixedHeight(5 * 36 + 40)
        self.score_chart = ChartView(NO_POISSON)
        self.score_chart.setMinimumHeight(420)
        scores = QHBoxLayout()
        scores.setSpacing(20)
        left = QVBoxLayout()
        left.addWidget(self.goals_label)
        left.addWidget(self.scores_table)
        left.addStretch()
        scores.addLayout(left, stretch=2)
        scores.addWidget(self.score_chart, stretch=3)
        poisson_layout.addLayout(scores)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.addWidget(self.back_button, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.hero)
        middle = QHBoxLayout()
        middle.setSpacing(16)
        middle.addWidget(models_card, stretch=3)
        middle.addWidget(teams_card, stretch=2)
        layout.addLayout(middle)
        layout.addWidget(poisson_card)
        layout.addStretch()

    def show_forecast(self, forecast: MatchForecast) -> None:
        """Show a match at once; how both teams came into it follows from the background."""
        self.forecast = forecast
        league = competition(forecast.competition)
        when = date_text(forecast.match_date)
        if forecast.kickoff_time is not None:
            when += f", {forecast.kickoff_time:%H:%M}"
        self.hero.eyebrow.setText(f"{league.name} · {season_text(forecast.season)} · {when}")
        self.hero.theme = theme_for(forecast.competition)
        self.hero.update()
        favourite = self._context.preferences.favourite
        favourite_team = favourite.team if favourite else None
        for badge, name, team in (
            (self.hero.home_badge, self.hero.home_name, forecast.home_team),
            (self.hero.away_badge, self.hero.away_name, forecast.away_team),
        ):
            badge.setPixmap(team_badge(team, CREST_SIZE, highlighted=team == favourite_team))
            name.setText(team.upper())
        played = forecast.played
        self.hero.score.setText(
            "VS" if played is None else f"{played.home_goals} – {played.away_goals}"
        )
        self.hero.status.setText(status_text(forecast))

        summaries = [summarize(prediction) for prediction in forecast.predictions.values()]
        self.bars.set_rows(
            [BarRow(model_label(str(s.model)), s.home_win, s.draw, s.away_win) for s in summaries]
        )
        if not summaries:
            self.verdict.setText(
                "Niciun model nu are destule meciuri anterioare pentru această dată."
            )
        elif played is not None:
            self.verdict.setText(verdict_text(forecast))
        else:
            self.verdict.setText("")
        self.verdict.setVisible(bool(self.verdict.text()))
        self.knowledge.setText(knowledge_text(forecast))
        self._show_poisson(forecast, summaries)
        self.teams_note.setText("Se calculează…")
        self._context.run_task(
            lambda: self._match_context(forecast), self._show_context, self._context_failed
        )

    def _show_poisson(self, forecast: MatchForecast, summaries) -> None:
        poisson = next((s for s in summaries if s.expected_goals is not None), None)
        if poisson is None or poisson.score_probabilities is None:
            self.goals_label.setText(NO_POISSON)
            fill_table(self.scores_table, [])
            self.score_chart.show_message(NO_POISSON)
            return
        home_goals, away_goals = poisson.expected_goals
        self.goals_label.setText(
            f"Goluri așteptate: {forecast.home_team} {number(home_goals, 2)}, "
            f"{forecast.away_team} {number(away_goals, 2)}"
        )
        fill_table(
            self.scores_table,
            [
                [f"{home}–{away}", percent(probability)]
                for home, away, probability in poisson.top_scores
            ],
            fit=True,
        )
        self.score_chart.show_figure(
            score_heatmap(forecast.home_team, forecast.away_team, poisson.score_probabilities)
        )

    def _match_context(self, forecast: MatchForecast) -> MatchContext:
        teams = self._context.league(forecast.competition).teams
        before = (
            forecast.as_of if forecast.played is None and forecast.as_of else forecast.match_date
        )
        season = forecast.season
        return MatchContext(
            home=teams.overview(season, forecast.home_team, before),
            away=teams.overview(season, forecast.away_team, before),
            home_rating=teams.rating_before(forecast.home_team, before),
            away_rating=teams.rating_before(forecast.away_team, before),
            teams=len(teams.standings(season)),
        )

    def _show_context(self, context: MatchContext) -> None:
        self.home_column.show_team(context.home, context.home_rating, context.teams)
        self.away_column.show_team(context.away, context.away_rating, context.teams)
        self.teams_note.setText(
            f"Înainte de {date_text(context.home.before)}: locul în clasament, ultimele cinci "
            "rezultate (V, E, Î) și ratingul Elo."
        )

    def _context_failed(self, message: str) -> None:
        self.teams_note.setText("")
        self._context.report_error(message)

    def _open(self, team: str) -> None:
        if self.forecast is not None:
            self._open_team(self.forecast.competition, team, self.forecast.season)


class HypotheticalDialog(QDialog):
    """Any two teams of a season on a chosen day; ``predicted`` carries the answer."""

    predicted = Signal(object)  # a MatchForecast

    def __init__(self, context: AppContext, league: LeagueServices, parent: QWidget) -> None:
        super().__init__(parent)
        self._context = context
        self._league = league
        self.setWindowTitle("Alt meci")
        self.season_box = QComboBox()
        for season in reversed(league.catalog.seasons()):
            self.season_box.addItem(season_text(season), season)
        self.season_box.currentIndexChanged.connect(self._season_changed)
        self.home_box, self.away_box = QComboBox(), QComboBox()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dd.MM.yyyy")
        self.status = label(role="caption", wrap=True)
        self.predict_button = QPushButton("Calculează predicția")
        self.predict_button.setProperty("role", "primary")
        self.predict_button.clicked.connect(self.predict)
        cancel = QPushButton("Renunță")
        cancel.clicked.connect(self.reject)
        form = QFormLayout()
        form.setSpacing(12)
        form.addRow("Sezon", self.season_box)
        form.addRow("Gazde", self.home_box)
        form.addRow("Oaspeți", self.away_box)
        form.addRow("Data", self.date_edit)
        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(self.predict_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 22)
        layout.setSpacing(14)
        flag = QLabel()
        flag.setPixmap(flag_pixmap(league.code, 20))
        heading = QHBoxLayout()
        heading.addWidget(flag)
        heading.addWidget(label(f"Alt meci · {league.name}", "section"))
        heading.addStretch()
        layout.addLayout(heading)
        layout.addWidget(
            label(
                "Oricare două echipe ale sezonului, la data aleasă. Predicția folosește doar "
                "meciurile jucate înainte de acea dată.",
                "caption",
                wrap=True,
            )
        )
        layout.addLayout(form)
        layout.addWidget(self.status)
        layout.addLayout(buttons)
        self.setMinimumWidth(460)
        self._season_changed()

    def predict(self) -> None:
        season = self.season_box.currentData()
        home, away = self.home_box.currentText(), self.away_box.currentText()
        if home == away:
            self.status.setText("Alege două echipe diferite.")
            return
        day = self.date_edit.date().toPython()
        self.predict_button.setEnabled(False)
        self.status.setText("Se calculează predicțiile…")
        predictions = self._league.predictions
        code = self._league.code
        self._context.run_task(
            lambda: forecast_of(predictions.predict(season, home, away, day), code),
            self._done,
            self._failed,
        )

    def _done(self, forecast: MatchForecast) -> None:
        self.predicted.emit(forecast)
        self.accept()

    def _failed(self, message: str) -> None:
        self.predict_button.setEnabled(True)
        self.status.setText("")
        self._context.report_error(message)

    def _season_changed(self) -> None:
        season = self.season_box.currentData()
        catalog = self._league.catalog
        teams = catalog.teams(season)
        for box in (self.home_box, self.away_box):
            box.clear()
            box.addItems(teams)
        self.away_box.setCurrentIndex(1 if len(teams) > 1 else 0)
        first_day, last_day = season_date_window(season)
        self.date_edit.setDateRange(_qdate(first_day), _qdate(last_day))
        days = [match.match_date for match in catalog.season_matches(season)]
        if season == catalog.current_season:
            start = max(days) + timedelta(days=1)
        else:
            start = days[len(days) // 2]
        self.date_edit.setDate(_qdate(start))


def _qdate(day: date) -> QDate:
    return QDate(day.year, day.month, day.day)
