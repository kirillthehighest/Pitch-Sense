# PyInstaller build of PitchSense (one folder; on macOS also PitchSense.app).
# Run it through packaging/build.py, which first rebuilds the database and the prediction logs
# that the package ships with and draws the icon files. PyInstaller provides Analysis, PYZ, EXE,
# COLLECT, BUNDLE and SPECPATH when it reads this file.
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent
sys.path.insert(0, str(ROOT))

from app import __version__ as VERSION  # noqa: E402
from app.data.competitions import COMPETITIONS  # noqa: E402

ICONS = ROOT / "build" / "icons"  # written by packaging/icons.py

analysis = Analysis(
    [str(ROOT / "app" / "__main__.py")],
    pathex=[str(ROOT)],
    # Read-only data inside the package; see app/data/paths.py.
    datas=[
        (str(ROOT / "data" / "pitchsense.db"), "data"),
        *(
            (str(ROOT / "data" / "results" / f"backtest_{code}.csv"), "data/results")
            for code in COMPETITIONS
        ),
        # The typefaces and the icons of the style sheet.
        (str(ROOT / "app" / "ui" / "assets"), "app/ui/assets"),
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
    icon=str(ICONS / "PitchSense.ico") if sys.platform == "win32" else None,
)
collected = COLLECT(exe, analysis.binaries, analysis.datas, name="PitchSense", upx=False)

if sys.platform == "darwin":
    app = BUNDLE(
        collected,
        name="PitchSense.app",
        icon=str(ICONS / "PitchSense.icns"),
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
