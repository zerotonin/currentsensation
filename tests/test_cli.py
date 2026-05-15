"""CLI argument parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from currentsensation.cli import main


def test_schedule_subcommand_runs(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    rc = main([
        "schedule",
        "--save-dir", str(tmp_path),
        "--reps", "1",
        "--stim-dur", "10",
        "--peri-stim-dur", "2",
        "--shake-dur", "3",
        "--capture", "video",
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "events" in out
    assert "finish" in out


def test_run_dry_run_with_mock_gpio(tmp_path: Path) -> None:
    rc = main([
        "run",
        "--save-dir", str(tmp_path),
        "--reps", "1",
        "--stim-dur", "10",
        "--peri-stim-dur", "2",
        "--shake-dur", "3",
        "--capture", "video",
        "--dry-run",
        "--mock-gpio",
    ])
    assert rc == 0
    assert (tmp_path / "lastExpSchedule.txt").exists()


def test_lines_parse_comma_separated(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    main([
        "schedule",
        "--save-dir", str(tmp_path),
        "--lines", "red,blue",
        "--reps", "1",
        "--no-randomise",
        "--stim-dur", "5",
        "--peri-stim-dur", "1",
        "--shake-dur", "1",
    ])
    out = capsys.readouterr().out
    # baseline + 1 rep * 2 lines + recovery = 4 capture_video events
    assert out.count("capture_video") == 4
    assert "yellow" not in out
