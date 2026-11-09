"""Each model's reasoning about one match (Phase 27): written from that match's own numbers."""

import numpy as np

from app.services.explanations import Side, elo_reason, logistic_reason, poisson_reason

STRONG = Side(rating=1650.0, points=22, played=10, form=("W", "W", "W", "D", "W"))
WEAK = Side(rating=1580.0, points=14, played=10, form=("L", "D", "W", "L", "L"))


def test_elo_says_both_ratings_and_who_starts_ahead():
    assert elo_reason(STRONG, WEAK, 100) == (
        "Ratingul Elo înaintea meciului: gazdele 1.650, oaspeții 1.580. Terenul propriu valorează "
        "100 de puncte, deci gazdele pornesc cu 170 de puncte înainte."
    )
    assert "oaspeții rămân cu 30 de puncte înainte" in elo_reason(WEAK, STRONG, 40)
    # the lead is the sum of the numbers shown: 1.613 + 100 − 1.765 = −52, not −53
    halves = elo_reason(Side(1612.6, 0, 0, ()), Side(1765.4, 0, 0, ()), 100)
    assert "oaspeții rămân cu 52 de puncte înainte" in halves


def test_poisson_gives_the_score_of_its_pick_and_the_likeliest_overall():
    grid = np.array([[0.10, 0.08], [0.11, 0.13]])  # home goals x away goals

    text = poisson_reason(grid, "H")

    assert "dacă câștigă gazdele, cel mai probabil scor e 1–0 (11,0%)" in text
    assert text.endswith("Luat singur, cel mai probabil scor e 1–1 (13,0%).")
    assert "Luat singur" not in poisson_reason(grid, "D")  # the same score: said once


def test_logistic_regression_never_contradicts_its_pick():
    assert "îi vede totuși favoriți pe gazde" in logistic_reason(WEAK, STRONG, "H")
    assert "îi vede totuși favoriți pe oaspeți" in logistic_reason(STRONG, WEAK, "A")
    assert logistic_reason(STRONG, WEAK, "H").endswith("ele îi arată favoriți pe gazde.")
    assert "2,20 față de 1,40 puncte pe meci" in logistic_reason(STRONG, WEAK, "H")
    one = Side(rating=1500.0, points=1, played=5, form=("D", "L", "L", "L", "L"))
    assert "față de 1 punct în ultimele 5 meciuri" in logistic_reason(STRONG, one, "H")
