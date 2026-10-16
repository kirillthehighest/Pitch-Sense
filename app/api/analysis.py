"""The routes of Analiză: how the algorithms work, the models on the season in progress, a
league's full chronological evaluation and the comparison of the leagues. Every number comes
from the services (the prediction logs of the backtests); nothing is computed here."""

from collections.abc import Callable, Sequence

from fastapi import FastAPI

from app.api import schemas
from app.api.backend import Backend
from app.data.competitions import competition
from app.evaluation.comparison import (
    COMPARED_MODELS,
    REFERENCE_MODEL,
    Agreement,
    PairedDifference,
    SubsetComparison,
)
from app.evaluation.evaluator import ModelEvaluation
from app.evaluation.metrics import Estimate
from app.services.evaluation import EvaluationResults
from app.services.explanations import (
    EXPLANATIONS,
    GROUPS_EXPLANATION,
    IMAGES_NOTE,
    SOURCES,
    crest_count,
    photo_credits,
)
from app.services.labels import MEASURE_LABELS, model_label, subset_label
from app.services.leagues import LeaguesOverview
from app.services.registry import LeagueServices

MARGIN = 1.96  # standard errors on each side of a 95% interval


def estimate_of(estimate: Estimate) -> schemas.Estimate:
    error = estimate.standard_error
    return schemas.Estimate(value=estimate.value, margin=None if error is None else MARGIN * error)


def difference_of(difference: PairedDifference) -> schemas.Difference:
    better = difference.better
    return schemas.Difference(
        first=difference.first,
        second=difference.second,
        first_label=model_label(difference.first),
        second_label=model_label(difference.second),
        measure=str(difference.measure),
        measure_label=MEASURE_LABELS[difference.measure],
        mean=difference.mean,
        lower=difference.lower,
        upper=difference.upper,
        better=better,
        better_label=None if better is None else model_label(better),
    )


def model_evaluation_of(evaluation: ModelEvaluation) -> schemas.ModelEvaluation:
    calibration = evaluation.calibration
    return schemas.ModelEvaluation(
        model=evaluation.model,
        label=model_label(evaluation.model),
        matches=evaluation.matches,
        accuracy=evaluation.accuracy.value,
        brier=None if evaluation.brier is None else evaluation.brier.value,
        log_loss=None if evaluation.log_loss is None else evaluation.log_loss.value,
        calibration_error=evaluation.calibration_error,
        goals_error=None if evaluation.goals_error is None else evaluation.goals_error.value,
        calibration=None
        if calibration is None
        else [
            schemas.CalibrationBin(
                lower=bin_.lower,
                upper=bin_.upper,
                count=bin_.count,
                predicted=bin_.mean_predicted,
                observed=bin_.observed_frequency,
            )
            for bin_ in calibration
        ],
        confusion=evaluation.confusion.astype(int).tolist(),
    )


def subsets_of(subsets: Sequence[SubsetComparison]) -> list[schemas.Subset]:
    return [
        schemas.Subset(
            key=subset.label,
            label=subset_label(subset.label),
            matches=subset.matches,
            brier={model: estimate.value for model, estimate in subset.brier.items()},
            best=subset.best,
            best_label=model_label(subset.best),
            real=subset.lead is not None and subset.lead.significant,
        )
        for subset in subsets
    ]


def agreement_of(agreement: Agreement) -> schemas.Agreement:
    return schemas.Agreement(
        first=agreement.first,
        second=agreement.second,
        first_label=model_label(agreement.first),
        second_label=model_label(agreement.second),
        same=agreement.same_prediction,
        distance=agreement.mean_distance,
    )


def evaluation_of(code: str, results: EvaluationResults) -> schemas.Evaluation:
    return schemas.Evaluation(
        competition=code,
        has_log=True,
        problem=None,
        matches=results.matches,
        first_season=results.first_season,
        last_season=results.last_season,
        compared=[*COMPARED_MODELS, REFERENCE_MODEL],
        models=[model_evaluation_of(e) for e in results.evaluations],
        differences=[difference_of(d) for d in results.differences],
        by_season=subsets_of(results.by_season),
        by_outcome=subsets_of(results.by_outcome),
        by_matchup_type=subsets_of(results.by_matchup_type),
        agreements=[agreement_of(a) for a in results.agreements],
        all_agree=results.all_agree,
    )


def no_evaluation(code: str, has_log: bool, problem: str | None) -> schemas.Evaluation:
    return schemas.Evaluation(
        competition=code,
        has_log=has_log,
        problem=problem,
        matches=0,
        first_season=None,
        last_season=None,
        compared=[*COMPARED_MODELS, REFERENCE_MODEL],
        models=[],
        differences=[],
        by_season=[],
        by_outcome=[],
        by_matchup_type=[],
        agreements=[],
        all_agree=None,
    )


