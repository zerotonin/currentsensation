# ╔══════════════════════════════════════════════════════════════════╗
# ║  currentsensation — capture                                      ║
# ║  « video (ffmpeg) and image (pygame) acquisition »               ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║  Thin wrappers around external capture tools. Subprocess only;   ║
# ║  no shell strings. Save paths are pathlib.Path everywhere.       ║
# ╚══════════════════════════════════════════════════════════════════╝
"""Video and image capture wrappers.

``VideoCapture`` spawns an ``ffmpeg`` process for the requested duration;
``ImageCapture`` grabs single frames via ``pygame.camera``.  Both expose
a uniform :meth:`record` method that writes a single timestamped file
into the session directory.

The capture backends are interchangeable from the experiment
orchestrator's perspective — picking video vs images is a CLI decision.
"""

from __future__ import annotations

import datetime as dt
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from currentsensation.constants import (
    DEFAULT_CAPTURE,
    IMAGE_EXT,
    IMAGE_FPS_MAX,
    TIMESTAMP_FMT,
    VIDEO_EXT,
    CaptureConfig,
    LineTag,
)

logger = logging.getLogger(__name__)


# ┌────────────────────────────────────────────────────────────┐
# │ Capture protocol  « uniform record() entry point »         │
# └────────────────────────────────────────────────────────────┘


class CaptureBackend(Protocol):
    """Any capture backend the orchestrator can drive."""

    def record(self, save_dir: Path, line: LineTag, duration_s: float) -> Path: ...
    def close(self) -> None: ...


# ─────────────────────────────────────────────────────────────────
#  Filename helper
# ─────────────────────────────────────────────────────────────────


def build_filename(save_dir: Path, line: LineTag, extension: str) -> Path:
    """Compose `<save_dir>/<timestamp>-<line><ext>` with current time."""
    stamp = dt.datetime.now().strftime(TIMESTAMP_FMT)
    return save_dir / f"{stamp}{line}{extension}"


# ┌────────────────────────────────────────────────────────────┐
# │ Video capture  « non-blocking ffmpeg invocation »          │
# └────────────────────────────────────────────────────────────┘


@dataclass
class VideoCapture:
    """ffmpeg-based video recorder."""

    config: CaptureConfig = DEFAULT_CAPTURE

    def record(self, save_dir: Path, line: LineTag, duration_s: float) -> Path:
        """Spawn ffmpeg to record ``duration_s`` seconds into a new file."""
        out_path = build_filename(save_dir, line, VIDEO_EXT)
        cmd = [
            "ffmpeg",
            "-t", f"{duration_s}",
            "-f", "v4l2",
            "-an",
            "-r", f"{self.config.fps}",
            "-s", f"{self.config.width}x{self.config.height}",
            "-i", self.config.device,
            str(out_path),
        ]
        logger.info("ffmpeg: %s", " ".join(cmd))
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return out_path

    def close(self) -> None:
        """No-op; ffmpeg processes terminate themselves at -t."""


# ┌────────────────────────────────────────────────────────────┐
# │ Image capture  « pygame, single frames, lazy import »      │
# └────────────────────────────────────────────────────────────┘


class ImageCapture:
    """pygame.camera-based single-frame grabber."""

    def __init__(self, config: CaptureConfig = DEFAULT_CAPTURE) -> None:
        if config.fps > IMAGE_FPS_MAX:
            raise ValueError(
                f"Image capture above {IMAGE_FPS_MAX} fps is unreliable; "
                "use VideoCapture instead."
            )
        try:
            import pygame
            import pygame.camera
        except ImportError as exc:
            raise RuntimeError(
                "pygame is not installed; install the 'pi' extra."
            ) from exc
        self._pygame = pygame
        self._pygame.camera.init()
        self._cam = self._pygame.camera.Camera(
            config.device, (config.width, config.height)
        )
        self._cam.start()
        self.config = config

    def record(
        self,
        save_dir: Path,
        line: LineTag,
        duration_s: float = 0.0,  # accepted for protocol parity; ignored
    ) -> Path:
        """Grab one frame and write it as JPEG."""
        del duration_s  # single-frame capture
        out_path = build_filename(save_dir, line, IMAGE_EXT)
        image = self._cam.get_image()
        self._pygame.image.save(image, str(out_path))
        return out_path

    def close(self) -> None:
        self._cam.stop()


# ┌────────────────────────────────────────────────────────────┐
# │ Null capture  « used by --dry-run for offline development » │
# └────────────────────────────────────────────────────────────┘


@dataclass
class NullCapture:
    """No-op capture backend that only logs what would have been recorded."""

    extension: str = VIDEO_EXT

    def record(self, save_dir: Path, line: LineTag, duration_s: float) -> Path:
        out_path = build_filename(save_dir, line, self.extension)
        logger.info("would record %.1fs %s → %s", duration_s, line, out_path)
        return out_path

    def close(self) -> None:
        """No-op."""
