# ╔══════════════════════════════════════════════════════════════════╗
# ║  currentsensation — constants                                    ║
# ║  « pins, durations, paths and Wong palette in one place »        ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║  Central configuration for the Raspberry Pi current-sensing      ║
# ║  experiment. Import this module rather than hardcoding values.   ║
# ╚══════════════════════════════════════════════════════════════════╝
"""Shared constants for the currentsensation package."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeAlias

# ┌────────────────────────────────────────────────────────────┐
# │ Type aliases  « short names for repeated structures »      │
# └────────────────────────────────────────────────────────────┘

LineTag: TypeAlias = str
PinMap: TypeAlias = dict[str, int]

# ┌────────────────────────────────────────────────────────────┐
# │ GPIO pin map  « BCM numbering, RPi Model B+ »              │
# └────────────────────────────────────────────────────────────┘

DEFAULT_PINS: PinMap = {
    "red":    18,
    "blue":   24,
    "yellow":  8,
    "light":  14,
    "shaker": 13,
}

CURRENT_LINES: tuple[LineTag, ...] = ("red", "blue", "yellow")
OFF_TAG: LineTag = "off"

# ┌────────────────────────────────────────────────────────────┐
# │ Default durations  « seconds, override via CLI »           │
# └────────────────────────────────────────────────────────────┘


@dataclass(frozen=True)
class ExperimentTiming:
    """Default time intervals for an experimental session.

    All durations are in seconds.
    """

    shake_dur: float = 30.0
    peri_stim_dur: float = 30.0
    stim_dur: float = 1800.0
    delay_offset: float = 5.0
    reps: int = 3


DEFAULT_TIMING = ExperimentTiming()

# Image-capture light pulse duration around each frame.
LIGHT_OFFSET_S: float = 0.2

# Maximum frame rate before image capture must defer to video.
IMAGE_FPS_MAX: int = 9

# ┌────────────────────────────────────────────────────────────┐
# │ Capture defaults  « camera resolution and fps »            │
# └────────────────────────────────────────────────────────────┘


@dataclass(frozen=True)
class CaptureConfig:
    """Default camera and recording parameters."""

    width: int = 640
    height: int = 480
    fps: int = 25
    device: str = "/dev/video0"


DEFAULT_CAPTURE = CaptureConfig()

# ┌────────────────────────────────────────────────────────────┐
# │ Output path templates  « datetime + line tag »             │
# └────────────────────────────────────────────────────────────┘

TIMESTAMP_FMT: str = "%Y-%m-%d--%H-%M-%S-%f--"
VIDEO_EXT: str = ".avi"
IMAGE_EXT: str = ".jpg"
SCHEDULE_FILENAME: str = "lastExpSchedule.txt"

# ┌────────────────────────────────────────────────────────────┐
# │ Wong (2011) palette  « colourblind-safe base colours »     │
# └────────────────────────────────────────────────────────────┘

WONG: dict[str, str] = {
    "black":          "#000000",
    "orange":         "#E69F00",
    "sky_blue":       "#56B4E9",
    "bluish_green":   "#009E73",
    "yellow":         "#F0E442",
    "blue":           "#0072B2",
    "vermilion":      "#D55E00",
    "reddish_purple": "#CC79A7",
}

# Semantic mapping of experimental line tags to plotting colours.  The
# tags "red"/"blue"/"yellow" are hardware labels, not perceptual ones;
# they map onto colourblind-safe equivalents for figures.
LINE_COLOURS: dict[LineTag, str] = {
    "red":    WONG["vermilion"],
    "blue":   WONG["blue"],
    "yellow": WONG["orange"],
    "off":    WONG["black"],
}

# ┌────────────────────────────────────────────────────────────┐
# │ Figure defaults  « used by any future plotting modules »   │
# └────────────────────────────────────────────────────────────┘

FIGURE_DPI: int = 200
FIGURE_SIZE_IN: tuple[float, float] = (6.0, 4.0)


@dataclass(frozen=True)
class SessionPaths:
    """Container for output paths derived from a session save directory."""

    root: Path
    schedule_file: Path = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "schedule_file", self.root / SCHEDULE_FILENAME)

    @classmethod
    def from_root(cls, root: Path | str) -> SessionPaths:
        """Build a SessionPaths from a root directory (created if missing)."""
        root_path = Path(root).expanduser().resolve()
        root_path.mkdir(parents=True, exist_ok=True)
        return cls(root=root_path)
