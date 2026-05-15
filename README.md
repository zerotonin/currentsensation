# currentsensation

[![tests](https://github.com/zerotonin/currentsensation/actions/workflows/tests.yml/badge.svg)](https://github.com/zerotonin/currentsensation/actions/workflows/tests.yml)
[![docs](https://github.com/zerotonin/currentsensation/actions/workflows/docs.yml/badge.svg)](https://zerotonin.github.io/currentsensation/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Raspberry-Pi experiment controller for **fish electroreception assays**:
three colour-coded GPIO-driven current lines, a startle shaker, a light,
and synchronised video or image capture.

Originally written in 2017 (Python 2) for a single experiment; refactored
in 2026 into a small Python 3.11+ package with a mock GPIO backend so the
scheduling and analysis pieces can be developed and tested off-Pi.

## Hardware

| Channel | Default GPIO (BCM) | Purpose                            |
|---------|--------------------|------------------------------------|
| red     | 18                 | current line A                     |
| blue    | 24                 | current line B                     |
| yellow  |  8                 | current line C                     |
| light   | 14                 | illumination for camera frames     |
| shaker  | 13                 | mechanical startle stimulus        |

Pin assignments live in `currentsensation.constants` and can be overridden
per deployment.

## Install

```bash
# off-Pi development (mock GPIO backend, no RPi.GPIO needed)
pip install -e ".[dev]"

# on a Raspberry Pi
pip install -e ".[pi]"
```

## Quickstart

```bash
currentsensation run \
    --save-dir /mnt/data/expt-2026-05-15 \
    --reps 3 \
    --stim-dur 1800 \
    --peri-stim-dur 30 \
    --shake-dur 30 \
    --lines red,blue,yellow \
    --capture video
```

## Citation

If you use this software, please cite via the metadata in
[`CITATION.cff`](CITATION.cff).
