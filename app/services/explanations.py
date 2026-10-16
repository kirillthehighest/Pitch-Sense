"""The plain sentences of the match and team pages (Phase 19, shared with the web interface in
Phase 22): what each model looks at, what happened or will happen, which matches the predictions
use, once played which models expected the result, and what the K-Means profiles are."""

from datetime import timedelta

from app.prediction.outputs import ModelName
from app.services.formatting import date_text
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
