"""Schedule builder correctness."""

from __future__ import annotations

import random
from dataclasses import replace
from pathlib import Path

import pytest

from currentsensation.constants import DEFAULT_TIMING, OFF_TAG
from currentsensation.scheduling import (
    ScheduleConfig,
    build_schedule,
    serialise_schedule,
)


def _short_config(**kw) -> ScheduleConfig:
    """Tiny timings so schedules are small and easy to reason about."""
    timing = replace(
        DEFAULT_TIMING,
        shake_dur=3.0,
        peri_stim_dur=2.0,
        stim_dur=10.0,
        delay_offset=1.0,
        reps=2,
    )
    return ScheduleConfig(timing=timing, **kw)


def test_video_schedule_events_sorted_by_time() -> None:
    events = build_schedule(_short_config(mode="video"))
    offsets = [e.offset_s for e in events]
    assert offsets == sorted(offsets)


def test_schedule_starts_at_delay_offset() -> None:
    events = build_schedule(_short_config(mode="video"))
    assert events[0].offset_s == pytest.approx(1.0)


def test_schedule_ends_with_finish() -> None:
    events = build_schedule(_short_config(mode="video"))
    assert events[-1].kind == "finish"


def test_video_schedule_trial_count() -> None:
    # baseline + 2 reps * 3 lines + recovery = 8 trials.
    events = build_schedule(_short_config(mode="video"))
    capture_events = [e for e in events if e.kind == "capture_video"]
    assert len(capture_events) == 8


def test_image_schedule_emits_one_capture_per_frame() -> None:
    config = _short_config(mode="image", image_fps=5)
    events = build_schedule(config)
    image_events = [e for e in events if e.kind == "capture_image"]
    # Per trial: 10s * 5fps = 50 frames; 8 trials = 400 frames.
    assert len(image_events) == 8 * 50


def test_randomisation_is_seeded() -> None:
    config = _short_config(mode="video")
    rng_a = random.Random(42)
    rng_b = random.Random(42)
    events_a = build_schedule(config, rng=rng_a)
    events_b = build_schedule(config, rng=rng_b)
    a_lines = [e.payload["line"] for e in events_a if e.kind == "capture_video"]
    b_lines = [e.payload["line"] for e in events_b if e.kind == "capture_video"]
    assert a_lines == b_lines


def test_no_randomise_keeps_line_order() -> None:
    config = _short_config(mode="video")
    config.randomise_lines = False
    events = build_schedule(config)
    capture_lines = [e.payload["line"] for e in events if e.kind == "capture_video"]
    # baseline=off, then [red,blue,yellow] * 2, then off.
    assert capture_lines == [OFF_TAG, "red", "blue", "yellow",
                             "red", "blue", "yellow", OFF_TAG]


def test_change_line_events_have_paired_off() -> None:
    events = build_schedule(_short_config(mode="video"))
    line_changes = [e for e in events if e.kind == "change_line"]
    # Each line activation must be paired with an OFF, so total even count.
    assert len(line_changes) % 2 == 0


def test_capture_video_has_duration() -> None:
    events = build_schedule(_short_config(mode="video"))
    for event in events:
        if event.kind == "capture_video":
            assert event.payload["duration_s"] > 0


def test_shake_pairs_match(tmp_path: Path) -> None:
    events = build_schedule(_short_config(mode="video"))
    shaker_highs = [e for e in events
                    if e.kind == "pin_high" and e.payload.get("channel") == "shaker"]
    shaker_lows = [e for e in events
                   if e.kind == "pin_low" and e.payload.get("channel") == "shaker"]
    assert len(shaker_highs) == len(shaker_lows) == 8


def test_serialise_writes_one_line_per_event(tmp_path: Path) -> None:
    events = build_schedule(_short_config(mode="video"))
    out = serialise_schedule(events, tmp_path / "schedule.txt")
    lines = out.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(events)


def test_unknown_mode_raises() -> None:
    config = _short_config()
    config.mode = "carrier-pigeon"  # type: ignore[assignment]
    with pytest.raises(ValueError):
        build_schedule(config)
