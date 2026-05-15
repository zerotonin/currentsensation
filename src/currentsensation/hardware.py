# ╔══════════════════════════════════════════════════════════════════╗
# ║  currentsensation — hardware                                     ║
# ║  « GPIO control with a swappable mock backend for off-Pi dev »   ║
# ╠══════════════════════════════════════════════════════════════════╣
# ║  Wraps RPi.GPIO behind a Protocol so the package imports and     ║
# ║  tests on any machine. The real backend is used on a Pi; the     ║
# ║  mock backend records state transitions for unit tests.          ║
# ╚══════════════════════════════════════════════════════════════════╝
"""GPIO control with pluggable backends.

The :class:`GPIOController` exposes domain-level operations
(``set_line_high``, ``all_off`` …) and delegates the actual pin toggling
to a backend.  Two backends ship with the package:

* :class:`RPiBackend` — real hardware via ``RPi.GPIO`` (only importable
  on a Raspberry Pi).
* :class:`MockBackend` — in-memory state for tests and dry-runs.

Picking the right backend is the responsibility of
:func:`make_default_controller`, which tries the real one and falls
back to the mock with a warning.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Protocol

from currentsensation.constants import CURRENT_LINES, DEFAULT_PINS, OFF_TAG, LineTag, PinMap

logger = logging.getLogger(__name__)


# ┌────────────────────────────────────────────────────────────┐
# │ Backend protocol  « anything that can flip a GPIO pin »    │
# └────────────────────────────────────────────────────────────┘


class GPIOBackend(Protocol):
    """Minimal interface a GPIO backend must implement."""

    def setup(self, pins: list[int]) -> None: ...
    def output_high(self, pin: int) -> None: ...
    def output_low(self, pin: int) -> None: ...
    def cleanup(self) -> None: ...


# ┌────────────────────────────────────────────────────────────┐
# │ Real backend  « RPi.GPIO, lazy imported »                  │
# └────────────────────────────────────────────────────────────┘


class RPiBackend:
    """Backend that drives real Broadcom GPIO pins via ``RPi.GPIO``."""

    def __init__(self) -> None:
        try:
            import RPi.GPIO as gpio  # noqa: N813
        except ImportError as exc:
            raise RuntimeError(
                "RPi.GPIO is not installed; install the 'pi' extra on a "
                "Raspberry Pi, or use MockBackend off-Pi."
            ) from exc
        self._gpio = gpio
        self._gpio.setmode(self._gpio.BCM)

    def setup(self, pins: list[int]) -> None:
        for pin in pins:
            self._gpio.setup(pin, self._gpio.OUT)
            self._gpio.output(pin, self._gpio.LOW)

    def output_high(self, pin: int) -> None:
        self._gpio.output(pin, self._gpio.HIGH)

    def output_low(self, pin: int) -> None:
        self._gpio.output(pin, self._gpio.LOW)

    def cleanup(self) -> None:
        self._gpio.cleanup()


# ┌────────────────────────────────────────────────────────────┐
# │ Mock backend  « records transitions, no hardware needed »  │
# └────────────────────────────────────────────────────────────┘


@dataclass
class PinTransition:
    """A single recorded pin state change."""

    timestamp: float
    pin: int
    state: bool


@dataclass
class MockBackend:
    """In-memory GPIO substitute for tests and dry-runs."""

    pin_state: dict[int, bool] = field(default_factory=dict)
    transitions: list[PinTransition] = field(default_factory=list)

    def setup(self, pins: list[int]) -> None:
        for pin in pins:
            self.pin_state[pin] = False
            self.transitions.append(PinTransition(time.monotonic(), pin, False))

    def output_high(self, pin: int) -> None:
        self.pin_state[pin] = True
        self.transitions.append(PinTransition(time.monotonic(), pin, True))

    def output_low(self, pin: int) -> None:
        self.pin_state[pin] = False
        self.transitions.append(PinTransition(time.monotonic(), pin, False))

    def cleanup(self) -> None:
        for pin in list(self.pin_state):
            self.output_low(pin)


# ┌────────────────────────────────────────────────────────────┐
# │ Controller facade  « the only class callers should use »   │
# └────────────────────────────────────────────────────────────┘


class UnknownLineError(KeyError):
    """Raised when a line tag does not exist in the pin map."""


class GPIOController:
    """Domain-level GPIO operations for the current-sensing rig."""

    def __init__(
        self,
        backend: GPIOBackend,
        pin_map: PinMap | None = None,
    ) -> None:
        self._backend = backend
        self._pin_map: PinMap = dict(pin_map) if pin_map else dict(DEFAULT_PINS)
        self._active_line: LineTag = OFF_TAG
        self._backend.setup(list(self._pin_map.values()))

    @property
    def active_line(self) -> LineTag:
        return self._active_line

    @property
    def pin_map(self) -> PinMap:
        return dict(self._pin_map)

    def set_line_high(self, line: LineTag) -> None:
        """Energise a named line, or turn everything off if ``line == 'off'``."""
        if line == OFF_TAG:
            self.all_off()
            return
        pin = self._lookup(line)
        self._backend.output_high(pin)
        self._active_line = line

    def set_line_low(self, line: LineTag) -> None:
        """De-energise a named line and mark the rig as off."""
        pin = self._lookup(line)
        self._backend.output_low(pin)
        self._active_line = OFF_TAG

    def change_current_line(self, line: LineTag) -> None:
        """Switch to ``line``: turn off all current lines first, then energise."""
        for tag in CURRENT_LINES:
            self._backend.output_low(self._pin_map[tag])
        self._active_line = line
        if line != OFF_TAG:
            self._backend.output_high(self._lookup(line))

    def all_off(self) -> None:
        """Drive every configured pin low."""
        for pin in self._pin_map.values():
            self._backend.output_low(pin)
        self._active_line = OFF_TAG

    def cleanup(self) -> None:
        """Release backend resources (idempotent)."""
        self._backend.cleanup()

    def _lookup(self, line: LineTag) -> int:
        try:
            return self._pin_map[line]
        except KeyError as exc:
            raise UnknownLineError(
                f"line {line!r} not in pin map {sorted(self._pin_map)}"
            ) from exc


# ─────────────────────────────────────────────────────────────────
#  Factory
# ─────────────────────────────────────────────────────────────────


def make_default_controller(
    pin_map: PinMap | None = None,
    *,
    force_mock: bool = False,
) -> GPIOController:
    """Return a controller with the best available backend.

    Args:
        pin_map:    Optional override for the line→pin assignment.
        force_mock: If True, never attempt the real backend.

    Returns:
        A :class:`GPIOController` ready to drive lines.
    """
    if force_mock:
        return GPIOController(MockBackend(), pin_map=pin_map)
    try:
        backend: GPIOBackend = RPiBackend()
    except RuntimeError:
        logger.warning("RPi.GPIO unavailable — using MockBackend")
        backend = MockBackend()
    return GPIOController(backend, pin_map=pin_map)
