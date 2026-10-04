"""Elo rating system for football teams, implemented from its definition.

Notation, as in docs/algorithms/elo.md:

    R_home, R_away   ratings of the two teams before the match
    H                home advantage, in rating points
    E_home           expected score of the home team                (Eq. 1)
                     E_home = 1 / (1 + 10^((R_away - R_home - H) / 400))
    S_home           actual score of the home team: 1 win, 0.5 draw, 0 loss   (Eq. 2)
    K                update factor
    Delta            K * (S_home - E_home)                           (Eq. 3)
                     R_home' = R_home + Delta,  R_away' = R_away - Delta

The away team's expected and actual scores are 1 - E_home and 1 - S_home, so every update moves
the same number of points from one team to the other and the league's total rating never changes.

E_home counts a draw as half a win, so it is not a probability of each outcome. The draw model
turns it into home/draw/away probabilities, learned from past matches:

    B                number of equal-width bins of E in [0, 1]
    b(E)             bin of an expected score: min(floor(E * B), B - 1)          (Eq. 4)
    d_b              draw rate of bin b, pulled towards the overall draw rate d   (Eq. 5)
                     d_b = (draws_b + m * d) / (matches_b + m)
    q                minimum probability kept by each result: 0.01
    P(D)             min(d_b(E), max(0, 2 * min(E, 1 - E) - 2 * q))               (Eq. 6)
    P(H), P(A)       E - P(D) / 2  and  1 - E - P(D) / 2

so P(H) + P(D) / 2 = E exactly and the three probabilities are non-negative and sum to 1.
Whenever q <= E <= 1 - q both wins keep at least q, and strictly inside these limits the draw
keeps a positive probability too, so no possible result is called impossible.
"""

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date

DEFAULT_INITIAL_RATING = 1500.0
RATING_SCALE = 400.0  # a gap of 400 points means the stronger side's expected score is 10/11
DEFAULT_DRAW_BINS = 10
DEFAULT_PRIOR_WEIGHT = 20.0  # m in Eq. 5: imaginary matches at the overall draw rate per bin
# q in Eq. 6. Without it, very uneven matches gave the underdog's win probability 0, and the
# evaluation (Phase 9) met such a match that the underdog won: Barcelona 0-2 Hercules, 2010.
MIN_OUTCOME_PROBABILITY = 0.01
_SCORES = (0.0, 0.5, 1.0)


@dataclass(frozen=True, slots=True)
class GameResult:
    """One finished match, as the Elo algorithm needs it."""

    match_date: date
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int

    def __post_init__(self) -> None:
        if not self.home_team or not self.away_team:
            raise ValueError("team names cannot be empty")
        if self.home_team == self.away_team:
            raise ValueError(f"a team cannot play itself: {self.home_team!r}")
        if self.home_goals < 0 or self.away_goals < 0:
            raise ValueError(f"goals cannot be negative: {self.home_goals}-{self.away_goals}")


def expected_score(home_rating: float, away_rating: float, home_advantage: float) -> float:
    """Eq. 1: the home team's expected score E_home, strictly between 0 and 1."""
    return 1.0 / (1.0 + 10.0 ** ((away_rating - home_rating - home_advantage) / RATING_SCALE))


def actual_score(home_goals: int, away_goals: int) -> float:
    """Eq. 2: the home team's actual score S_home: 1 for a win, 0.5 for a draw, 0 for a loss."""
    if home_goals < 0 or away_goals < 0:
        raise ValueError(f"goals cannot be negative: {home_goals}-{away_goals}")
    if home_goals > away_goals:
        return 1.0
    if home_goals < away_goals:
        return 0.0
    return 0.5


def rating_change(expected: float, actual: float, k_factor: float) -> float:
    """Eq. 3: Delta = K (S_home - E_home), gained by the home team and lost by the away team."""
    return k_factor * (actual - expected)


