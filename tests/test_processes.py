"""The worker process (``app/services/processes.py``): a long computation runs away from the
caller's interpreter and comes back pickled, exactly as it would have been computed here."""

import pickle
from functools import partial

from app.services.predictions import compute_predictions
from app.services.processes import compute_here, compute_in_process, stop_processes


def test_a_job_runs_in_another_process_with_the_same_result(season_matches, next_season_matches):
    matches = [*season_matches, *next_season_matches]
    job = partial(compute_predictions, matches, (), 3)
    try:
        elsewhere = pickle.loads(compute_in_process(job))
    finally:
        stop_processes()
    here = pickle.loads(compute_here(job))

    assert len(elsewhere.results) == len(here.results) > 0
    for theirs, ours in zip(elsewhere.results, here.results, strict=True):
        assert theirs.match == ours.match
        assert {model: p.probabilities.as_tuple() for model, p in theirs.predictions.items()} == {
            model: p.probabilities.as_tuple() for model, p in ours.predictions.items()
        }


def test_stopping_without_a_worker_process_does_nothing():
    stop_processes()
    stop_processes()
