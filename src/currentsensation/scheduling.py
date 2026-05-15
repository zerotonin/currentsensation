# ╔══════════════════════════════════════════════════════════════════╗
# ║  currentsensation — scheduling                                   ║
# ║  « pure-Python builder for an experiment timeline »              ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║  No hardware here. Produces a list of TimedEvent records that    ║
# ║  the orchestrator dispatches via sched. Trivially unit-testable. ║
# ╚══════════════════════════════════════════════════════════════════╝
"""Build a deterministic, replayable experiment timeline.

The schedule is the **single source of truth** for what happens when.
The orchestrator merely walks it; the hardware modules merely react.
Splitting this out means you can dry-run an experiment, inspect the
timeline, and unit-test it without ever touching a GPIO library.

The session layout follows the 2017 original:

```
[ off-trial ]            ← baseline
[ rep 1: line A, B, C ]  ← order randomised if requested
[ rep 2: line A, B, C ]
...
[ off-trial ]            ← recovery baseline
[ finish ]
```

Each *trial* consists of a shake stimulus immediately followed by a
current line being switched on for ``stim_dur`` seconds, with a video
(or stream of images) recorded across the shake-and-stim interval.
"""

from __future__ import annotations

import datetime as dt
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from currentsensation.constants import (
    CURRENT_LINES,
    DEFAULT_TIMING,
    LIGHT_OFFSET_S,
    OFF_TAG,
    SCHEDULE_FILENAME,
    ExperimentTiming,
    LineTag,
)

CaptureMode = Literal["video", "image"]

# ┌────────────────────────────────────────────────────────────┐
# │ Event record  « a single scheduled callback »              │
# └────────────────────────────────────────────────────────────┘

EventKind = Literal[
    "pin_high",
    "pin_low",
    "change_line",
    "capture_video",
    "capture_image",
    "finish",
]


@dataclass(frozen=True)
class TimedEvent:
    """A single thing-to-do at a given offset from session start.

    Attributes:
        offset_s: Seconds from the start of the session.
        kind:     What kind of event this is (drives orchestrator dispatch).
        payload:  Event-specific arguments.
        priority: Tiebreaker for events at the same offset (lower fires first).
    """

    offset_s: float
    kind: EventKind
    payload: dict = field(default_factory=dict)
    priority: int = 2


# ┌────────────────────────────────────────────────────────────┐
# │ Schedule config  « what to build a schedule for »          │
# └────────────────────────────────────────────────────────────┘


@dataclass
class ScheduleConfig:
    """Inputs to :func:`build_schedule`."""

    timing: ExperimentTiming = field(default_factory=lambda: DEFAULT_TIMING)
    lines: tuple[LineTag, ...] = CURRENT_LINES
    randomise_lines: bool = True
    mode: CaptureMode = "video"
    image_fps: int = 2


# ─────────────────────────────────────────────────────────────────
#  Public API
# ─────────────────────────────────────────────────────────────────


def build_schedule(
    config: ScheduleConfig,
    rng: random.Random | None = None,
) -> list[TimedEvent]:
    """Generate the full event timeline for one experimental session.

    Args:
        config: Timing, line set, capture mode.
        rng:    Random source for line-order shuffling. Defaults to a
                fresh :class:`random.Random` so tests can pass a seeded one.

    Returns:
        List of :class:`TimedEvent` sorted by ``(offset_s, priority)``.
    """
    rng = rng or random.Random()
    events: list[TimedEvent] = []
    cursor = config.timing.delay_offset

    # baseline off-trial
    cursor = _emit_trial(events, cursor, OFF_TAG, config)
    cursor += config.timing.peri_stim_dur

    # randomised reps
    for _ in range(config.timing.reps):
        lines = list(config.lines)
        if config.randomise_lines:
            rng.shuffle(lines)
        for line in lines:
            cursor = _emit_trial(events, cursor, line, config)
            cursor += config.timing.peri_stim_dur

    # recovery off-trial
    cursor = _emit_trial(events, cursor, OFF_TAG, config)
    cursor += config.timing.peri_stim_dur

    events.append(
        TimedEvent(cursor + 1.0, "finish", {"message": "Experiment finished!"}, priority=1)
    )
    return sorted(events, key=lambda e: (e.offset_s, e.priority))


