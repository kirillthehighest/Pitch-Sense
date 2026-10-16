# PyInstaller build of the local server of the web interface (Phase 22): one folder,
# pitchsense-server, which the desktop window (web/src-tauri) carries as a resource and starts.
# Run it through packaging/build.py, which first rebuilds the database and the prediction logs
# that the package ships with and downloads the season in progress.
# PyInstaller provides Analysis, PYZ, EXE, COLLECT and SPECPATH when it reads this file.
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent
sys.path.insert(0, str(ROOT))

from app.data.competitions import COMPETITIONS  # noqa: E402

analysis = Analysis(
    [str(ROOT / "app" / "api" / "__main__.py")],
    pathex=[str(ROOT)],
    # Read-only data inside the package; see app/data/paths.py.
    datas=[
        (str(ROOT / "data" / "pitchsense.db"), "data"),
        *(
            (str(ROOT / "data" / "results" / f"backtest_{code}.csv"), "data/results")
            for code in COMPETITIONS
        ),
        # The season in progress, downloaded by the build (python -m app.data.update).
        (str(ROOT / "data" / "live"), "data/live"),
        # The images the server sends: crests, league images and stadium photos.
        (str(ROOT / "app" / "assets"), "app/assets"),
    ],
    # uvicorn chooses its pieces when it starts, out of PyInstaller's sight
    hiddenimports=["uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto",
                   "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.on"],  # fmt: skip
    # Qt (used by the image tools only) and the test and notebook tools stay out of the server.
    excludes=["PySide6", "shiboken6", "tkinter", "pytest", "IPython"],
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="pitchsense-server",
    console=True,  # its first line tells the window the port; the window hides its console
    upx=False,
)
COLLECT(exe, analysis.binaries, analysis.datas, name="pitchsense-server", upx=False)
