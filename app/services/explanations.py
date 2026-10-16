"""The plain sentences of the interface (Phase 19, shared with the web interface in Phase 22):
on a match's page what each model looks at, what happened or will happen, which matches the
predictions use and, once played, which models expected the result; on a team's page what the
K-Means profiles are; in Analiză how the algorithms work and where the data and images come
from."""

import json
from datetime import timedelta

from app.data.competitions import competition
from app.prediction.outputs import ModelName
from app.services.formatting import date_text
from app.services.images import CRESTS_DIR, LEAGUE_PHOTOS_DIR, STADIUMS_DIR
from app.services.labels import model_label, outcome_label
from app.services.predictions import MatchForecast

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

# The K-Means profiles of a team page (the description itself is shown in Analiză)
GROUPS_EXPLANATION = (
    "K‑Means grupează echipele după șase valori pe meci ale unui sezon: goluri marcate și primite, "
    "șuturi pe poartă date și primite, puncte și diferența dintre punctele de acasă și din "
    "deplasare. Rezultă patru profiluri: Elită, Jumătatea de sus, Jumătatea de jos (puternică "
    "acasă) și Slabă peste tot. Grupul de dinaintea sezonului vine din sezonul anterior; grupul "
    "sezonului descrie sezonul încheiat."
)
GROUPS_IN_PROGRESS = (
    "Sezonul este în desfășurare. Grupurile K‑Means descriu sezoane încheiate, așa că apar după "
    "ultimul meci al sezonului."
)
GROUPS_NO_STATISTICS = "Sezonul nu are statistici de șuturi, deci echipele nu pot fi grupate."


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


# Analiză: how the algorithms work, in plain words
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

# Analiză: the sources of the data and images
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
        "Fotografiile stadioanelor",
        "Wikipedia și Wikimedia Commons: fotografia din articolul stadionului fiecărui club, la "
        "1024 px. Fotografiile aparțin autorilor lor; sunt folosite doar în acest proiect "
        "universitar privat și nu se publică. Fiecare fotografie, cu stadionul și fișierul ei: "
        "app/ui/assets/stadiums/sources.json.",
    ),
    (
        "Literele",
        "Kanit (sigla), Barlow Condensed și Plus Jakarta Sans, SIL Open Font License 1.1.",
    ),
)
IMAGES_NOTE = (
    "Imaginile au fost alese de echipă. Drepturile asupra lor, ale jucătorilor, siglelor și "
    "sponsorilor aparțin deținătorilor lor; sunt folosite doar în acest proiect universitar privat "
    "și nu se publică."
)


def crest_count() -> int:
    """How many club crests the application carries."""
    return len(list(CRESTS_DIR.glob("*.png")))


def stadium_photo_count() -> int:
    """How many stadium photos the application carries."""
    return len(list(STADIUMS_DIR.glob("*.jpg")))


def photo_credits() -> list[str]:
    """One line per league image: the league and where the image comes from."""
    path = LEAGUE_PHOTOS_DIR / "sources.json"
    if not path.is_file():
        return []
    return [
        f"{competition(entry['competition']).name}: imagine promoțională, sursa {entry['source']}."
        for entry in json.loads(path.read_text(encoding="utf-8"))
    ]
