"""End-to-end tests: raw season files -> database -> backtest log -> evaluation -> the screens.

Each test runs the whole chain on the small synthetic seasons of conftest.py and checks that the
layers agree with each other, or that a broken input is reported in the window instead of
stopping the application.
"""

import pytest

from app.evaluation.backtesting import read_log
from app.evaluation.evaluator import evaluate
from app.prediction.prediction_engine import predict_season
from app.services.catalog import DataCatalog
from app.services.formatting import number, percent
from app.services.labels import model_label
from app.ui import main_window
from app.ui.main_window import MainWindow

MODELS = ("Elo", "Poisson", "Logistic regression")


def table_rows(table):
    return [
        [table.item(row, column).text() for column in range(table.columnCount())]
        for row in range(table.rowCount())
    ]


@pytest.fixture
def window(app_context):
    window = MainWindow(app_context)
    yield window
    window.close()


@pytest.fixture
def window_with_log(window):
    window.analysis.models.backtest_button.click()
    return window


def show(window, page):
    window.show_page(window.pages.index(page))


def bar_numbers(bars):
    return [
        [row.label, percent(row.home), percent(row.draw), percent(row.away)] for row in bars.rows
    ]


def day_rows(page):
    return [row for group in page.groups for row in group.rows]


def test_every_played_match_shows_the_forecasts_of_the_backtest_log(
    window_with_log, app_context, errors
):
    log = read_log(app_context.league("SP1").evaluation.log)
    logged = {(row.match_date, row.home_team, row.away_team, row.model): row for row in log}
    page = window_with_log.matches
    played = app_context.league("SP1").catalog.season_matches("2007-08")

    for match in played:
        page.show_day(match.match_date)
        (row,) = day_rows(page)  # one match a day
        rows = {
            model: logged[(match.match_date, match.home_team, match.away_team, model)]
            for model in MODELS
        }
        logistic = rows["Logistic regression"]  # the model of the list
        assert row.hit == (logistic.predicted == logistic.actual)
        row.click()

        detail = page.detail
        assert bar_numbers(detail.bars) == [
            [
                model_label(model),
                percent(rows[model].p_home),
                percent(rows[model].p_draw),
                percent(rows[model].p_away),
            ]
            for model in MODELS
        ]
        poisson = rows["Poisson"]
        assert detail.goals_label.text() == (
            f"Goluri așteptate: {match.home_team} {number(poisson.expected_home_goals, 2)}, "
            f"{match.away_team} {number(poisson.expected_away_goals, 2)}"
        )
        assert detail.hero.score.text() == f"{match.home_goals} – {match.away_goals}"
        page.show_list()
    assert len(played) == 12
    assert errors == []


def test_the_screens_show_the_evaluation_of_the_log(window_with_log, app_context, errors):
    evaluations = evaluate(read_log(app_context.league("SP1").evaluation.log))
    show(window_with_log, window_with_log.analysis)

    assert table_rows(window_with_log.analysis.models.metrics_table) == [
        [
            model_label(e.model),
            percent(e.accuracy.value),
            number(e.brier.value if e.brier else None),
            number(e.log_loss.value if e.log_loss else None),
            number(e.calibration_error),
            number(e.goals_error.value if e.goals_error else None, 3),
        ]
        for e in evaluations
    ]
    assert errors == []


