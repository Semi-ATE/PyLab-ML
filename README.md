## Indroduction

We developed this package to be able to address electronic instruments relatively simply over their different interfaces (e.q. serial, GBIP, PXIe ...).
It was very important for us to be able to switch to other devices from other manufacturers within a measurement setup without having to change much of the actual code for the measurements.

In conjunction with **[Semi-ATE ](https://github.com/Semi-ATE/Semi-ATE)** you can create your own test machine and then run testflows with different testbenches.

When we started with this package we did not know **[pymeasure ](https://pymeasure.readthedocs.io/en/latest/introduction.html)** yet. Therefore there are some overlaps with this package.

## Instrument ready

The package includes a number of instruments already defined.

Their definitions are organized by their function, for example smu, dmm, scope. And then by the manufacturer name of the instrument.
For example the class that defines the National Instrument PXIE 4138 SourceMeter can be imported by calling:

```bash
from labml_instruments.smu.natinst.pxie41xx import PXIe41xx
...
```

## Installation via pip (Development mode)

activate your Semi-ATE environment

```bash
conda activate <your environment>
cd ~/repos/<your environment>
git clone https://github.com/Semi-ATE/LAB-ML.git

cd LAB-ML/src/labml_instruments
pip install -e .

cd ../plugins/labml-instruments         # install the spyder plugin for semi-ate in the General Purpose Funktions from the hardwaresetups
pip install -e .

cd ../plugins\stdf_browser              # install the STDF-data widget for spyder
pip install -e .
...
```

 The detailed description of the different devices with functions and attributes can be found [here](https://semi-ate.github.io/LAB-ML/)
