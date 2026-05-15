"""currentsensation — RPi controller for fish electroreception assays."""

from __future__ import annotations

try:
    from currentsensation._version import version as __version__
except ImportError:  # editable install before setuptools-scm ran
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
