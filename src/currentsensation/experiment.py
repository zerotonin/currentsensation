# ╔══════════════════════════════════════════════════════════════════╗
# ║  currentsensation — experiment                                   ║
# ║  « orchestrator wiring scheduling, hardware and capture »        ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║  Thin glue layer. Holds no business logic of its own; reads      ║
# ║  the schedule and dispatches callbacks at the right moments.     ║
# ╚══════════════════════════════════════════════════════════════════╝
"""Run an experimental session given a schedule and the hardware to drive."""

from __future__ import annotations

import logging
import sched
import time
from dataclasses import dataclass
from pathlib import Path

from currentsensation.capture import CaptureBackend
from currentsensation.constants import OFF_TAG, SessionPaths
from currentsensation.hardware import GPIOController
from currentsensation.scheduling import (
    ScheduleConfig,
    TimedEvent,
    build_schedule,
    default_schedule_path,
    serialise_schedule,
)

logger = logging.getLogger(__name__)


class ScheduleFinished(SystemExit):
    """Raised inside a scheduled callback to terminate the session cleanly."""


@dataclass
class Experiment:
    """Drive a single experimental session."""

    controller: GPIOController
    capture: CaptureBackend
    paths: SessionPaths

    def run(
        self,
        config: ScheduleConfig,
        *,
        dry_run: bool = False,
    ) -> list[TimedEvent]:
        """Build a schedule, write it to disk, and (optionally) execute it.

        Args:
            config:  What to schedule.
            dry_run: If True, do not enter the scheduler loop; just write
                     the schedule file and return the event list.

        Returns:
            The sorted event list that was scheduled.
        """
        events = build_schedule(config)
        serialise_schedule(events, default_schedule_path(self.paths.root))
        if dry_run:
            logger.info("dry-run: %d events written to %s",
                        len(events), self.paths.schedule_file)
            return events

        timer = sched.scheduler(time.time, time.sleep)
        session_start = time.time()
        for event in events:
            timer.enter(
                event.offset_s,
                event.priority,
                self._dispatch,
                argument=(event,),
            )
        logger.info("starting session with %d events", len(events))
        try:
            timer.run()
        except ScheduleFinished as exit_:
            logger.info("session finished after %.1fs: %s",
                        time.time() - session_start, exit_)
        finally:
            self.controller.cleanup()
            self.capture.close()
        return events

    # ─────────────────────────────────────────────────────────────
    #  Dispatch table
    # ─────────────────────────────────────────────────────────────

    def _dispatch(self, event: TimedEvent) -> None:
        handler = _HANDLERS[event.kind]
        handler(self, event)


def _on_pin_high(exp: Experiment, event: TimedEvent) -> None:
    exp.controller.set_line_high(event.payload["channel"])


def _on_pin_low(exp: Experiment, event: TimedEvent) -> None:
    exp.controller.set_line_low(event.payload["channel"])


def _on_change_line(exp: Experiment, event: TimedEvent) -> None:
    exp.controller.change_current_line(event.payload["line"])


def _on_capture_video(exp: Experiment, event: TimedEvent) -> None:
    exp.capture.record(
        save_dir=exp.paths.root,
        line=event.payload["line"],
        duration_s=event.payload["duration_s"],
    )


def _on_capture_image(exp: Experiment, event: TimedEvent) -> None:
    exp.capture.record(
        save_dir=exp.paths.root,
        line=event.payload["line"],
        duration_s=0.0,
    )


def _on_finish(exp: Experiment, event: TimedEvent) -> None:
    exp.controller.all_off()
    raise ScheduleFinished(event.payload.get("message", "done"))


_HANDLERS = {
    "pin_high":      _on_pin_high,
    "pin_low":       _on_pin_low,
    "change_line":   _on_change_line,
    "capture_video": _on_capture_video,
    "capture_image": _on_capture_image,
    "finish":        _on_finish,
}
