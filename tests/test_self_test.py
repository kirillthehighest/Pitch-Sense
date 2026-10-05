"""The packaged application's self-test, run here on the synthetic seasons."""

from app.ui import self_test
from app.ui.self_test import run_self_test


def test_every_check_passes_on_working_data(app_context, capsys):
    assert run_self_test(lambda: app_context) == 0

    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 13
    assert all(line.startswith("ok") for line in lines)
    assert any("calibration chart" in line for line in lines)
    assert app_context.evaluation.has_log  # the missing log was built by the test


def test_missing_data_fails_with_the_reason(application, capsys):
    def load():
        raise FileNotFoundError("Database not found")

    assert run_self_test(load) == 1
    assert capsys.readouterr().out == "FAILED  data: Database not found\n"


def test_without_a_console_the_report_goes_to_a_file(application, monkeypatch, tmp_path):
    def load():
        raise FileNotFoundError("Database not found")

    monkeypatch.setattr(self_test, "user_data_dir", lambda: tmp_path / "PitchSense")
    monkeypatch.setattr("sys.stdout", None)  # a packaged Windows application has no console

    assert self_test.run_self_test(load) == 1
    report = (tmp_path / "PitchSense" / "self-test.txt").read_text(encoding="utf-8")
    assert report == "FAILED  data: Database not found\n"
