"""Baseclass Interfaces to the Keithley SMU Instruments.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>

"""
from pylab_ml.base_instrument import logger
from pylab_ml.collate_instrument import Interface
from pylab_ml.baseclass.base_measurement import Measure


class Keithley (Measure):
    """Baseclass Interface to the Keithley SMU Instruments.

    The Keithley baseclass can connect to Keithley SMU instruments

    Methods:
        inst.write('*RST')
            write direct to instrument
        ask=inst.query(':READ?')
            write and read the answer

    """

    interchoices = [Interface.usbserial, Interface.gpib]

    def __init__(self, **kwargs):
        """Connect and initialize.

        Args:
           addr (int):
              interface address

           interface (Interface):
              gpib, usbserial

           backend (str):
              visa backend is either '@ivi' (or '@ni') for NI-Library or
              '@py' for pure python pyvisa-py backend.
              On default it uses '@ivi' (or '@ni') on win32 and '@py' on
              other platforms.

        Example: Initialization
           >>> instrument = Keithley(addr=24)   # GPIB or USB address
           >>> instrument.init()                # connect and initialize instrument

        """
        self.is_local = False
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
        self.com._init(self)

    def init(self, identify=False):
        """Connect to Keithley instrument and initialize."""
        super().init(identify)

    def reset(self):
        """Reset and switch beep off."""
        self.budget.set_slack(self)
        self.inst.clear()
        self.inst.write(':SYST:BEEP:STAT 0')
        self.inst.write('*RST')
        self.inst.write(':SYST:BEEP:STAT 0')

    def clear(self):
        """Clear error status."""
        self.budget.set_slack(self)
        self.inst.clear()

    def error_list(self):
        """List of instrument errors."""
        self.budget.set_slack(self)
        errormsgs = self.inst.query(':SYST:ERR:ALL?')
        errors = errormsgs.split(",")[1::2]
        codes = errormsgs.split(",")[0::2]
        errorlist = []
        for c, m in zip(codes, errors):
            print("{} : {}".format(c, m))
            errorlist.append((c, m))
        return errorlist

    def message(self, message=None):
        """Message display.

        instrument message ("string") or ()
        """
        self.budget.set_slack(self)
        if message is None:
            self.inst.write(':DISP:TEXT:STAT 0')
        else:
            linlen = self.msg_row_col[0] * self.msg_row_col[1]
            msg = message[:linlen]
            self.inst.write(':DISP:TEXT:DATA \"{message}\"'.format(message=msg))
            self.inst.write(':DISP:TEXT:STAT 1')

    @property
    def id(self):
        """Query IDN."""
        self.budget.set_slack(self)
        try:
            value = self.inst.query('*IDN?')
        except Exception:
            value = ""
        return value.replace('\r', '').replace('\n', '')

    def local(self):
        """Switch back to local instrument control."""
        self.budget.set_slack(self)
        self.inst.write(':SYSTEM:LOC')
        self.is_local = True

    def com_recover(self, fix=False):
        """Detect & attempt to recover out of step communication (maybe after timeout).

        Can lose coherency between read request and data, usually because of Timeout
        this routine can diagnose such loss of coherency and attempt to fix it, when fix=True
        """
        self.budget.set_slack(self)
        ires = None
        for i in range(1, 10):
            self.inst.write(':DISP:TEXT:DATA \"{}\"'.format(i))
            res = self.inst.query(':DISP:TEXT:DATA?')
            try:
                res = "".join([r for r in res if not r in '"'])
                ires = int(float(res))
                print("For {} got {}".format(i, ires))
                if i in [5, 6, 7] and fix:
                    diff = i - ires
                    if diff > 0:
                        print("See offset {}".format(diff))
                        for j in range(diff):
                            consume = self.inst.read()
                            print("Consumed '{}'".format(consume))
            except Exception:
                print("For {} got: {}".format(i, res))
        return (ires == i)
