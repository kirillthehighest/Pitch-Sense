"""The icon files of the packages: read back, every image is the logo at the declared size."""

import importlib.util
import struct
from pathlib import Path

import pytest
from PySide6.QtGui import QImage

SCRIPT = Path(__file__).resolve().parent.parent / "packaging" / "icons.py"


@pytest.fixture(scope="module")
def icons():
    spec = importlib.util.spec_from_file_location("pitchsense_icons", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def written(application, icons, tmp_path_factory):
    return icons.write_icons(tmp_path_factory.mktemp("icons"))


def png_size(data: bytes) -> tuple[int, int]:
    image = QImage.fromData(data, "PNG")
    assert not image.isNull()
    return image.width(), image.height()


def test_the_ico_holds_every_windows_size_as_png(icons, written):
    data = written[0].read_bytes()
    reserved, kind, count = struct.unpack_from("<HHH", data, 0)

    assert (reserved, kind, count) == (0, 1, len(icons.ICO_SIZES))
    for index, size in enumerate(icons.ICO_SIZES):
        width, height, _, _, planes, bits, length, offset = struct.unpack_from(
            "<BBBBHHII", data, 6 + 16 * index
        )
        assert (width or 256, height or 256, planes, bits) == (size, size, 1, 32)
        assert png_size(data[offset : offset + length]) == (size, size)


def test_the_icns_holds_every_macos_type_as_png(icons, written):
    data = written[1].read_bytes()
    assert data[:4] == b"icns"
    assert struct.unpack_from(">I", data, 4)[0] == len(data)

    position, found = 8, []
    while position < len(data):
        kind = data[position : position + 4]
        length = struct.unpack_from(">I", data, position + 4)[0]
        found.append((kind, png_size(data[position + 8 : position + length])[0]))
        position += length

    assert position == len(data)
    assert found == list(icons.ICNS_TYPES)


def test_an_ico_image_cannot_be_larger_than_256_pixels(icons):
    with pytest.raises(ValueError, match="1 to 256 pixels"):
        icons.ico_bytes({512: b"png"})


def test_the_package_icon_is_the_mark_in_the_default_league_colours(application, icons):
    from PySide6.QtGui import QImage

    from app.ui.brand import icon_image
    from app.ui.themes import DEFAULT_THEME

    image = QImage.fromData(icons.png_images({64})[64])
    expected = icon_image(64, DEFAULT_THEME).convertToFormat(image.format())

    assert image == expected
