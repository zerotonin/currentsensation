"""Sanity checks for the constants module."""

from __future__ import annotations

from pathlib import Path

import pytest

from currentsensation.constants import (
    CURRENT_LINES,
    DEFAULT_CAPTURE,
    DEFAULT_PINS,
    DEFAULT_TIMING,
    LINE_COLOURS,
    OFF_TAG,
    SessionPaths,
    WONG,
)


def test_default_pins_cover_all_channels() -> None:
    assert set(DEFAULT_PINS) == {"red", "blue", "yellow", "light", "shaker"}


def test_pins_are_unique() -> None:
    assert len(set(DEFAULT_PINS.values())) == len(DEFAULT_PINS)


def test_current_lines_subset_of_pins() -> None:
    assert set(CURRENT_LINES).issubset(set(DEFAULT_PINS))


def test_off_tag_not_a_real_pin() -> None:
    assert OFF_TAG not in DEFAULT_PINS


def test_timing_defaults_positive() -> None:
    assert DEFAULT_TIMING.shake_dur > 0
    assert DEFAULT_TIMING.stim_dur > 0
    assert DEFAULT_TIMING.peri_stim_dur > 0
    assert DEFAULT_TIMING.reps >= 1


def test_capture_defaults_sensible() -> None:
    assert DEFAULT_CAPTURE.width > 0
    assert DEFAULT_CAPTURE.height > 0
    assert DEFAULT_CAPTURE.fps > 0


def test_wong_palette_complete() -> None:
    expected = {
        "black", "orange", "sky_blue", "bluish_green",
        "yellow", "blue", "vermilion", "reddish_purple",
    }
    assert set(WONG) == expected
    for hex_value in WONG.values():
        assert hex_value.startswith("#") and len(hex_value) == 7


def test_line_colours_cover_lines_and_off() -> None:
    assert set(LINE_COLOURS) == set(CURRENT_LINES) | {OFF_TAG}


def test_session_paths_creates_directory(tmp_path: Path) -> None:
    root = tmp_path / "session"
    paths = SessionPaths.from_root(root)
    assert paths.root.is_dir()
    assert paths.schedule_file.parent == paths.root


def test_session_paths_rejects_garbage(tmp_path: Path) -> None:
    paths = SessionPaths.from_root(tmp_path)
    with pytest.raises(AttributeError):
        paths.root = tmp_path  # frozen
