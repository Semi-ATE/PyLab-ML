from pylab_ml.base_instrument import logger
from pylab_ml.collate_instrument import Interface
from pylab_ml.example.base_example import Example


class EG_Generic (Example):
    """Interface to the Keithley SMU Instruments.

    The Keithley baseclass can connect to Keithley SMU instruments

    Initialization arguments:
        addr (int):
                        interface address

        interface (dev_interface.Instrument):
                        gpib, usbserial

        backend (str):
                        visa backend is either '@ni' for NI-Library or
                        '@py' for pure python pyvisa-py backend.
                        On default it uses '@ni' on win32 and '@py' on
                        other platforms.

    Example: Initialization
        >>> instrument = Keithley(addr=24)   # GPIB or USB address
        >>> instrument.init()                # connect and initialize instrument

    Methods:
        init()
            connect and initialize
        local()
            switch back to instrument control
        reset()
            reset
        identify()
            instrument message, reflect address & interface
        message("")
            instrument message ("string") or ()
        error_list()
            list of instrument errors
        close()
            terminate interface
        com_recover(bool)
            detect & attempt to recover out of step communication (maybe after timeout)
        inst.write('*RST')
            write direct to instrument
        ask=inst.query(':READ?')
            write and read the answer

    Properties:
        id          get IDN string
    """

    interchoices = [Interface.generic]

    def __init__(self, **kwargs):
        if not hasattr(self, 'interchoices'):
            self.interchoices = [Interface.generic]
        self.is_local = False
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
        self.com._init(self)

    def create_session(self):
        """Create an Instrument Session for Instrument.inst, example Keithley2000 or Keithley2400 on Linux usbserial."""
        print("Create an Instrument Session for Instrument.inst, example Keithley2000 or Keithley2400 on Linux usbserial")

        import pyvisa

        rm = pyvisa.ResourceManager(self.backend)
        logger.debug("Generic instrument example resource manager {}".format(rm))
        resourceid = 'ASRL/dev/ttyUSB{!r}::INSTR'.format(self.addr)
        logger.debug("Generic instrument example resource manager {}".format(resourceid))
        inst = rm.open_resource(resourceid)
        logger.debug("Generic instrument example instrument interface inst {}".format(inst))
        return (inst)

    def init(self, identify=False):
        """Connect to Keithley instrument and initialize."""
        super().init(identify)

    def reset(self):
        """Reset and switch beep off"""
        self.inst.clear()
        self.inst.write(':SYST:BEEP:STAT 0')
        self.inst.write('*RST')
        self.inst.write(':SYST:BEEP:STAT 0')

    def clear(self):
        """Clear error status"""
        self.inst.clear()

    def error_list(self):
        """list of outstanding errors"""
        errormsgs = self.inst.query(':SYST:ERR:ALL?')
        errors = errormsgs.split(",")[1::2]
        codes = errormsgs.split(",")[0::2]
        errorlist = []
        for c, m in zip(codes, errors):
            print("{} : {}".format(c, m))
            errorlist.append((c, m))
        return errorlist

    def message(self, message=None):
        """Message display."""
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
        try:
            value = self.inst.query('*IDN?')
        except Exception:
            value = ""
        return value.replace('\r', '').replace('\n', '')

    def local(self):
        """Switch back to local instrument control"""
        self.inst.write(':SYSTEM:LOC')
        self.is_local = True

    def com_recover(self, fix=False):
        """can lose coherency between read request and data, usually because of Timeout
        this routine can diagnose such loss of coherency and attempt to fix it, when fix=True"""
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
