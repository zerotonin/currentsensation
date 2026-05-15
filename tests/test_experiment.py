"""End-to-end experiment dry-run with the mock GPIO backend."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from currentsensation.capture import NullCapture
from currentsensation.constants import DEFAULT_TIMING, SessionPaths
from currentsensation.experiment import Experiment
from currentsensation.hardware import GPIOController, MockBackend
from currentsensation.scheduling import ScheduleConfig


def test_dry_run_writes_schedule_and_returns_events(tmp_path: Path) -> None:
    paths = SessionPaths.from_root(tmp_path / "session")
    experiment = Experiment(
        controller=GPIOController(MockBackend()),
        capture=NullCapture(),
        paths=paths,
    )
    timing = replace(
        DEFAULT_TIMING,
        shake_dur=3.0,
        peri_stim_dur=2.0,
        stim_dur=10.0,
        delay_offset=1.0,
        reps=1,
    )
    events = experiment.run(ScheduleConfig(timing=timing), dry_run=True)
    assert paths.schedule_file.exists()
    assert events[-1].kind == "finish"
