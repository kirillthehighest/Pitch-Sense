"""Check that the active environment matches CLAUDE.md decisions and pyproject.toml pins."""

import sys
import tomllib
from importlib.metadata import version
from pathlib import Path

import pytest

PYPROJECT = Path(__file__).resolve().parent.parent / "pyproject.toml"


def declared_requirements() -> list[str]:
    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    return project["dependencies"] + project["optional-dependencies"]["dev"]


def test_python_is_3_14():
    assert sys.version_info[:2] == (3, 14)


def test_every_requirement_is_an_exact_pin():
    unpinned = [requirement for requirement in declared_requirements() if "==" not in requirement]

    assert unpinned == []


@pytest.mark.parametrize("requirement", declared_requirements())
def test_installed_version_matches_pin(requirement):
    name, _, pinned_version = requirement.partition("==")

    assert version(name.strip()) == pinned_version.strip()


def test_matplotlib_qt_backend_loads_with_pyside6():
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    from PySide6.QtWidgets import QWidget

    assert issubclass(FigureCanvasQTAgg, QWidget)
