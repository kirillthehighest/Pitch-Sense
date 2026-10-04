import numpy as np
import pytest

from app.data.build_database import build_database
from app.evaluation.kmeans_selection import compare_k, main, rand_index, summarize
from app.evaluation.team_clustering import cluster_profiles
from app.statistics.team_profiles import season_profiles
from app.statistics.team_statistics import MatchHistory


def test_rand_index_of_identical_groupings_with_other_numbers_is_one():
    assert rand_index([0, 0, 1, 1, 2], [2, 2, 0, 0, 1]) == 1.0


def test_rand_index_hand_example():
    # Of the 6 pairs, only (0, 3) and (1, 2) are treated alike: different in both labellings.
    assert rand_index([0, 0, 1, 1], [0, 1, 0, 1]) == pytest.approx(2 / 6)


def test_rand_index_needs_matching_labellings():
    with pytest.raises(ValueError):
        rand_index([0, 1], [0, 1, 1])
    with pytest.raises(ValueError):
        rand_index([0], [0])


def test_compare_k_skips_impossible_values(season_matches, next_season_matches):
    history = MatchHistory([*season_matches, *next_season_matches])
    # The two fixture seasons are identical, so 8 profiles have only 4 distinct values.
    profiles = [*season_profiles(history, "2006-07"), *season_profiles(history, "2007-08")]

    comparisons = compare_k(profiles, k_values=(1, 2, 3, 4, 5), seeds=(0, 1, 2))

    assert [row.k for row in comparisons] == [2, 3, 4]
    for row in comparisons:
        assert 0 <= row.stability <= 1
        assert -1 <= row.silhouette <= 1
        assert row.smallest_cluster >= 1
    assert comparisons[-1].inertia == pytest.approx(0.0)


def test_summaries_describe_every_group_strongest_first(season_matches):
    profiles = season_profiles(MatchHistory(season_matches), "2006-07")
    clusters = cluster_profiles(profiles, k=2)

    summaries = summarize(clusters, examples=2)

    assert [summary.group for summary in summaries] == [0, 1]
    assert sum(summary.size for summary in summaries) == 4
    assert summaries[0].centre[4] > summaries[1].centre[4]  # points per match
    for summary in summaries:
        members = [p for p, g in zip(profiles, clusters.groups, strict=True) if g == summary.group]
        assert summary.centre == pytest.approx(tuple(np.mean([p.values for p in members], axis=0)))
        assert 1 <= len(summary.examples) <= 2


def test_main_prints_the_comparisons_and_the_groups(raw_data_dir, tmp_path, capsys):
    database_path = tmp_path / "pitchsense.db"
    build_database(raw_data_dir, database_path, {"SP1": 4})

    exit_code = main(database_path)

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Choosing k on 2006-07, 2007-08: 8 team-season profiles" in output
    assert "Chosen k = 4" in output


def test_main_explains_a_missing_database(tmp_path, capsys):
    assert main(tmp_path / "missing.db") == 1
    assert "python -m app.data.build_database" in capsys.readouterr().err
