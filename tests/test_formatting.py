"""What the user reads: numbers, dates, seasons and names written the Romanian way."""

from datetime import date

import pytest

from app.data.competitions import COMPETITIONS
from app.evaluation.backtesting import ALWAYS_HOME_WIN, MODEL_ORDER, PAST_FREQUENCIES
from app.evaluation.comparison import Measure
from app.services.formatting import (
    date_text,
    integer,
    number,
    percent,
    quantity,
    season_text,
    signed,
)
from app.services.labels import (
    MEASURE_LABELS,
    OUTCOME_LABELS,
    country_label,
    model_label,
    outcome_label,
)


def test_numbers_use_a_decimal_comma_and_a_true_minus_sign():
    assert number(0.57764) == "0,5776"
    assert number(1.5, 2) == "1,50"
    assert number(-0.0073) == "−0,0073"
    assert number(None) == "–"


def test_differences_always_show_their_sign():
    assert signed(0.0051) == "+0,0051"
    assert signed(-0.0073) == "−0,0073"
    assert signed(0.4, 2) == "+0,40"


def test_percentages():
    assert percent(0.534) == "53,4%"
    assert percent(0.5, 0) == "50%"
    assert percent(-0.012) == "−1,2%"


def test_thousands_are_separated_by_a_dot():
    assert integer(28893) == "28.893"
    assert integer(380) == "380"
    assert integer(1_234_567) == "1.234.567"


def test_dates_and_seasons():
    assert date_text(date(2025, 10, 26)) == "26.10.2025"
    assert date_text(date(2006, 9, 4)) == "04.09.2006"
    assert season_text("2006-07") == "2006/07"


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (0, "0 meciuri"),
        (1, "1 meci"),
        (2, "2 meciuri"),
        (19, "19 meciuri"),
        (20, "20 de meciuri"),
        (38, "38 de meciuri"),
        (100, "100 de meciuri"),
        (101, "101 meciuri"),
        (119, "119 meciuri"),
        (120, "120 de meciuri"),
        (6080, "6.080 de meciuri"),
        (1005, "1.005 meciuri"),
    ],
)
def test_counts_follow_the_romanian_rule_for_de(count, expected):
    assert quantity(count, "meci", "meciuri") == expected


def test_every_model_of_the_log_has_a_romanian_name():
    assert [model_label(model) for model in MODEL_ORDER] == [
        "Elo",
        "Poisson",
        "Regresie logistică",
        "Frecvențele trecute",
        "Mereu victoria gazdelor",
    ]
    assert model_label(PAST_FREQUENCIES) != PAST_FREQUENCIES
    assert model_label(ALWAYS_HOME_WIN) != ALWAYS_HOME_WIN
    assert model_label("Something new") == "Something new"


def test_outcomes_and_measures_have_romanian_names():
    assert [outcome_label(code) for code in "HDA"] == ["Victorie gazde", "Egal", "Victorie oaspeți"]
    assert set(OUTCOME_LABELS) == {"H", "D", "A"}
    assert set(MEASURE_LABELS) == set(Measure)
    with pytest.raises(KeyError):
        outcome_label("X")


def test_every_league_has_a_romanian_country():
    assert [country_label(code) for code in COMPETITIONS] == [
        "Anglia",
        "Spania",
        "Italia",
        "Germania",
        "Franța",
    ]
    assert country_label("XX") == ""