def comparison_of(overview: LeaguesOverview) -> schemas.LeaguesComparison:
    results = []
    for result in overview.results:
        character = result.character
        results.append(
            schemas.LeagueResult(
                code=result.competition,
                name=competition(result.competition).name,
                character=schemas.Character(
                    matches=character.matches,
                    home_win=character.home_win,
                    draw=character.draw,
                    away_win=character.away_win,
                    goals=character.goals,
                    home_margin=character.home_margin,
                    closed_doors_home_win=character.closed_doors_home_win,
                    other_seasons_home_win=character.other_seasons_home_win,
                ),
                brier={e.model: e.brier.value for e in result.evaluations if e.brier is not None},
                best=result.best,
                best_label=model_label(result.best),
                skill=dict(result.skill),
                differences=[difference_of(d) for d in result.differences],
            )
        )
    return schemas.LeaguesComparison(
        missing=[],
        problem=None,
        matches=overview.matches,
        compared=list(COMPARED_MODELS),
        reference=REFERENCE_MODEL,
        results=results,
        pooled=[difference_of(d) for d in overview.pooled],
    )


def no_comparison(missing: list[str], problem: str | None) -> schemas.LeaguesComparison:
    return schemas.LeaguesComparison(
        missing=missing,
        problem=problem,
        matches=0,
        compared=list(COMPARED_MODELS),
        reference=REFERENCE_MODEL,
        results=[],
        pooled=[],
    )


def add_analysis_routes(
    app: FastAPI, backend: Backend, league_of: Callable[[str], LeagueServices]
) -> None:
    """Add the routes of Analiză to the server ``app``."""

    @app.get("/api/about", response_model=schemas.About)
    def about() -> schemas.About:
        return schemas.About(
            explanations=[schemas.Text(title=t, text=x) for t, x in EXPLANATIONS],
            groups=GROUPS_EXPLANATION,
            sources=[schemas.Text(title=t, text=x) for t, x in SOURCES],
            crests=crest_count(),
            photos=photo_credits(),
            images_note=IMAGES_NOTE,
        )

    @app.get("/api/season-check/{code}", response_model=schemas.SeasonCheck)
    def season_check(code: str) -> schemas.SeasonCheck:
        """Every model scored on the matches of the season in progress played so far."""
        services = league_of(code)
        season = services.catalog.current_season

        def state(name: str) -> schemas.SeasonCheck:
            return schemas.SeasonCheck(
                competition=code,
                season=season,
                state=name,
                matches=0,
                first_day=None,
                last_day=None,
                models=[],
            )

        if season is None:
            return state("missing")
        if not services.predictions.is_prepared:
            return state("preparing")
        check = services.predictions.season_check(season)
        if not check.models:
            return state("empty")
        return schemas.SeasonCheck(
            competition=code,
            season=season,
            state="ready",
            matches=check.matches,
            first_day=check.first_day,
            last_day=check.last_day,
            models=[
                schemas.ModelCheck(
                    model=str(model.model),
                    label=model_label(str(model.model)),
                    accuracy=model.accuracy.value,
                    brier=estimate_of(model.brier_score),
                    log_loss=estimate_of(model.log_loss),
                )
                for model in check.models
            ],
        )

    def evaluation(code: str) -> schemas.Evaluation:
        service = league_of(code).evaluation
        if not service.has_log:
            return no_evaluation(code, has_log=False, problem=None)
        try:
            return evaluation_of(code, service.results())
        except (ValueError, OSError) as error:  # a damaged log: shown in place, with the remedy
            return no_evaluation(code, has_log=True, problem=str(error))

    @app.get("/api/evaluation/{code}", response_model=schemas.Evaluation)
    def read_evaluation(code: str) -> schemas.Evaluation:
        """A league's backtest evaluated and compared (empty while it has no log)."""
        return evaluation(code)

    @app.post("/api/evaluation/{code}/backtest", response_model=schemas.Evaluation)
    def build_evaluation(code: str) -> schemas.Evaluation:
        """Run the league's chronological backtest (about 10 s) and evaluate its log."""
        league_of(code).evaluation.build_log()
        return evaluation(code)

    def leagues() -> schemas.LeaguesComparison:
        comparison = backend.comparison
        missing = comparison.missing()
        if missing:
            return no_comparison(missing, None)
        try:
            return comparison_of(comparison.overview())
        except (ValueError, OSError) as error:
            return no_comparison([], str(error))

    @app.get("/api/leagues-comparison", response_model=schemas.LeaguesComparison)
    def read_leagues() -> schemas.LeaguesComparison:
        """The five leagues side by side (empty while a league has no log)."""
        return leagues()

    @app.post("/api/leagues-comparison/backtest", response_model=schemas.LeaguesComparison)
    def build_leagues() -> schemas.LeaguesComparison:
        """Run the backtest of every league without a log (about 10 s each)."""
        backend.comparison.build_missing_logs()
        return leagues()
