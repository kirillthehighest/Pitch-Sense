"""The Romanian names the user sees for models, outcomes and measures.

The code and the prediction logs keep their English identifiers (``ModelName``, ``H``/``D``/``A``);
only what is displayed is translated, here, in one place.
"""

from app.evaluation.backtesting import ALWAYS_HOME_WIN, PAST_FREQUENCIES
from app.evaluation.comparison import MATCHUP_TYPES, Measure
from app.prediction.outputs import ModelName
from app.services.formatting import season_text

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


# The types of match of the comparison's breakdown, in the order of MATCHUP_TYPES
MATCHUP_LABELS = dict(
    zip(
        MATCHUP_TYPES,
        (
            "cu o echipă promovată",
            "cu o echipă de elită",
            "echipe din același grup",
            "echipe din grupuri diferite",
        ),
        strict=True,
    )
)


def subset_label(label_text: str) -> str:
    """The Romanian name of a subset: a season, an actual result or a type of match."""
    if label_text in OUTCOME_LABELS:
        return OUTCOME_LABELS[label_text]
    return MATCHUP_LABELS.get(label_text, season_text(label_text))
