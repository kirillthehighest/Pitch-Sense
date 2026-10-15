"""The main window: the top bar with the four screens (Meciuri, Clasament, Echipe, Analiză),
the leagues on the left, the hero banner and the screens.

The application entry point (``main``) also lives here.
"""

import sys
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app import __version__
from app.data.competitions import competition
from app.data.live import UpdateSummary, copy_bundled_live
from app.data.paths import copy_bundled_results
from app.services.formatting import season_text
from app.services.labels import country_label
from app.services.predictions import MatchForecast
from app.services.preferences import FavouriteTeam
from app.services.updates import summary_text, updated_text
from app.ui.analysis import AnalysisPage
from app.ui.brand import Lockup, app_icon, flag_pixmap, league_photo, photo_credit
from app.ui.context import AppContext, default_context
from app.ui.matches import MatchesPage
from app.ui.standings import StandingsPage
from app.ui.team_page import TeamPage
from app.ui.theme import apply_theme
from app.ui.widgets import BrandStripe, HeroBanner, LeagueButton, label

WINDOW_TITLE = "PitchSense – analiza și predicția meciurilor de fotbal"
SIDE_PANEL_WIDTH = 248
NO_FAVOURITE = "Alege echipa ta"
UPDATE = "Actualizează datele"
UPDATE_TIP = (
    "Descarcă rezultatele sezonului în desfășurare (Football-Data.co.uk) și calendarul "
    "meciurilor rămase (openfootball). Restul aplicației funcționează fără internet."
)


class FavouriteDialog(QDialog):
    """Choose the team you follow: a league, then one of its teams in the latest season."""

    def __init__(self, context: AppContext, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._context = context
        self.cleared = False
        self.setWindowTitle("Echipa ta")
        self.league_box = QComboBox()
        for code in context.competitions:
            self.league_box.addItem(flag_pixmap(code, 18), competition(code).name, code)
        self.league_box.currentIndexChanged.connect(self._league_changed)
        self.team_box = QComboBox()
        self.save_button = QPushButton("Salvează")
        self.save_button.setProperty("role", "primary")
        self.save_button.clicked.connect(self.accept)
        self.clear_button = QPushButton("Fără echipă")
        self.clear_button.clicked.connect(self._clear)
        self.cancel_button = QPushButton("Renunță")
        self.cancel_button.clicked.connect(self.reject)

        form = QFormLayout()
        form.setSpacing(12)
        form.addRow("Liga", self.league_box)
        form.addRow("Echipa", self.team_box)
        buttons = QHBoxLayout()
        buttons.addWidget(self.clear_button)
        buttons.addStretch()
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.save_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 22)
        layout.setSpacing(14)
        layout.addWidget(label("ECHIPA PE CARE O URMĂREȘTI", "section"))
        layout.addWidget(
            label(
                "Va fi aleasă din start și evidențiată în clasamente și pe ecranul Acasă.",
                "caption",
                wrap=True,
            )
        )
        layout.addLayout(form)
        layout.addLayout(buttons)
        self.setMinimumWidth(420)

        favourite = context.preferences.favourite
        if favourite and favourite.competition in context.competitions:
            self.league_box.setCurrentIndex(self.league_box.findData(favourite.competition))
        self._league_changed()
        if favourite:
            self.team_box.setCurrentText(favourite.team)

    def chosen(self) -> FavouriteTeam | None:
        """The team chosen, or None when the user removed it."""
        if self.cleared:
            return None
        return FavouriteTeam(self.league_box.currentData(), self.team_box.currentText())

    def _league_changed(self) -> None:
        catalog = self._context.league(self.league_box.currentData()).catalog
        self.team_box.clear()
        self.team_box.addItems(catalog.teams(catalog.seasons()[-1]))

    def _clear(self) -> None:
        self.cleared = True
        self.accept()


