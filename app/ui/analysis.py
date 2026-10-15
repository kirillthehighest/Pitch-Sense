"""Analiză (Phase 19): how the algorithms work, in plain words; how they did on the season in
progress; the full evaluation of the league's models and the comparison of the five leagues
(the former Modele and Ligi screens); and the sources of the data and images."""

import json
from collections.abc import Callable

from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from app.data.competitions import competition
from app.services.formatting import date_text, number, percent, quantity, season_text
from app.services.labels import model_label
from app.services.predictions import SeasonCheck
from app.ui.algorithm_comparison import AlgorithmComparisonTab
from app.ui.brand import CRESTS_DIR, LEAGUE_PHOTOS_DIR
from app.ui.context import AppContext, LeagueServices
from app.ui.leagues import LeaguesTab
from app.ui.widgets import PageTabs, card, fill_table, label, make_table

TABS = ("Cum funcționează", "Sezonul curent", "Modele", "Ligi", "Surse")
EXPLANATIONS = (
    (
        "Ratingul Elo",
        "Fiecare echipă are un număr care îi arată puterea. După fiecare meci, câștigătoarea ia "
        "puncte de la învinsă: mai multe dacă a învins o echipă mai puternică, mai puține dacă "
        "era favorită. Din diferența de rating (plus avantajul terenului propriu) rezultă șansa "
        "fiecărei echipe; șansa de egal a fost învățată din meciurile trecute.",
    ),
    (
        "Modelul Poisson",
        "Estimează câte goluri va marca fiecare echipă, din cât marchează ea și cât primește "
        "adversarul, acasă și în deplasare, față de media ligii. Din cele două medii rezultă "
        "probabilitatea fiecărui scor (0–0, 1–0, 2–1...), iar din scoruri, șansele de victorie, "
        "egal și înfrângere. Presupune că golurile celor două echipe nu depind unele de altele, "
        "de aceea subestimează puțin egalurile.",
    ),
    (
        "Regresia logistică",
        "Primește cinci diferențe dintre gazde și oaspeți (rating Elo, puncte și goluri pe meci, "
        "forma recentă, șuturi pe poartă) și a învățat, din toate meciurile trecute, cât "
        "contează fiecare. Este reantrenată în fiecare luni, doar pe meciurile deja jucate.",
    ),
    (
        "K‑Means",
        "Nu prezice meciuri: grupează echipele după profilul lor dintr-un sezon (goluri, șuturi, "
        "puncte, acasă față de deplasare) în patru grupuri, de la Elită la Slabă peste tot. "
        "Grupurile arată ce fel de echipă este fiecare și unde se descurcă bine sau prost "
        "fiecare model.",
    ),
    (
        "Cum sunt verificate",
        "Ca în viața reală: meciurile sunt parcurse în ordinea datelor, fiecare predicție "
        "folosește doar meciurile jucate înaintea ei, iar rezultatul se află abia după. "
        "Sezonul 2006/07 doar pornește modelele, 2007/08–2009/10 au servit la alegerea "
        "setărilor, iar rezultatele raportate vin din 2010/11–2025/26.",
    ),
    (
        "Cum citești măsurile",
        "Acuratețea: cât de des rezultatul cel mai probabil s-a întâmplat. Scorul Brier: cât de "
        "departe au fost probabilitățile de rezultat (0 ar fi perfect; mai mic e mai bine). "
        "Pierderea logaritmică: pedepsește mult o predicție sigură pe ea și greșită. "
        "O diferență între modele este reală doar dacă intervalul ei de încredere nu conține 0.",
    ),
)
CHECK_HEADERS = ["Model", "Meciuri", "Acuratețe", "Scor Brier", "Pierdere logaritmică"]
SOURCES = (
    (
        "Rezultatele",
        "Football-Data.co.uk: sezoanele 2006/07–2025/26 ale celor cinci ligi și rezultatele "
        "sezonului în desfășurare.",
    ),
    (
        "Calendarul",
        "openfootball/football.json, domeniu public (CC0 1.0): meciurile programate ale "
        "sezonului în desfășurare.",
    ),
    (
        "Stemele cluburilor",
        "Wikipedia (articolele cluburilor), la rezoluție mică. Stemele sunt mărci ale "
        "cluburilor; sunt folosite doar ca să recunoști echipele, într-un proiect universitar "
        "privat. Fiecare stemă, cu articolul și fișierul ei: app/ui/assets/crests/sources.json.",
    ),
    (
        "Literele",
        "Barlow Condensed și Libre Franklin, SIL Open Font License 1.1.",
    ),
)


def interval_text(value: float, standard_error: float | None, digits: int) -> str:
    """A value with its 95% margin: 0,5776 ± 0,0123."""
    if standard_error is None:
        return number(value, digits)
    return f"{number(value, digits)} ± {number(1.96 * standard_error, digits)}"


def photo_credits() -> list[str]:
    """One line per league image: the league and where the image comes from."""
    path = LEAGUE_PHOTOS_DIR / "sources.json"
    if not path.is_file():
        return []
    return [
        f"{competition(entry['competition']).name}: imagine promoțională, sursa {entry['source']}."
        for entry in json.loads(path.read_text(encoding="utf-8"))
    ]


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
        crests = quantity(len(list(CRESTS_DIR.glob("*.png"))), "stemă", "steme")
        for title, text in SOURCES:
            frame_layout.addWidget(label(title.upper(), "overline"))
            frame_layout.addWidget(label(text, wrap=True))
            if title == "Stemele cluburilor":
                frame_layout.addWidget(label(f"{crests} în aplicație.", "caption"))
        frame_layout.addWidget(label("IMAGINILE LIGILOR", "overline"))
        for line in photo_credits() or ["Nicio imagine inclusă."]:
            frame_layout.addWidget(label(line, wrap=True))
        frame_layout.addWidget(
            label(
                "Imaginile au fost alese de echipă. Drepturile asupra lor, ale jucătorilor, "
                "siglelor și sponsorilor aparțin deținătorilor lor; sunt folosite doar în acest "
                "proiect universitar privat și nu se publică.",
                "caption",
                wrap=True,
            )
        )
        layout.addWidget(frame)
        layout.addStretch()
        return page
