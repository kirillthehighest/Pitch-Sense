"""Enforce the layer rules from AGENTS.md by inspecting the imports of every module in app/."""

import ast
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent / "app"
LAYERS = (
    "algorithms",
    "data",
    "statistics",
    "prediction",
    "evaluation",
    "services",
    "visualization",
    "ui",
)
QT_MODULES = {"PySide6", "shiboken6"}
BANNED_LIBRARIES = {"sklearn", "scipy", "statsmodels"}


def imported_top_level_modules(source: str) -> set[str]:
    """Return the top-level module names a source file imports; relative imports count as "app"."""
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                imported.add("app")
            elif node.module:
                imported.add(node.module.split(".")[0])
    return imported


def modules_in(directory: Path) -> dict[Path, set[str]]:
    return {
        path: imported_top_level_modules(path.read_text(encoding="utf-8"))
        for path in sorted(directory.rglob("*.py"))
    }


def layer_of(path: Path) -> str:
    return path.relative_to(APP_DIR).parts[0]


def test_import_scanner_finds_absolute_relative_and_nested_imports():
    source = (
        "import numpy as np\n"
        "import os.path\n"
        "from pandas import DataFrame\n"
        "from . import elo\n"
        "def build():\n"
        "    from PySide6.QtWidgets import QWidget\n"
    )

    assert imported_top_level_modules(source) == {"numpy", "os", "pandas", "app", "PySide6"}


def test_every_layer_package_exists():
    missing = [layer for layer in LAYERS if not (APP_DIR / layer / "__init__.py").is_file()]

    assert missing == []


def test_algorithms_import_only_standard_library_and_numpy():
    allowed = set(sys.stdlib_module_names) | {"numpy"}
    violations = {
        str(path.relative_to(APP_DIR)): sorted(imports - allowed)
        for path, imports in modules_in(APP_DIR / "algorithms").items()
        if imports - allowed
    }

    assert violations == {}


def test_only_ui_imports_qt():
    violations = [
        str(path.relative_to(APP_DIR))
        for path, imports in modules_in(APP_DIR).items()
        if imports & QT_MODULES and layer_of(path) != "ui"
    ]

    assert violations == []


def test_matplotlib_is_imported_only_by_visualization_and_ui():
    violations = [
        str(path.relative_to(APP_DIR))
        for path, imports in modules_in(APP_DIR).items()
        if "matplotlib" in imports and layer_of(path) not in {"visualization", "ui"}
    ]

    assert violations == []


def test_no_module_imports_banned_libraries():
    violations = {
        str(path.relative_to(APP_DIR)): sorted(imports & BANNED_LIBRARIES)
        for path, imports in modules_in(APP_DIR).items()
        if imports & BANNED_LIBRARIES
    }

    assert violations == {}
