# Legacy code (2017, Python 2)

These two files are the original `currentsensation` codebase as it ran on
the lab Raspberry Pi between roughly 2017 and 2020.  They are kept here
for historical and provenance reasons only — **they do not run on Python 3**
(statement-form `print`, unbracketed exception handlers, etc.).

The 2026 refactor lives under `src/currentsensation/`.  The mapping is:

| Legacy                                                | New                                                |
|-------------------------------------------------------|----------------------------------------------------|
| `currentSensation.py` `currentExp.__init__` pin setup | `currentsensation.constants` + `hardware.GPIOController` |
| `currentSensation.py` `setPinHigh/Low`, `allOut`      | `hardware.GPIOController`                          |
| `currentSensation.py` `setExperimentSchedule*`        | `scheduling.build_schedule`                        |
| `currentSensation.py` `captureVidSched`               | `capture.VideoCapture`                             |
| `currentSensation.py` `captureImgSched`               | `capture.ImageCapture`                             |
| `currentSensation.py` `runExperiment`                 | `experiment.Experiment.run`                        |
| `experimentCurrent.py`                                | `cli.main`                                         |

Do not import from `_legacy/`.  Anything worth keeping has been ported.
