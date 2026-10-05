"""A self-test of the whole application: ``python -m app --self-test``, or the packaged app.

It opens the main window off-screen on the real data, uses every screen once through its own
buttons, draws every chart and returns 0 when everything worked. It checks a freshly built
package, where the test suite cannot run. The report is printed; a packaged Windows application
has no console, so there it goes to ``self-test.txt`` in the user's PitchSense folder.
"""

import os
import sys
from collections.abc import Callable

from PySide6.QtGui import QImageReader
from PySide6.QtWidgets import QApplication

from app.data.paths import copy_bundled_results, user_data_dir
from app.ui.context import AppContext, default_context
from app.ui.main_window import MainWindow
from app.ui.theme import apply_theme
from app.ui.worker import run_now


def run_self_test(load_context: Callable[[], AppContext] = default_context) -> int:
    """Run the checks, print one line per check and return the exit code (0 = all passed)."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    application = QApplication.instance() or QApplication(sys.argv)
    typeface = apply_theme(application)  # the bundled fonts must load from a package too
    copy_bundled_results()
    try:
        context = load_context()
    except FileNotFoundError as error:
        _report([f"FAILED  data: {error}"])
        return 1
    errors: list[str] = []
    context.run_task = run_now  # every task finishes before the next step
    context.report_error = errors.append
    window = MainWindow(context)
    window.resize(1280, 820)
    league = context.league(window.current_league)

    checks = {
        "typeface": typeface,
        "SVG icons": b"svg" in QImageReader.supportedImageFormats(),  # the style sheet's icons
        f"historical predictions ({league.code})": league.predictions.is_prepared,
    }
    home = window.home
    if not league.evaluation.has_log:
        home.backtest_button.click()
    window.show_page(window.pages.index(home))
    checks["home"] = home.results_table.rowCount() > 0
    prediction = window.match_prediction
    prediction.predict_button.click()
    checks["match prediction"] = prediction.probability_table.rowCount() > 0
    team = window.team_analysis
    team.show_button.click()
    checks["team analysis"] = team.standings_table.rowCount() > 0
    comparison = window.algorithm_comparison
    window.show_page(window.pages.index(comparison))  # shows the latest results
    checks["algorithm comparison"] = comparison.metrics_table.rowCount() > 0
    leagues = window.leagues
    if context.comparison.missing():
        leagues.backtest_button.click()
    window.show_page(window.pages.index(leagues))
    checks["leagues"] = leagues.models_table.rowCount() == len(context.competitions)
    for name, chart in (
        ("score chart", prediction.score_chart),
        ("Elo chart", team.elo_chart),
        ("team groups chart", team.groups_chart),
        ("calibration chart", comparison.calibration_chart),
        ("confusion matrix chart", comparison.confusion_chart),
        ("skill chart", leagues.skill_chart),
        ("home advantage chart", leagues.home_chart),
    ):
        try:
            chart.figure.canvas.draw()
            checks[name] = True
        except Exception as error:  # a chart that is missing or cannot be drawn fails the test
            errors.append(f"{name}: {error}")
            checks[name] = False
    for index, page in enumerate(window.pages):
        window.show_page(index)
        checks[f"{page.title} screen drawn"] = not window.grab().isNull()
    window.close()
    application.processEvents()

    _report(
        [f"{'ok     ' if passed else 'FAILED '} {name}" for name, passed in checks.items()]
        + [f"error   {message}" for message in errors]
    )
    return 0 if all(checks.values()) and not errors else 1


def _report(lines: list[str]) -> None:
    if sys.stdout is not None:
        print("\n".join(lines))
    else:  # no console
        folder = user_data_dir()
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "self-test.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
