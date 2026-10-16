"""Write the app icon files of the packages from the logo: ``python packaging/icons.py DIR``.

The icon is drawn by ``app/ui/brand.py`` at every size, in the colours of the default league
(La Liga; the window's icon then follows the league on screen), and saved as PNG images inside
the two container formats the systems read: ``PitchSense.ico`` for Windows and
``PitchSense.icns`` for macOS. Both formats accept PNG images directly (Windows Vista and later,
macOS 10.7 and later), so no image library beyond Qt is needed, and the icon always matches the
logo of the window.
"""

import os
import struct
import sys
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))  # run as a script from the build

ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
# macOS icon types that hold a PNG image, with the pixel size of each.
ICNS_TYPES = (
    (b"icp4", 16),
    (b"icp5", 32),
    (b"icp6", 48),  # macOS reads this type as 48 pixels
    (b"ic07", 128),
    (b"ic08", 256),
    (b"ic09", 512),
    (b"ic10", 1024),  # 512 points at twice the pixel density
    (b"ic11", 32),  # 16 points, twice the density
    (b"ic12", 64),  # 32 points, twice the density
    (b"ic13", 256),  # 128 points, twice the density
    (b"ic14", 512),  # 256 points, twice the density
)


def png_images(sizes: set[int]) -> dict[int, bytes]:
    """The logo as PNG data at each size in pixels."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QGuiApplication

    from app.ui.brand import icon_image
    from app.ui.theme import LOGO_FAMILY, load_fonts
    from app.ui.themes import DEFAULT_THEME

    QGuiApplication.instance() or QGuiApplication([])
    if LOGO_FAMILY not in load_fonts():  # the mark's letters are drawn in it
        raise RuntimeError(f"the {LOGO_FAMILY} typeface of the logo did not load")
    images = {}
    for size in sorted(sizes):
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        if not icon_image(size, DEFAULT_THEME).save(buffer, "PNG"):
            raise RuntimeError(f"could not draw the icon at {size} pixels")
        images[size] = bytes(data.data())
    return images


def ico_bytes(images: Mapping[int, bytes]) -> bytes:
    """An ICO file: a header, one directory entry per image, then the PNG images."""
    sizes = sorted(images)
    header = struct.pack("<HHH", 0, 1, len(sizes))  # reserved, type 1 (icon), image count
    offset = len(header) + 16 * len(sizes)
    entries, data = b"", b""
    for size in sizes:
        if not 1 <= size <= 256:
            raise ValueError(f"an ICO image is 1 to 256 pixels, not {size}")
        png = images[size]
        side = size % 256  # 0 means 256
        entries += struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(png), offset + len(data))
        data += png
    return header + entries + data


def icns_bytes(images: Mapping[int, bytes]) -> bytes:
    """An ICNS file: the 'icns' header, then one typed block per image (big-endian lengths)."""
    blocks = b""
    for kind, size in ICNS_TYPES:
        png = images[size]
        blocks += kind + struct.pack(">I", 8 + len(png)) + png
    return b"icns" + struct.pack(">I", 8 + len(blocks)) + blocks


def write_icons(folder: Path) -> tuple[Path, Path]:
    """Write ``PitchSense.ico`` and ``PitchSense.icns`` into ``folder``; returns both paths."""
    images = png_images(set(ICO_SIZES) | {size for _, size in ICNS_TYPES})
    folder.mkdir(parents=True, exist_ok=True)
    ico = folder / "PitchSense.ico"
    icns = folder / "PitchSense.icns"
    ico.write_bytes(ico_bytes({size: images[size] for size in ICO_SIZES}))
    icns.write_bytes(icns_bytes(images))
    return ico, icns


if __name__ == "__main__":
    for path in write_icons(Path(sys.argv[1])):
        print(f"{path} ({path.stat().st_size / 1e3:.0f} kB)")
