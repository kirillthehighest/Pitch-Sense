"""Each model's reasoning about one match (Phase 27): what it looks at, this match's numbers and
the result they give, written so a reader can follow and check them."""

import numpy as np

from app.services.explanations import Side, elo_reason, logistic_reason, poisson_reason

STRONG = Side(rating=1650.0, points=22, played=10, form=("W", "W", "W", "D", "W"))
WEAK = Side(rating=1580.0, points=14, played=10, form=("L", "D", "W", "L", "L"))


def test_elo_says_both_ratings_the_gap_and_what_it_means():
    assert elo_reason(STRONG, WEAK, 100, "H", 0.62) == (
        "Elo măsoară puterea fiecărei echipe din toate rezultatele ei: gazdele au ratingul 1.650, "
        "oaspeții 1.580. Terenul propriu adaugă gazdelor 100 de puncte, deci diferența este de "
        "170 de puncte în favoarea gazdelor: un avantaj mare al gazdelor. Cel mai probabil "
        "rezultat: victoria gazdelor (62%)."
    )
    assert "30 de puncte în favoarea oaspeților: un meci echilibrat" in elo_reason(
        WEAK, STRONG, 40, "A", 0.4
    )
    # the gap is the sum of the numbers shown: 1.613 + 100 − 1.765 = −52, not −53
    halves = elo_reason(Side(1612.6, 0, 0, ()), Side(1765.4, 0, 0, ()), 100, "A", 0.5)
    assert "52 de puncte în favoarea oaspeților: un avantaj clar al oaspeților" in halves


def test_poisson_explains_the_exact_score_against_the_most_likely_result():
    grid = np.array([[0.10, 0.08], [0.11, 0.13]])  # home goals x away goals

    text = poisson_reason((1.62, 0.94), grid, "H", 0.42)

    assert "gazdele în medie 1,62, oaspeții 0,94" in text
    assert "Cel mai probabil scor exact este 1–1 (13,0%)" in text
    assert text.endswith(
        "cel mai probabil rezultat este victoria gazdelor (42%); dacă se întâmplă, scorul cel mai "
        "probabil este 1–0."
    )
    assert "dacă se întâmplă" not in poisson_reason((1.0, 1.0), grid, "D", 0.4)  # the same score


def test_logistic_regression_says_who_each_value_favours_and_never_contradicts_its_pick():
    text = logistic_reason(STRONG, WEAK, "H", 0.55)
    assert "2,20 față de 1,40 puncte pe meci în sezon (în favoarea gazdelor)" in text
    assert text.endswith("Adunate, cu avantajul terenului propriu, dau: victoria gazdelor (55%).")
    turned = logistic_reason(WEAK, STRONG, "H", 0.41)
    assert "Deși 3 din cele 3 cifre sunt în favoarea oaspeților" in turned
    assert turned.endswith("înclină balanța: victoria gazdelor (41%).")
    one = Side(rating=1500.0, points=1, played=5, form=("D", "L", "L", "L", "L"))
    assert "față de 1 punct în ultimele 5 meciuri" in logistic_reason(STRONG, one, "H", 0.6)
