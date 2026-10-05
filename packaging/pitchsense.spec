# PyInstaller build of PitchSense (one folder; on macOS also PitchSense.app).
# Run it through packaging/build.py, which first rebuilds the database and the prediction log
# that the package ships with. PyInstaller provides Analysis, PYZ, EXE, COLLECT, BUNDLE and
# SPECPATH when it reads this file.
import sys
import tomllib
from pathlib import Path

ROOT = Path(SPECPATH).parent
VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]

analysis = Analysis(
    [str(ROOT / "app" / "__main__.py")],
    pathex=[str(ROOT)],
    # Read-only data inside the package; see app/data/paths.py.
    datas=[
        (str(ROOT / "data" / "pitchsense.db"), "data"),
        (str(ROOT / "data" / "results" / "backtest_SP1.csv"), "data/results"),
    ],
    excludes=["tkinter", "pytest", "IPython"],
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="PitchSense",
    console=False,
    upx=False,
)
collected = COLLECT(exe, analysis.binaries, analysis.datas, name="PitchSense", upx=False)

if sys.platform == "darwin":
    app = BUNDLE(
        collected,
        name="PitchSense.app",
        bundle_identifier="md.utm.pitchsense",
        version=VERSION,
        info_plist={
            "CFBundleDisplayName": "PitchSense",
            "CFBundleShortVersionString": VERSION,
            # The oldest macOS the bundled libraries support (numpy's are built for 14.0).
            "LSMinimumSystemVersion": "14.0",
            "NSHighResolutionCapable": True,
        },
    )
