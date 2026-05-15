# ╔══════════════════════════════════════════════════════════════════╗
# ║  currentsensation — cli                                          ║
# ║  « argparse entry point »                                        ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║  Replaces the 30-line experimentCurrent.py runner from 2017      ║
# ║  with a proper command-line interface.                           ║
# ╚══════════════════════════════════════════════════════════════════╝
"""Command-line entry point for ``currentsensation run``."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from currentsensation import __version__
from currentsensation.capture import CaptureBackend, NullCapture, VideoCapture
from currentsensation.constants import (
    CURRENT_LINES,
    DEFAULT_CAPTURE,
    DEFAULT_TIMING,
    IMAGE_EXT,
    SessionPaths,
    VIDEO_EXT,
)
from currentsensation.experiment import Experiment
from currentsensation.hardware import make_default_controller
from currentsensation.scheduling import CaptureMode, ScheduleConfig


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, build the experiment, dispatch."""
    parser = _build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
    )

    if args.command == "run":
        return _cmd_run(args)
    if args.command == "schedule":
        return _cmd_schedule(args)
    parser.print_help()
    return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="currentsensation",
        description=(
            "Raspberry-Pi controller for insect electroreception experiments."
        ),
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Execute a session on the connected hardware.")
    _add_session_args(run)
    run.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the schedule and write it to disk; do not drive hardware.",
    )
    run.add_argument(
        "--mock-gpio",
        action="store_true",
        help="Force the mock GPIO backend even on a Raspberry Pi.",
    )

    sched = sub.add_parser(
        "schedule",
        help="Print the planned event timeline without running anything.",
    )
    _add_session_args(sched)

    return parser


def _add_session_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--save-dir", type=Path, required=True,
                        help="Directory for output files (created if missing).")
    parser.add_argument("--reps", type=int, default=DEFAULT_TIMING.reps,
                        help="Number of randomised repetitions.")
    parser.add_argument("--stim-dur", type=float, default=DEFAULT_TIMING.stim_dur,
                        help="Stimulus duration (s).")
    parser.add_argument("--peri-stim-dur", type=float,
                        default=DEFAULT_TIMING.peri_stim_dur,
                        help="Inter-trial interval (s).")
    parser.add_argument("--shake-dur", type=float, default=DEFAULT_TIMING.shake_dur,
                        help="Shaker stimulus duration (s).")
    parser.add_argument(
        "--lines",
        type=_parse_lines,
        default=",".join(CURRENT_LINES),
        help="Comma-separated current line tags (default: red,blue,yellow).",
    )
    parser.add_argument(
        "--no-randomise",
        action="store_true",
        help="Disable shuffling of line order between reps.",
    )
    parser.add_argument(
        "--capture",
        choices=("video", "image"),
        default="video",
        help="Capture mode.",
    )
    parser.add_argument("--fps", type=int, default=DEFAULT_CAPTURE.fps,
                        help="Camera frame rate (default 25 video / 2 image).")


def _parse_lines(text: str) -> tuple[str, ...]:
    return tuple(token.strip() for token in text.split(",") if token.strip())


def _build_config(args: argparse.Namespace) -> ScheduleConfig:
    from dataclasses import replace

    timing = replace(
        DEFAULT_TIMING,
        shake_dur=args.shake_dur,
        peri_stim_dur=args.peri_stim_dur,
        stim_dur=args.stim_dur,
        reps=args.reps,
    )
    return ScheduleConfig(
        timing=timing,
        lines=tuple(args.lines),
        randomise_lines=not args.no_randomise,
        mode=args.capture,
        image_fps=args.fps if args.capture == "image" else 2,
    )


def _cmd_schedule(args: argparse.Namespace) -> int:
    """Print the event list to stdout without touching hardware."""
    from currentsensation.scheduling import build_schedule

    paths = SessionPaths.from_root(args.save_dir)
    config = _build_config(args)
    events = build_schedule(config)
    for event in events:
        print(f"  {event.offset_s:10.3f}s  [p{event.priority}]  "
              f"{event.kind:14s}  {event.payload}")
    print(f"\n{len(events)} events  →  {paths.root}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    paths = SessionPaths.from_root(args.save_dir)
    config = _build_config(args)

    controller = make_default_controller(force_mock=args.mock_gpio)

    capture: CaptureBackend
    if args.dry_run:
        ext = VIDEO_EXT if args.capture == "video" else IMAGE_EXT
        capture = NullCapture(extension=ext)
    elif args.capture == "video":
        capture = VideoCapture()
    else:
        from currentsensation.capture import ImageCapture
        capture = ImageCapture()

    experiment = Experiment(controller=controller, capture=capture, paths=paths)
    experiment.run(config, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