class EloRatings:
    """Ratings of the teams in a league, updated match by match in chronological order.

    Call ``start_season`` with the league's teams before the first match of every season, then
    ``update`` once per finished match. ``expected_home_score`` gives the prediction for a match
    from the current ratings, so it must be called before that match's result is applied.
    """

    def __init__(
        self,
        k_factor: float,
        home_advantage: float,
        initial_rating: float = DEFAULT_INITIAL_RATING,
    ) -> None:
        if not (math.isfinite(k_factor) and k_factor > 0):
            raise ValueError(f"k_factor must be a positive number, got {k_factor}")
        if not (math.isfinite(home_advantage) and home_advantage >= 0):
            raise ValueError(f"home_advantage must be zero or positive, got {home_advantage}")
        if not math.isfinite(initial_rating):
            raise ValueError(f"initial_rating must be a finite number, got {initial_rating}")
        self.k_factor = k_factor
        self.home_advantage = home_advantage
        self.initial_rating = initial_rating
        self._ratings: dict[str, float] = {}
        self._last_match_date: date | None = None

    @property
    def ratings(self) -> Mapping[str, float]:
        """A copy of the current ratings of the league's teams."""
        return dict(self._ratings)

    def rating(self, team: str) -> float:
        """Return the current rating of a team in the league."""
        if team not in self._ratings:
            raise ValueError(f"{team!r} is not in the league; add it with start_season")
        return self._ratings[team]

    def start_season(self, teams: Iterable[str]) -> None:
        """Set the league's teams for a new season.

        The first season starts every team at the initial rating. Later, teams that stay keep
        their rating, teams that left are removed, and teams that joined (promoted, or returning
        after an absence) start at the average rating of the teams that left. With as many teams
        joining as leaving, the league's total and average rating stay unchanged. If no team
        left, joining teams start at the league's current average rating.
        """
        teams = set(teams)
        if len(teams) < 2 or not all(teams):
            raise ValueError("a season needs at least two teams with non-empty names")
        if not self._ratings:
            self._ratings = dict.fromkeys(teams, self.initial_rating)
            return
        leaving = [rating for team, rating in self._ratings.items() if team not in teams]
        entry_rating = _mean(leaving) if leaving else _mean(self._ratings.values())
        self._ratings = {team: self._ratings.get(team, entry_rating) for team in teams}

    def expected_home_score(self, home_team: str, away_team: str) -> float:
        """Return E_home (Eq. 1) for a match between two teams, from the current ratings."""
        return expected_score(self.rating(home_team), self.rating(away_team), self.home_advantage)

    def update(self, game: GameResult) -> float:
        """Apply one finished match and return Delta, the home team's rating change (Eq. 3).

        Matches must arrive in chronological order; several on the same date are allowed.
        """
        if self._last_match_date is not None and game.match_date < self._last_match_date:
            raise ValueError(
                f"matches must be chronological: {game.match_date} comes after "
                f"{self._last_match_date}"
            )
        expected = self.expected_home_score(game.home_team, game.away_team)
        actual = actual_score(game.home_goals, game.away_goals)
        delta = rating_change(expected, actual, self.k_factor)
        self._ratings[game.home_team] += delta
        self._ratings[game.away_team] -= delta
        self._last_match_date = game.match_date
        return delta


@dataclass(frozen=True, slots=True)
class DrawModel:
    """Draw probability as a function of the Elo expected score (Eq. 4-6).

    Build it with ``fit`` from matches played before the ones it will be used for. ``draw_rates``
    holds d_b for each of the bins, from the lowest expected score to the highest.
    """

    draw_rates: tuple[float, ...]
    overall_draw_rate: float
    matches: int

    def __post_init__(self) -> None:
        rates = (*self.draw_rates, self.overall_draw_rate)
        if not self.draw_rates or not all(0.0 <= rate <= 1.0 for rate in rates):
            raise ValueError("draw rates must be probabilities, with at least one bin")

    @classmethod
    def fit(
        cls,
        expected_scores: Sequence[float],
        actual_scores: Sequence[float],
        bins: int = DEFAULT_DRAW_BINS,
        prior_weight: float = DEFAULT_PRIOR_WEIGHT,
    ) -> DrawModel:
        """Estimate d_b (Eq. 5) from past matches given as pairs (E_home, S_home)."""
        if len(expected_scores) != len(actual_scores) or not expected_scores:
            raise ValueError("need the same, non-zero number of expected and actual scores")
        if bins < 1:
            raise ValueError(f"bins must be at least 1, got {bins}")
        if not (math.isfinite(prior_weight) and prior_weight >= 0):
            raise ValueError(f"prior_weight must be zero or positive, got {prior_weight}")
        if any(score not in _SCORES for score in actual_scores):
            raise ValueError("actual scores must be 0, 0.5 or 1")

        matches_per_bin = [0] * bins
        draws_per_bin = [0] * bins
        for expected, actual in zip(expected_scores, actual_scores, strict=True):
            bin_index = _bin_of(expected, bins)
            matches_per_bin[bin_index] += 1
            draws_per_bin[bin_index] += actual == 0.5
        overall = sum(draws_per_bin) / len(expected_scores)
        rates = tuple(
            (draws + prior_weight * overall) / (count + prior_weight)
            if count + prior_weight
            else overall
            for draws, count in zip(draws_per_bin, matches_per_bin, strict=True)
        )
        return cls(draw_rates=rates, overall_draw_rate=overall, matches=len(expected_scores))

    def draw_probability(self, expected: float) -> float:
        """Return P(D) for a match with home expected score ``expected`` (Eq. 6)."""
        _check_probability(expected)
        cap = max(0.0, 2 * min(expected, 1 - expected) - 2 * MIN_OUTCOME_PROBABILITY)
        return min(self.draw_rates[_bin_of(expected, len(self.draw_rates))], cap)

    def outcome_probabilities(self, expected: float) -> tuple[float, float, float]:
        """Return (P(H), P(D), P(A)) for a match with home expected score ``expected``.

        The order is always home win, draw, away win; the values are non-negative, sum to 1 and
        keep P(H) + P(D) / 2 equal to ``expected``.
        """
        draw = self.draw_probability(expected)
        return expected - draw / 2, draw, 1 - expected - draw / 2


def _bin_of(expected: float, bins: int) -> int:
    """Eq. 4: the index of the equal-width bin of [0, 1] that contains ``expected``."""
    _check_probability(expected)
    return min(int(expected * bins), bins - 1)


def _check_probability(value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"an expected score must be between 0 and 1, got {value}")


def _mean(values: Iterable[float]) -> float:
    values = list(values)
    return math.fsum(values) / len(values)
