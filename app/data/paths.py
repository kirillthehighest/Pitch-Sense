"""Locations of the project's data files. Every data path is resolved through this module.

The paths are relative to the project folder, so they work wherever the project is cloned.
Packaged builds (Phase 14) will adapt this module.
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
DATABASE_PATH = DATA_DIR / "pitchsense.db"