@pytest.mark.parametrize("season", ["2006-07", "2007-08"])
def test_the_league_table_matches_the_raw_files(window, raw_season_rows, next_season_rows, season):
    raw_rows = raw_season_rows if season == "2006-07" else next_season_rows
    records = {}
    for row in raw_rows:
        home_goals, away_goals = int(row["FTHG"]), int(row["FTAG"])
        for team, scored, conceded in (
            (row["HomeTeam"], home_goals, away_goals),
            (row["AwayTeam"], away_goals, home_goals),
        ):
            played, wins, draws, losses, goals_for, goals_against = records.get(team, [0] * 6)
            records[team] = [
                played + 1,
                wins + (scored > conceded),
                draws + (scored == conceded),
                losses + (scored < conceded),
                goals_for + scored,
                goals_against + conceded,
            ]
    expected = sorted(
        records.items(),
        key=lambda item: (
            -(3 * item[1][1] + item[1][2]),
            -(item[1][4] - item[1][5]),
            -item[1][4],
            item[0],
        ),
    )
    page = window.standings
    page.show_season(season)

    assert table_rows(page.table) == [
        [
            str(position),
            team,
            *(str(value) for value in record),
            f"{record[4] - record[5]:+d}".replace("-", "−") if record[4] != record[5] else "0",
            str(3 * record[1] + record[2]),
            "",  # the form, drawn in the cell
        ]
        for position, (team, record) in enumerate(expected, start=1)
    ]


def test_a_missing_database_is_explained_at_start_up(application, monkeypatch, tmp_path):
    shown = []

    class MessageBox:
        @staticmethod
        def critical(parent, title, text):
            shown.append(text)

    monkeypatch.setattr(main_window, "QMessageBox", MessageBox)
    monkeypatch.setattr(
        main_window, "default_context", lambda: DataCatalog.load(tmp_path / "missing.db")
    )

    assert main_window.main() == 1
    assert len(shown) == 1
    assert "python -m app.data.build_database" in shown[0]


def test_a_damaged_log_is_explained_in_place_and_can_be_rebuilt(app_context, errors):
    log = app_context.league("SP1").evaluation.log
    log.parent.mkdir(parents=True)
    log.write_text("not,a,prediction,log\n1,2,3,4\n", encoding="utf-8")

    window = MainWindow(app_context)
    analysis = window.analysis
    models, leagues = analysis.models, analysis.leagues

    for label in (models.summary_label, leagues.summary_label):
        assert label.text().startswith("Rezultatele nu pot fi citite. Rulează din nou backtestul")
        assert "is not a prediction log" in label.text()  # the details
    assert not models.backtest_button.isHidden()
    show(window, analysis)  # changing screens repeats no dialog
    show(window, window.matches)
    assert errors == []

    models.backtest_button.click()
    show(window, analysis)

    assert models.backtest_button.isHidden()
    assert models.metrics_table.rowCount() == 5
    assert leagues.models_table.rowCount() == 1
    assert errors == []
    window.close()


def test_a_backtest_that_fails_is_reported_and_the_window_keeps_working(
    app_context, database, errors
):
    window = MainWindow(app_context)
    database.unlink()  # the data is already loaded; the backtest reads the database again
    models = window.analysis.models

    models.backtest_button.click()

    assert len(errors) == 1
    assert "Database not found" in errors[0]
    assert models.backtest_button.isEnabled()
    assert not models.backtest_button.isHidden()
    window.standings.show_season("2006-07")  # the loaded data still works
    assert window.standings.table.rowCount() == 4
    assert len(errors) == 1
    window.close()


def test_every_scheduled_match_shows_the_engines_forecast_from_the_downloads(
    make_app_context, database, live_dir, errors
):
    # raw files -> database, downloads -> season in progress -> engine and window agree
    catalog = DataCatalog.load(database, competition="SP1", live_dir=live_dir)
    _, upcoming = predict_season(catalog.matches, catalog.fixtures, min_training_matches=3)
    window = MainWindow(make_app_context(database, live_dir=live_dir))
    page = window.matches

    for expected in upcoming:
        fixture = expected.fixture
        page.show_day(fixture.match_date)
        (row,) = day_rows(page)
        assert (row.forecast.home_team, row.forecast.away_team) == (
            fixture.home_team,
            fixture.away_team,
        )
        row.click()

        assert bar_numbers(page.detail.bars) == [
            [
                model_label(str(model)),
                percent(prediction.probabilities.home_win),
                percent(prediction.probabilities.draw),
                percent(prediction.probabilities.away_win),
            ]
            for model, prediction in expected.predictions.items()
        ]
        assert page.detail.hero.status.text() == "Programat"
        page.show_list()
    assert errors == []
    window.close()
