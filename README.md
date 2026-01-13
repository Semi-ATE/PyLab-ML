# Pylab-ML


[![GitHub](https://img.shields.io/github/license/Semi-ATE/PyLab-ML?color=black)](https://github.com/Semi-ATE/PyLab-ML/blob/master/LICENSE.txt)
[![Supported Python versions](https://img.shields.io/badge/python-%3E%3D3.9-black)](https://www.python.org/downloads/)
[![CI-CD](https://github.com/Semi-ATE/PyLab-ML/workflows/CI-CD/badge.svg)](https://github.com/Semi-ATE/PyLab-ML/actions/workflows/CICD.yml?query=workflow%3ACD)

[![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/Semi-ATE/PyLab-ML?color=blue&label=GitHub&sort=semver)](https://github.com/Semi-ATE/PyLab-ML/releases/latest)
[![GitHub commits since latest release (by date)](https://img.shields.io/github/commits-since/Semi-ATE/PyLab-ML/latest)](https://github.com/Semi-ATE/PyLab-ML)
[![GitHub issues](https://img.shields.io/github/issues/Semi-ATE/PyLab-ML)](https://github.com/Semi-ATE/PyLab-ML/issues)
[![GitHub pull requests](https://img.shields.io/github/issues-pr/Semi-ATE/PyLab-ML)](https://github.com/Semi-ATE/SPyLab-ML/pulls)

[![PyPI](https://img.shields.io/pypi/v/Pylab-ML?color=blue&label=PyPI)](https://pypi.org/project/Pylab-ML/)


## Indroduction

We developed this package to be able to address electronic instruments relatively simply over their different interfaces (e.q. serial, GBIP, PXIe ...).
It was very important for us to be able to switch to other devices from other manufacturers within a measurement setup without having to change much of the actual code for the measurements.

In conjunction with **[Semi-ATE ](https://github.com/Semi-ATE/Semi-ATE)** you can create your own test machine and then run testflows with different testbenches.


## Documentaion

You can read the Pylab-ML documentation online on [here](https://semi-ate.github.io/PyLab-ML/)

## Instrument ready

The package includes a number of instruments already defined.

Their definitions are organized by their function, for example smu, dmm, scope. And then by the manufacturer name of the instrument.
For example the class that defines the National Instrument PXIE 4138 SourceMeter can be imported by calling:

```bash
from pylab_ml.smu.natinst.pxie41xx import PXIe41xx
...
```

## Installation via pip (Development mode)

activate your Semi-ATE environment

```bash
conda activate <your environment>
cd ~/repos/<your environment>
git clone https://github.com/Semi-ATE/PyLab-ML.git

cd PyLab-ML
pip install -e .						# install the pylab-ml instrument lib, the spyder plugin for semi-ate in the General Purpose Funktions from the hardwaresetup,
										# and the STDF-data widget for spyder
```

When we started with this package we did not know **[pymeasure ](https://pymeasure.readthedocs.io/en/latest/introduction.html)** yet. Therefore there are some overlaps with this package.