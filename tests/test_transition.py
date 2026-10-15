"""The change of colours between leagues: a wavy circle from the top-left corner opens the
picture of the old window until it has passed every corner."""

import math
from itertools import pairwise

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QWidget

from app.ui.transition import (
    AMPLITUDE,
    CALM_AMPLITUDE,
    WAVELENGTH,
    ThemeReveal,
    reveal_radius,
    wave_amplitude,
    wave_edge,
    wave_offset,
)

WIDTH, HEIGHT = 600, 400


@pytest.fixture
def reveal(application):
    window = QWidget()
    window.resize(WIDTH, HEIGHT)
    old = QPixmap(WIDTH, HEIGHT)
    old.fill(QColor("#47201A"))
    cover = ThemeReveal(window, old, "#3DDCFF")
    yield cover
    window.deleteLater()


def test_the_circle_grows_from_nothing_past_the_farthest_corner():
    assert reveal_radius(0, WIDTH, HEIGHT) == 0
    assert reveal_radius(1, WIDTH, HEIGHT) > math.hypot(WIDTH, HEIGHT) + AMPLITUDE
    radii = [reveal_radius(step / 10, WIDTH, HEIGHT) for step in range(11)]
    assert radii == sorted(radii)


def test_the_waves_calm_down_as_the_circle_grows():
    assert wave_amplitude(0) == pytest.approx(AMPLITUDE)
    assert wave_amplitude(1) == pytest.approx(CALM_AMPLITUDE)
    heights = [wave_amplitude(step / 10) for step in range(11)]
    assert heights == sorted(heights, reverse=True)


def test_the_waves_rise_and_fall_along_the_edge_and_run_with_time():
    offsets = [wave_offset(arc, 0.3, 10) for arc in range(0, round(3 * WAVELENGTH), 5)]

    assert max(offsets) > 0 > min(offsets)  # crests and troughs
    assert all(abs(offset) <= 10 + 1e-9 for offset in offsets)
    assert wave_offset(40, 0.3, 10) != pytest.approx(wave_offset(40, 0.35, 10))  # they run


def test_the_edge_runs_from_the_top_edge_to_the_left_edge_near_the_circle():
    radius, amplitude = 300.0, 12.0
    edge = wave_edge(radius, 0.4, amplitude)

    assert edge[0].y() == pytest.approx(0, abs=1e-9)  # on the top edge of the window
    assert edge[-1].x() == pytest.approx(0, abs=1e-9)  # on the left edge
    distances = [math.hypot(point.x(), point.y()) for point in edge]
    assert all(radius - amplitude - 1e-6 <= d <= radius + amplitude + 1e-6 for d in distances)
    assert max(distances) - min(distances) > amplitude  # it is wavy, not round
    gaps = [math.dist((a.x(), a.y()), (b.x(), b.y())) for a, b in pairwise(edge)]
    assert max(gaps) < 10  # smooth


def test_the_cover_shrinks_from_the_whole_window_to_nothing(reveal):
    centre, corner = QPointF(WIDTH / 2, HEIGHT / 2), QPointF(WIDTH - 2, HEIGHT - 2)

    reveal.progress = 0.0
    assert reveal.cover().contains(centre) and reveal.cover().contains(QPointF(2, 2))

    reveal.progress = 0.5  # the top-left corner is new, the bottom-right still old
    assert not reveal.cover().contains(QPointF(2, 2))
    assert reveal.cover().contains(corner)

    reveal.progress = 1.0
    for point in (QPointF(2, 2), QPointF(WIDTH - 2, 2), QPointF(2, HEIGHT - 2), corner, centre):
        assert not reveal.cover().contains(point)


def test_a_reveal_lets_clicks_through_and_removes_itself_when_finished(reveal):
    ended = []
    reveal.ended.connect(lambda: ended.append(True))
    assert reveal.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    assert reveal.geometry() == reveal.parentWidget().rect()

    reveal.start()
    assert reveal.animation.state() == reveal.animation.State.Running
    reveal.animation.setCurrentTime(reveal.animation.duration() // 2)
    assert 0 < reveal.progress < 1
    reveal.grab()  # paints without error mid-way

    reveal.finish()
    assert ended == [True] and reveal.isHidden()
