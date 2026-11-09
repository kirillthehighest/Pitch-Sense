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


def test_poisson_gives_the_score_of_its_pick_and_the_likeliest_overall():
    grid = np.array([[0.10, 0.08], [0.11, 0.13]])  # home goals x away goals

    text = poisson_reason((1.62, 0.94), grid, "H")

    assert text.startswith("Goluri așteptate: gazdele 1,62, oaspeții 0,94.")
    assert "cel mai probabil scor e 1–0 (11,0%)" in text
    assert text.endswith("În general, cel mai probabil e 1–1 (13,0%).")
    assert "În general" not in poisson_reason((1.0, 1.0), grid, "D")  # the same score: said once


def test_logistic_regression_never_contradicts_its_pick():
    assert "îi vede totuși favoriți pe gazde" in logistic_reason(WEAK, STRONG, "H")
    assert "îi vede totuși favoriți pe oaspeți" in logistic_reason(STRONG, WEAK, "A")
    assert logistic_reason(STRONG, WEAK, "H").endswith("ele îi arată favoriți pe gazde.")
    assert "2,20 față de 1,40 puncte pe meci" in logistic_reason(STRONG, WEAK, "H")
