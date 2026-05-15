currentsensation
================

Raspberry-Pi controller for fish electroreception experiments.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   overview
   api

Overview
--------

``currentsensation`` drives three colour-coded GPIO current lines, a
startle shaker and a camera light, synchronising them against a single
declarative schedule.  The schedule itself is pure Python and can be
inspected with ``currentsensation schedule --save-dir ./out`` without
touching any hardware.

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
