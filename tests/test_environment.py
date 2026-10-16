"""Check that the active environment matches AGENTS.md decisions and pyproject.toml pins."""

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


WEB = PYPROJECT.parent / "web"


def test_the_web_interface_pins_every_package_exactly():
    import json

    package = json.loads((WEB / "package.json").read_text(encoding="utf-8"))
    pins = {**package["dependencies"], **package["devDependencies"]}
    loose = {name: pin for name, pin in pins.items() if not pin[0].isdigit()}

    assert loose == {}
    cargo = tomllib.loads((WEB / "src-tauri" / "Cargo.toml").read_text(encoding="utf-8"))
    for name in ("tauri", "tauri-build"):
        section = "dependencies" if name == "tauri" else "build-dependencies"
        assert cargo[section][name]["version"].startswith("=")


def test_the_window_carries_the_version_of_the_code():
    import json

    from app import __version__

    cargo = tomllib.loads((WEB / "src-tauri" / "Cargo.toml").read_text(encoding="utf-8"))
    config = json.loads((WEB / "src-tauri" / "tauri.conf.json").read_text(encoding="utf-8"))

    assert cargo["package"]["version"] == config["version"] == __version__
