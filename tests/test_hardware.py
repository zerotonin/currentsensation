"""GPIOController + MockBackend behaviour."""

from __future__ import annotations

import pytest

from currentsensation.constants import CURRENT_LINES, DEFAULT_PINS, OFF_TAG
from currentsensation.hardware import (
    GPIOController,
    MockBackend,
    UnknownLineError,
    make_default_controller,
)


@pytest.fixture
def controller() -> GPIOController:
    return GPIOController(MockBackend())


def test_setup_initialises_all_pins_low(controller: GPIOController) -> None:
    backend = controller._backend  # noqa: SLF001 — test introspection
    for pin in DEFAULT_PINS.values():
        assert backend.pin_state[pin] is False


def test_set_line_high_energises_only_target(controller: GPIOController) -> None:
    controller.set_line_high("red")
    backend = controller._backend  # noqa: SLF001
    assert backend.pin_state[DEFAULT_PINS["red"]] is True
    for tag in ("blue", "yellow", "light", "shaker"):
        assert backend.pin_state[DEFAULT_PINS[tag]] is False
    assert controller.active_line == "red"


def test_set_line_high_off_drives_all_low(controller: GPIOController) -> None:
    controller.set_line_high("red")
    controller.set_line_high(OFF_TAG)
    backend = controller._backend  # noqa: SLF001
    assert all(state is False for state in backend.pin_state.values())
    assert controller.active_line == OFF_TAG


def test_change_current_line_clears_previous(controller: GPIOController) -> None:
    controller.change_current_line("red")
    controller.change_current_line("blue")
    backend = controller._backend  # noqa: SLF001
    assert backend.pin_state[DEFAULT_PINS["red"]] is False
    assert backend.pin_state[DEFAULT_PINS["blue"]] is True
    assert controller.active_line == "blue"


def test_change_current_line_off(controller: GPIOController) -> None:
    controller.change_current_line("red")
    controller.change_current_line(OFF_TAG)
    backend = controller._backend  # noqa: SLF001
    for tag in CURRENT_LINES:
        assert backend.pin_state[DEFAULT_PINS[tag]] is False


def test_unknown_line_raises(controller: GPIOController) -> None:
    with pytest.raises(UnknownLineError):
        controller.set_line_high("magenta")


def test_all_off_drives_every_pin_low(controller: GPIOController) -> None:
    controller.set_line_high("red")
    controller.set_line_high("light")
    controller.all_off()
    backend = controller._backend  # noqa: SLF001
    assert all(state is False for state in backend.pin_state.values())


def test_factory_falls_back_to_mock_off_pi() -> None:
    controller = make_default_controller(force_mock=True)
    assert isinstance(controller._backend, MockBackend)  # noqa: SLF001


def test_factory_handles_missing_rpi_gracefully() -> None:
    # On a non-Pi machine this is the normal path; on a Pi it should also
    # work as long as the mock can be forced.
    controller = make_default_controller()
    controller.set_line_high("red")
    controller.cleanup()