def serialise_schedule(
    events: list[TimedEvent],
    out_path: Path,
    session_start: dt.datetime | None = None,
) -> Path:
    """Write a human-readable schedule file mirroring the 2017 format."""
    start = session_start or dt.datetime.now()
    with out_path.open("w", encoding="utf-8") as handle:
        for event in events:
            stamp = (start + dt.timedelta(seconds=event.offset_s)).strftime(
                "%Y-%m-%d--%H-%M-%S-%f--"
            )
            handle.write(f"{stamp}: {event.kind} {event.payload}\n")
    return out_path


def default_schedule_path(save_dir: Path) -> Path:
    """Where the schedule text file lives within a session directory."""
    return save_dir / SCHEDULE_FILENAME


# ─────────────────────────────────────────────────────────────────
#  Trial composition
# ─────────────────────────────────────────────────────────────────


def _emit_trial(
    events: list[TimedEvent],
    start: float,
    line: LineTag,
    config: ScheduleConfig,
) -> float:
    """Append events for one trial; return the offset at trial end."""
    shake_dur = config.timing.shake_dur
    stim_dur = config.timing.stim_dur

    shake_end = _emit_shake(events, start, shake_dur)
    _emit_line(events, shake_end, line, stim_dur)

    if config.mode == "video":
        capture_start = shake_end - shake_dur / 3.0
        capture_dur = stim_dur + shake_dur / 3.0
        _emit_video_capture(events, capture_start, capture_dur, line)
        return max(shake_end + stim_dur, capture_start + capture_dur)

    if config.mode == "image":
        _emit_image_burst(
            events,
            burst_start=shake_end,
            burst_end=shake_end + stim_dur,
            line=line,
            fps=config.image_fps,
        )
        return shake_end + stim_dur

    raise ValueError(f"Unknown capture mode: {config.mode!r}")


def _emit_shake(events: list[TimedEvent], start: float, duration: float) -> float:
    events.append(TimedEvent(start, "pin_high", {"channel": "shaker"}))
    events.append(TimedEvent(start + duration, "pin_low", {"channel": "shaker"}))
    return start + duration


def _emit_line(
    events: list[TimedEvent],
    start: float,
    line: LineTag,
    duration: float,
) -> None:
    events.append(TimedEvent(start, "change_line", {"line": line}))
    events.append(TimedEvent(start + duration, "change_line", {"line": OFF_TAG}))


def _emit_video_capture(
    events: list[TimedEvent],
    start: float,
    duration: float,
    line: LineTag,
) -> None:
    events.append(TimedEvent(start, "pin_high", {"channel": "light"}))
    events.append(
        TimedEvent(
            start,
            "capture_video",
            {"line": line, "duration_s": duration},
            priority=1,
        )
    )
    events.append(TimedEvent(start + duration, "pin_low", {"channel": "light"}))


def _emit_image_burst(
    events: list[TimedEvent],
    burst_start: float,
    burst_end: float,
    line: LineTag,
    fps: int,
) -> None:
    """Emit one light-pulse + frame-grab event triple per image."""
    period = 1.0 / fps
    n_frames = int(round((burst_end - burst_start) * fps))
    for i in range(n_frames):
        t = burst_start + i * period
        events.append(TimedEvent(t - LIGHT_OFFSET_S, "pin_high", {"channel": "light"}))
        events.append(
            TimedEvent(t, "capture_image", {"line": line}, priority=1)
        )
        events.append(TimedEvent(t + LIGHT_OFFSET_S, "pin_low", {"channel": "light"}))
