"""Measuremet-Unit (SMU) Keithley2000.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>

"""
from pylab_ml.base_instrument import logger
from pylab_ml.collate_instrument import Interface
from pylab_ml.smu.keithley.base_keithley import Keithley


class Keithley2000(Keithley):
    """Interface to the Measuremet-Unit (SMU) Keithley2000.

    The Keithley2000 can measure voltage and current precisely

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    .. image:: ../_static/kethley2000.jpg

    """

    interchoices = [Interface.usbserial, Interface.gpib]

    def __init__(self, addr=None, interface=None, backend=None, identify=True, instName=None, **kwargs):
        """Connect and initialize.

        Args:
           addr (int):
              interface address
           interface (Interface):
              gpib, usbserial
           backend (str):
              visa backend is either '@ni' for NI-Library or
              '@py' for pure python pyvisa-py backend.
              On default it uses '@ni' on win32 and '@py' on
              other platforms.
           instName (string):
              Instance Name from parent.

        Example: Initialization
           >>> vdd = Keithley2000(addr=24)  # GPIB or USB address
           >>> vdd.init()                   # connect and initialize instrument

        Example: Current measurement
           >>> i = vdd.current              # measure (supply) current

        Example: Voltage measurement
           >>> v = vdd.voltage              # measure voltage

        """
        kwargs = {"addr": addr, "interface": interface, "backend": backend, "identify": identify, "instName": instName, **kwargs}
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
        self.msg_row_col = (1, 12)

    def setup_inst(self):
        """Start setup instrument settings, called from class instruments."""
        super().setup_inst()
        self._nplc = 1.0
        self.per_threshold = 1.0
        self.per_aperture = 1.0
        self.freq_threshold = 1.0
        self.freq_aperture = 1.0
        if self.inst:
            if self.interface == Interface.gpib:
                self.inst.read_termination = '\n'
                self.inst.write_termination = '\n'
            else:
                self.inst.read_termination = '\r'
                self.inst.write_termination = '\r'

    def error_list(self):
        """List of instrument errors."""
        self.budget.set_slack(self)
        errorlist = []
        while True:
            errormsg = self.inst.query(':SYST:ERR?')
            if errormsg is None or errormsg == "":
                break
            (c, m) = errormsg.split(",")
            print("{} : {}".format(c, m))
            errorlist.append((c, m))
            if errormsg == '0, "No error"':
                break
        return errorlist

    @property
    def nplc(self):
        """Set the conversion number of power line cycles accuracy, for all converters.

        for a plc of 1, conversion rate is 1/50s = 20ms, max 10, min 0.1 accuracy
        """
        val = self._nplc
        return float(val)

    @nplc.setter
    def nplc(self, cycles):            # cycles are number of power line cycles for conversion
        self._nplc = cycles
        self.budget.set_slack(self)
        # in Keithley 2000 each measurement has separate accuracy in reality
        self.inst.write(':SENS:VOLT:NPLC {}'.format(cycles))
        self.inst.write(':SENS:CURR:NPLC {}'.format(cycles))
        self.inst.write(':SENS:VOLT:AC:NPLC {}'.format(cycles))
        self.inst.write(':SENS:CURR:AC:NPLC {}'.format(cycles))
        self.inst.write(':SENS:RES:NPLC {}'.format(cycles))
        self.inst.write(':SENS:FRES:NPLC {}'.format(cycles))
        self.inst.write(':SENS:TEMP:NPLC {}'.format(cycles))

    @property
    def v_autorange(self):
        """Autorange voltage measurement on or off."""
        self.budget.set_slack(self)
        res = self.inst.query(':SENS:VOLT:RANG:AUTO?')
        return (float(res) != 0)

    @v_autorange.setter
    def v_autorange(self, on):
        self.budget.set_slack(self)
        if on:
            self.inst.write(':SENS:VOLT:RANG:AUTO ON')
        else:
            self.inst.write(':SENS:VOLT:RANG:AUTO OFF')

    @property
    def i_autorange(self):
        """Autorange current measurement on or off."""
        self.budget.set_slack(self)
        res = self.inst.query(':SENS:CURR:RANG:AUTO?')
        return (float(res) != 0)

    @i_autorange.setter
    def i_autorange(self, on):
        self.budget.set_slack(self)
        if on:
            self.inst.write(':SENS:CURR:RANG:AUTO ON')
        else:
            self.inst.write(':SENS:CURR:RANG:AUTO OFF')

    @property
    def vac_autorange(self):
        """Autorange AC voltage measurement on or off."""
        self.budget.set_slack(self)
        res = self.inst.query(':SENS:VOLT:AC:RANG:AUTO?')
        return (float(res) != 0)

    @vac_autorange.setter
    def vac_autorange(self, on):
        self.budget.set_slack(self)
        if on:
            self.inst.write(':SENS:VOLT:AC:RANG:AUTO ON')
        else:
            self.inst.write(':SENS:VOLT:AC:RANG:AUTO OFF')

    @property
    def iac_autorange(self):
        """Autorange AC current measurement on or off."""
        self.budget.set_slack(self)
        res = self.inst.query(':SENS:CURR:AC:RANG:AUTO?')
        return (float(res) != 0)

    @iac_autorange.setter
    def iac_autorange(self, on):
        self.budget.set_slack(self)
        if on:
            self.inst.write(':SENS:CURR:AC:RANG:AUTO ON')
        else:
            self.inst.write(':SENS:CURR:AC:RANG:AUTO OFF')

    @property
    def r_autorange(self):
        """Autorange resistance measurement on or off."""
        self.budget.set_slack(self)
        res = self.inst.query(':SENS:RES:RANG:AUTO?')
        return (float(res) != 0)

    @r_autorange.setter
    def r_autorange(self, on):
        self.budget.set_slack(self)
        if on:
            self.inst.write(':SENS:RES:RANG:AUTO ON')
        else:
            self.inst.write(':SENS:RES:RANG:AUTO OFF')

    @property
    def fr_autorange(self):
        """Autorange 4-wire resistance measurement on or off."""
        self.budget.set_slack(self)
        res = self.inst.query(':SENS:FRES:RANG:AUTO?')
        return (float(res) != 0)

    @fr_autorange.setter
    def fr_autorange(self, on):
        self.budget.set_slack(self)
        if on:
            self.inst.write(':SENS:FRES:RANG:AUTO ON')
        else:
            self.inst.write(':SENS:FRES:RANG:AUTO OFF')

    @property
    def v_range(self):
        """Set the voltage measurement range."""
        self.budget.set_slack(self)
        val = self.inst.query(':SENS:VOLT:RANG?')
        return float(val)

    @v_range.setter
    def v_range(self, vmax):            # vmax in V
        self._v_range = vmax
        self.budget.set_slack(self)
        self.inst.write(':SENS:VOLT:RANG {}'.format(vmax))

    @property
    def i_range(self):
        """Set the current measurement range."""
        self.budget.set_slack(self)
        val = self.inst.query(':SENS:CURR:RANG?')
        return float(val)

    @i_range.setter
    def i_range(self, imax):            # imax in I
        self._i_range = imax
        self.budget.set_slack(self)
        self.inst.write(':SENS:CURR:RANG {}'.format(imax))

    @property
    def vac_range(self):
        """Set the AC voltage measurement range."""
        self.budget.set_slack(self)
        val = self.inst.query(':SENS:VOLT:AC:RANG?')
        return float(val)

    @vac_range.setter
    def vac_range(self, vmax):            # vmax in V
        self._vac_range = vmax
        self.budget.set_slack(self)
        self.inst.write(':SENS:VOLT:AC:RANG {}'.format(vmax))

    @property
    def iac_range(self):
        """Set the AC current measurement range."""
        self.budget.set_slack(self)
        val = self.inst.query(':SENS:CURR:AC:RANG?')
        return float(val)

    @iac_range.setter
    def iac_range(self, imax):            # imax in A
        self._iac_range = imax
        self.budget.set_slack(self)
        self.inst.write(':SENS:CURR:AC:RANG {}'.format(imax))

    @property
    def r_range(self):
        """Set the resistance measurement range."""
        self.budget.set_slack(self)
        val = self.inst.query(':SENS:RES:RANG?')
        return float(val)

    @r_range.setter
    def r_range(self, rmax):            # rmax in Ohms
        self._r_range = rmax
        self.budget.set_slack(self)
        self.inst.write(':SENS:RES:RANG {}'.format(rmax))

    @property
    def fr_range(self):
        """Set voltage 4-wire resistance range."""
        self.budget.set_slack(self)
        val = self.inst.query(':SENS:FRES:RANG?')
        return float(val)

    @fr_range.setter
    def fr_range(self, rmax):            # rmax in Ohms
        self._fr_range = rmax
        self.budget.set_slack(self)
        self.inst.write(':SENS:FRES:RANG {}'.format(rmax))

    @property
    def voltage(self):
        """Get voltage."""
        self.budget.set_slack(self)
        self.inst.write(':SENS:FUNC "VOLT"')
        value = self.inst.query(':READ?')
        logger.measure("{!r} voltage == {}".format(self.instName, float(value)))
        return float(value)

    @property
    def current(self):
        """Get current."""
        self.budget.set_slack(self)
        self.inst.write(':SENS:FUNC "CURR"')
        value = self.inst.query(':READ?')
        logger.measure("{!r} current == {}".format(self.instName, float(value)))
        return float(value)

    @property
    def ac_voltage(self):
        """Get AC voltage."""
        self.budget.set_slack(self)
        self.inst.write(':SENS:FUNC "VOLT:AC"')
        value = self.inst.query(':READ?')
        logger.measure("{!r} ac_voltage == {}".format(self.instName, float(value)))
        return float(value)

    @property
    def ac_current(self):
        """Get AC current."""
        self.budget.set_slack(self)
        self.inst.write(':SENS:FUNC "CURR:AC"')
        value = self.inst.query(':READ?')
        logger.measure("{!r} ac_current == {}".format(self.instName, float(value)))
        return float(value)

    @property
    def resistance(self):
        """Get resistance."""
        self.budget.set_slack(self)
        self.inst.write(':SENS:FUNC "RES"')
        value = self.inst.query(':READ?')
        logger.measure("{!r} resistance == {}".format(self.instName, float(value)))
        return float(value)

    @property
    def fresistance(self):
        """Get 4-wire resistance."""
        self.budget.set_slack(self)
        self.inst.write(':SENS:FUNC "FRES"')
        value = self.inst.query(':READ?')
        logger.measure("{!r} fresistance == {}".format(self.instName, float(value)))
        return float(value)

    @property
    def period(self):
        """Get period, set (threshold,aperture)."""
        self.budget.set_slack(self, self.per_aperture)
        self.inst.write(':SENS:FUNC "PER"')
        value = self.inst.query(':READ?')
        logger.measure("{!r} period == {}".format(self.instName, float(value)))
        self.budget.set_slack(self)
        return float(value)

    @period.setter
    def period(self, threshold_aperture):
        self.per_threshold, self.per_aperture = threshold_aperture
        self.budget.set_slack(self)
        self.inst.write(':SENS:PER:THR:VOLT:RANG {}'.format(self.per_threshold))
        self.inst.write(':SENS:PER:APER {}'.format(self.per_aperture))

    @property
    def frequency(self):
        """Get frequency, set (threshold,aperture)."""
        self.budget.set_slack(self, self.freq_aperture)
        self.inst.write(':SENS:FUNC "FREQ"')
        value = self.inst.query(':READ?')
        logger.measure("{!r} frequency == {}".format(self.instName, float(value)))
        self.budget.set_slack(self)
        return float(value)

    @frequency.setter
    def frequency(self, threshold_aperture):
        self.freq_threshold, self.freq_aperture = threshold_aperture
        self.budget.set_slack(self)
        self.inst.write(':SENS:FREQ:THR:VOLT:RANG {}'.format(self.freq_threshold))
        self.inst.write(':SENS:FREQ:APER {}'.format(self.freq_aperture))

    def temporal_tuple(self, threshold, aperture):
        """Wrapper for tuple assignment to period & frequency."""
        return threshold, aperture
