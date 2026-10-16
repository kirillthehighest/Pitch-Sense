"""Analiză (Phase 19): how the algorithms work, in plain words; how they did on the season in
progress; the full evaluation of the league's models and the comparison of the five leagues
(the former Modele and Ligi screens); and the sources of the data and images."""

from collections.abc import Callable

from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from app.services.explanations import (
    EXPLANATIONS,
    IMAGES_NOTE,
    SOURCES,
    crest_count,
    photo_credits,
)
from app.services.formatting import date_text, number, percent, quantity, season_text
from app.services.labels import model_label
from app.services.predictions import SeasonCheck
from app.services.registry import LeagueServices
from app.ui.algorithm_comparison import AlgorithmComparisonTab
from app.ui.context import AppContext
from app.ui.leagues import LeaguesTab
from app.ui.widgets import PageTabs, card, fill_table, label, make_table

TABS = ("Cum funcționează", "Sezonul curent", "Modele", "Ligi", "Surse")
CHECK_HEADERS = ["Model", "Meciuri", "Acuratețe", "Scor Brier", "Pierdere logaritmică"]


def interval_text(value: float, standard_error: float | None, digits: int) -> str:
    """A value with its 95% margin: 0,5776 ± 0,0123."""
    if standard_error is None:
        return number(value, digits)
    return f"{number(value, digits)} ± {number(1.96 * standard_error, digits)}"


class AnalysisPage(QWidget):
    """The tabs of the analysis; the models and leagues tabs are the earlier screens."""

    title = "Analiză"
    subtitle = (
        "Cum funcționează algoritmii, cât de bine prezic și cum diferă ligile, din rulări "
        "reale, cronologice."
    )

    def __init__(self, context: AppContext, choose_league: Callable[[str], None]) -> None:
        super().__init__()
        self._context = context
        self._league: LeagueServices | None = None
        self.models = AlgorithmComparisonTab(context)
        self.leagues = LeaguesTab(context, choose_league)
        self.views = PageTabs()
        self.views.addTab(self._explanations(), TABS[0])
        self.views.addTab(self._season_check(), TABS[1])
        self.views.addTab(self.models, TABS[2])
        self.views.addTab(self.leagues, TABS[3])
        self.views.addTab(self._sources(), TABS[4])
        self.views.currentChanged.connect(lambda _: self.refresh())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.views)

    def show_league(self, league: LeagueServices) -> None:
        self._league = league
        self.models.show_league(league)
        self.leagues.show_league(league)
        self.show_check()

    def refresh(self) -> None:
        """Re-read what may have changed elsewhere: the logs and the season's predictions."""
        self.models.refresh()
        self.leagues.refresh()
        self.show_check()

    def show_check(self) -> None:
        """The models on the season in progress, once the league's predictions are ready."""
        league = self._league
        if league is None:
            return
        season = league.catalog.current_season
        if season is None:
            self._check_message(
                "Sezonul în desfășurare nu a fost descărcat. Apasă „Actualizează datele”."
            )
            return
        if not league.predictions.is_prepared:
            self._check_message("Predicțiile ligii se pregătesc…")
            return
        self._show_check(league.predictions.season_check(season))

    def _show_check(self, check: SeasonCheck) -> None:
        league = self._league
        if not check.models:
            self._check_message(
                f"Niciun meci al sezonului {season_text(check.season)} nu are încă predicțiile "
                "tuturor modelelor."
            )
            return
        fill_table(
            self.check_table,
            [
                [
                    model_label(str(model.model)),
                    str(check.matches),
                    percent(model.accuracy.value),
                    interval_text(model.brier_score.value, model.brier_score.standard_error, 4),
                    interval_text(model.log_loss.value, model.log_loss.standard_error, 4),
                ]
                for model in check.models
            ],
            fit=True,
        )
        self.check_table.show()
        self.check_label.setText(
            f"{league.name} {season_text(check.season)}: "
            f"{quantity(check.matches, 'meci jucat', 'meciuri jucate')} între "
            f"{date_text(check.first_day)} și {date_text(check.last_day)}, fiecare prezis înainte "
            "să se joace. Marjele (±) sunt intervale de 95%. Sunt puține meciuri, așa că "
            "diferențele dintre modele nu sunt încă sigure; evaluarea completă, pe 16 sezoane, "
            "este în fila Modele. Acest sezon nu face parte din ea."
        )

    def _check_message(self, text: str) -> None:
        fill_table(self.check_table, [])
        self.check_table.hide()
        self.check_label.setText(text)

    def _explanations(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(16)
        for title, text in EXPLANATIONS:
            frame, frame_layout = card(title)
            frame_layout.addWidget(label(text, wrap=True))
            layout.addWidget(frame)
        layout.addStretch()
        return page

    def _season_check(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        frame, frame_layout = card("Cum au prezis modelele sezonul în desfășurare")
        self.check_table = make_table(CHECK_HEADERS, stretch_column=0)
        self.check_label = label(role="caption", wrap=True)
        frame_layout.addWidget(self.check_table)
        frame_layout.addWidget(self.check_label)
        frame.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        layout.addWidget(frame)
        layout.addStretch()
        return page

    def _sources(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        frame, frame_layout = card("Sursele datelor și ale imaginilor")
        crests = quantity(crest_count(), "stemă", "steme")
        for title, text in SOURCES:
            frame_layout.addWidget(label(title.upper(), "overline"))
            frame_layout.addWidget(label(text, wrap=True))
            if title == "Stemele cluburilor":
                frame_layout.addWidget(label(f"{crests} în aplicație.", "caption"))
        frame_layout.addWidget(label("IMAGINILE LIGILOR", "overline"))
        for line in photo_credits() or ["Nicio imagine inclusă."]:
            frame_layout.addWidget(label(line, wrap=True))
        frame_layout.addWidget(label(IMAGES_NOTE, "caption", wrap=True))
        layout.addWidget(frame)
        layout.addStretch()
        return page