class MainWindow(QMainWindow):
    """Hosts the four screens, the choice of league and "your team"; prepares the predictions of
    every league in the background, the chosen league first."""

    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self._context = context
        self._league_code: str | None = None
        self._reported_problems: set[str] = set()
        self._preparing: set[str] = set()
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(app_icon())
        self.resize(1400, 900)
        self.setMinimumSize(1180, 740)

        self.matches = MatchesPage(
            context, self.open_standings, self.open_team, self.open_favourite_dialog
        )
        self.standings = StandingsPage(context, self.open_team)
        self.team_page = TeamPage(context, self.open_match)
        self.analysis = AnalysisPage(context, self.show_league)
        self.pages = (self.matches, self.standings, self.team_page, self.analysis)

        self.stack = QStackedWidget()
        self.stack.setObjectName("pages")
        self.scrolls: list[QScrollArea] = []
        for page in self.pages:
            scroll = QScrollArea()
            scroll.setWidget(page)
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            page.setObjectName("page")
            self.stack.addWidget(scroll)
            self.scrolls.append(scroll)
        self.hero = HeroBanner()
        self.page_title = self.hero.title_label
        self.page_subtitle = self.hero.subtitle_label

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._top_bar())
        layout.addWidget(BrandStripe())
        body = QHBoxLayout()
        body.setSpacing(0)
        body.addWidget(self._side_panel())
        main = QVBoxLayout()
        main.setSpacing(0)
        main.addWidget(self.hero)
        pages = QVBoxLayout()
        pages.setContentsMargins(28, 22, 28, 8)
        pages.addWidget(self.stack)
        main.addLayout(pages, stretch=1)
        body.addLayout(main, stretch=1)
        layout.addLayout(body, stretch=1)
        self.setCentralWidget(central)

        self.show_favourite()
        self.show_league(context.first_league)
        self.show_page(0)
        self._prepare_next()

    @property
    def current_league(self) -> str:
        return self._league_code

    def show_page(self, index: int) -> None:
        """Bring a screen to the front; screens that read results re-read them."""
        page = self.pages[index]
        self.stack.setCurrentIndex(index)
        self.nav_buttons[index].setChecked(True)
        self.hero.show_page(page.title, page.subtitle)
        if page is self.matches:
            page.show_list()
        if page in (self.matches, self.analysis):
            page.refresh()  # a log or a league's predictions may be ready since

    def show_league(self, code: str) -> None:
        """Show every screen for one league and prepare its predictions in the background."""
        if code == self._league_code:
            return
        self._league_code = code
        self.league_buttons[code].setChecked(True)
        league = self._context.league(code)
        self._context.preferences.set_competition(code)
        catalog = league.catalog
        seasons = catalog.seasons()
        self.hero.show_league(
            f"{league.name} · {country_label(code)} · "
            f"{season_text(seasons[0])}–{season_text(seasons[-1])}",
            flag_pixmap(code, 18),
            league_photo(code),
            photo_credit(code),
        )
        self.version_note.setText(self._note(catalog.updated_at))
        for page in self.pages:
            page.show_league(league)
        if catalog.live_problem and catalog.live_problem not in self._reported_problems:
            self._reported_problems.add(catalog.live_problem)
            self._context.report_error(
                f"Sezonul în desfășurare pentru {league.name} nu a putut fi citit, așa că sunt "
                "arătate doar sezoanele încheiate. Apăsați „Actualizează datele” ca să-l "
                f"descărcați din nou.\n\nDetalii: {catalog.live_problem}"
            )
        self._prepare(code)

    def open_standings(self, code: str) -> None:
        self.show_league(code)
        self.show_page(self.pages.index(self.standings))

    def open_team(self, code: str, team: str, season: str | None = None) -> None:
        """Open a team's page, in ``season`` or else the latest season it played."""
        self.show_league(code)
        self.team_page.show_team(team, season)
        self.show_page(self.pages.index(self.team_page))
        self.scrolls[self.pages.index(self.team_page)].verticalScrollBar().setValue(0)

    def open_match(self, forecast: MatchForecast) -> None:
        self.show_page(self.pages.index(self.matches))
        self.matches.show_match(forecast)
        self.scrolls[self.pages.index(self.matches)].verticalScrollBar().setValue(0)

    def update_data(self) -> None:
        """Download the season in progress in the background, then show it in every screen."""
        self.update_button.setEnabled(False)
        self.update_button.setText("Se actualizează…")
        self.statusBar().showMessage(
            "Se descarcă rezultatele și calendarul sezonului în desfășurare…"
        )
        self._context.run_task(self._context.update_data, self._updated, self._update_failed)

    def _updated(self, summary: UpdateSummary) -> None:
        self._reset_update_button()
        self._context.reload()
        self._preparing.clear()
        self.matches.day = None  # open on the next day with matches of the new data
        code, self._league_code = self._league_code, None
        self.show_league(code)
        self._prepare_next()
        self.statusBar().showMessage(f"Date actualizate. {summary_text(summary)}", 15000)

    def _update_failed(self, message: str) -> None:
        self._reset_update_button()
        self.statusBar().clearMessage()
        self._context.report_error(
            "Datele nu au putut fi actualizate; au rămas cele de până acum. Verificați conexiunea "
            f"la internet și încercați din nou.\n\nDetalii: {message}"
        )

    def _reset_update_button(self) -> None:
        self.update_button.setEnabled(True)
        self.update_button.setText(UPDATE)

    def open_favourite_dialog(self) -> FavouriteDialog:
        """Open the dialog to choose "your team"; returns it (it is not modal for the code)."""
        dialog = FavouriteDialog(self._context, self)
        dialog.accepted.connect(lambda: self._favourite_chosen(dialog.chosen()))
        dialog.open()
        return dialog

    def show_favourite(self) -> None:
        favourite = self._context.preferences.favourite
        self.favourite_button.setText(f"Echipa ta: {favourite.team}" if favourite else NO_FAVOURITE)

    def _favourite_chosen(self, favourite: FavouriteTeam | None) -> None:
        self._context.preferences.set_favourite(favourite)
        self.show_favourite()
        if favourite and favourite.competition != self.current_league:
            self.show_league(favourite.competition)
        else:
            for page in self.pages:
                page.show_league(self._context.league(self.current_league))

    def _prepare(self, code: str) -> None:
        """Predict a league's matches in the background, once."""
        league = self._context.league(code)
        if league.predictions.is_prepared or code in self._preparing:
            return
        self._preparing.add(code)
        if code == self._league_code:
            self.statusBar().showMessage(f"Se pregătesc predicțiile pentru {league.name}…")
        self._context.run_task(
            league.predictions.prepare,
            lambda _: self._prepared(code),
            lambda message: self._prepare_failed(code, message),
        )

    def _prepared(self, code: str) -> None:
        self._preparing.discard(code)
        name = self._context.league(code).name
        self.statusBar().showMessage(f"Predicțiile pentru {name} sunt gata", 6000)
        self.matches.league_ready(code)
        if code == self._league_code:
            self.team_page.refresh()
            self.analysis.show_check()
        self._prepare_next()

    def _prepare_failed(self, code: str, message: str) -> None:
        self._preparing.discard(code)
        self._failed(message)

    def _prepare_next(self) -> None:
        """Prepare the next league that is not ready, one at a time."""
        if self._preparing:
            return
        for code in self._context.competitions:
            if not self._context.league(code).predictions.is_prepared:
                self._prepare(code)
                return

    def _failed(self, message: str) -> None:
        self.statusBar().clearMessage()
        self._context.report_error(message)

    def _top_bar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("topbar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(24, 0, 24, 0)
        layout.setSpacing(4)
        layout.addWidget(Lockup(40))
        layout.addSpacing(36)
        group = QButtonGroup(self)
        group.setExclusive(True)
        self.nav_buttons: list[QPushButton] = []
        for index, page in enumerate(self.pages):
            button = QPushButton(page.title.upper())
            button.setProperty("role", "nav")
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _, i=index: self.show_page(i))
            group.addButton(button)
            layout.addWidget(button)
            self.nav_buttons.append(button)
        layout.addStretch()
        self.update_button = QPushButton(UPDATE)
        self.update_button.setToolTip(UPDATE_TIP)
        self.update_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.update_button.clicked.connect(self.update_data)
        layout.addWidget(self.update_button)
        layout.addSpacing(10)
        self.favourite_button = QPushButton()
        self.favourite_button.setProperty("role", "favourite")
        self.favourite_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.favourite_button.clicked.connect(self.open_favourite_dialog)
        layout.addWidget(self.favourite_button)
        return bar

    def _side_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("sidepanel")
        panel.setFixedWidth(SIDE_PANEL_WIDTH)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 22, 0, 18)
        layout.setSpacing(2)
        heading = label("COMPETIȚII", "overline")
        heading.setContentsMargins(22, 0, 0, 8)
        layout.addWidget(heading)
        group = QButtonGroup(self)
        group.setExclusive(True)
        self.league_buttons: dict[str, LeagueButton] = {}
        for code in self._context.competitions:
            button = LeagueButton(
                code, competition(code).name, country_label(code), flag_pixmap(code, 24)
            )
            button.clicked.connect(lambda _, c=code: self.show_league(c))
            group.addButton(button)
            layout.addWidget(button)
            self.league_buttons[code] = button
        layout.addStretch()
        note = label(self._note(None), "sidebar-note")
        note.setWordWrap(True)
        self.version_note = note
        note.setContentsMargins(22, 0, 12, 0)
        layout.addWidget(note)
        return panel

    @staticmethod
    def _note(updated_at: datetime | None) -> str:
        """The side panel's note: the version, the sources and the last update."""
        update = f"Actualizat: {updated_text(updated_at)}" if updated_at else "Sezonul curent: —"
        return (
            f"PitchSense {__version__}\nRezultate: Football-Data.co.uk\n"
            f"Calendar: openfootball (CC0)\n{update}\nUTM · APA · TI-251"
        )


def main() -> int:
    """Start the application; returns the exit code."""
    application = QApplication.instance() or QApplication(sys.argv)
    application.setApplicationName("PitchSense")
    apply_theme(application)
    application.setWindowIcon(app_icon())
    try:
        copy_bundled_results()  # a packaged application ships its prediction logs read-only
    except OSError as error:  # without the copy the logs can still be rebuilt in the window
        QMessageBox.warning(
            None, "PitchSense", f"Jurnalele predicțiilor nu au putut fi copiate: {error}"
        )
    try:
        copy_bundled_live()  # and a snapshot of the season in progress
    except (OSError, ValueError) as error:  # it can be downloaded again in the window
        QMessageBox.warning(
            None, "PitchSense", f"Datele sezonului în desfășurare nu au putut fi copiate: {error}"
        )
    try:
        context = default_context()
    except FileNotFoundError as error:
        QMessageBox.critical(
            None,
            "PitchSense",
            "Baza de date nu a fost găsită. Construiți-o cu comanda de mai jos și porniți "
            f"aplicația din nou.\n\n{error}",
        )
        return 1
    window = MainWindow(context)
    window.show()
    return application.exec()
