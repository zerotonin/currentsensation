Overview
========

Pipeline
--------

``currentsensation`` is structured as five small modules:

* :mod:`currentsensation.constants` — pin map, durations, palette.
* :mod:`currentsensation.hardware` — GPIO controller with mock backend.
* :mod:`currentsensation.capture` — video (ffmpeg) and image (pygame).
* :mod:`currentsensation.scheduling` — pure-Python timeline builder.
* :mod:`currentsensation.experiment` — orchestrator wiring it together.

The CLI lives in :mod:`currentsensation.cli`.

Off-Pi development
------------------

The package is designed to import on any Linux/macOS/Windows machine.
``RPi.GPIO`` and ``pygame`` are optional dependencies imported lazily;
when they are unavailable, the :class:`MockBackend` records pin
transitions in memory so that scheduling logic can be unit-tested
without hardware.

Use ``--mock-gpio`` on the CLI or pass ``force_mock=True`` to
:func:`make_default_controller` to force the mock backend.
