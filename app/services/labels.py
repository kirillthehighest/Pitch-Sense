"""The Romanian names the user sees for models, outcomes and measures.

The code and the prediction logs keep their English identifiers (``ModelName``, ``H``/``D``/``A``);
only what is displayed is translated, here, in one place.
"""

from app.evaluation.backtesting import ALWAYS_HOME_WIN, PAST_FREQUENCIES
from app.evaluation.comparison import Measure
from app.prediction.outputs import ModelName

MODEL_LABELS = {
    str(ModelName.ELO): "Elo",
    str(ModelName.POISSON): "Poisson",
    str(ModelName.LOGISTIC_REGRESSION): "Regresie logistică",
    PAST_FREQUENCIES: "Frecvențele trecute",
    ALWAYS_HOME_WIN: "Mereu victoria gazdelor",
}
OUTCOME_LABELS = {"H": "Victorie gazde", "D": "Egal", "A": "Victorie oaspeți"}
RESULT_LETTERS = {"W": "V", "D": "E", "L": "Î"}  # victorie, egal, înfrângere
COUNTRY_LABELS = {"E0": "Anglia", "SP1": "Spania", "I1": "Italia", "D1": "Germania", "F1": "Franța"}
MEASURE_LABELS = {
    Measure.BRIER: "scor Brier",
    Measure.LOG_LOSS: "pierdere logaritmică",
    Measure.ACCURACY: "acuratețe",
}


def model_label(model: str) -> str:
    """The Romanian name of a model; an unknown name is shown as it is."""
    return MODEL_LABELS.get(model, model)


def outcome_label(code: str) -> str:
    """The Romanian name of a result code (H, D or A)."""
    return OUTCOME_LABELS[code]


def country_label(code: str) -> str:
    """The country of a league, in Romanian; an unknown league has none."""
    return COUNTRY_LABELS.get(code, "")


def team_abbreviation(team: str) -> str:
    """Three capital letters for a team, as on a scoreboard: Barcelona -> BAR, Real Madrid -> RMA,
    Man United -> MUN, Nott'm Forest -> NFO. Letters only; a short name keeps what it has."""
    words = ["".join(c for c in word if c.isalpha()) for word in team.split()]
    words = [word for word in words if word]
    if not words:
        raise ValueError(f"a team name needs letters: {team!r}")
    if len(words) == 1:
        return words[0][:3].upper()
    return (words[0][0] + words[1][:2]).upper()
