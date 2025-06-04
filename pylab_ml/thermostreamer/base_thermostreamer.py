"""
Basic Thermostreamer class.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>
"""

from pylab_ml.base_instrument import logger
from pylab_ml.collate_instrument import Interface
from pylab_ml.base_instrument import Instrument


class Base_Thermostreamer(Instrument):
    """Interface to the thermostreamer.

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    The thermostreamer baseclass can connect to thermostreamer

    Initialization arguments:
        addr (int):
                        interface address

        interface (Interface):
                        gpib, usbserial

        backend (str):
                        visa backend is either '@ni' for NI-Library or
                        '@py' for pure python pyvisa-py backend.
                        On default it uses '@ni' on win32 and '@py' on
                        other platforms.

    Example: Initialization
        >>> instrument = Base_Thermostreamer(addr=24)   # GPIB or USB address

    """

    interchoices = [Interface.usbserial, Interface.gpib]

    def __init__(self, **kwargs):
        """Initialise."""
        self.is_local = False
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
        self.com._init(self)
        if self.inst is None:
            kwargs['message'] = 'Use Dummy Thermostreamer instead:'
            self.inst = Dummy(self, **kwargs)
            self.setup_inst()

    def write(self, msg):
        """Write the instance with msg."""
        self.inst.write(msg)

    def read(self):
        """Read the instance."""
        return self.inst.read()

    def _get_ack(self):
        return                                    # MPI_TA5000 sendet kein Acknowledge!!
        ret = self.inst.read()
        if ret != '@@@OK':
            raise ValueError("No 'OK' in return value after reset: {}".format(ret))

    def reset(self):
        """Reset the instrument."""
        self.budget.set_slack(self)
        self.inst.write('*RST')
        self._get_ack()
        self.local()
        self._setpoint = None

    def clear(self):
        """Clear error status."""
        self.budget.set_slack(self)
        self.inst.clear()

    def close(self):
        """Close connection to Thermostreamer."""
        if self.inst is not None:
            self.flow = 0
            self.inst.flush(2)
            logger.info('{} close interface to {}'.format(self.instName, self.id))
        super().close()

    def error_list(self):
        """List of outstanding errors."""
        self.budget.set_slack(self)
        errormsgs = self.inst.query(':SYST:ERR:ALL?')
        errors = errormsgs.split(",")[1::2]
        codes = errormsgs.split(",")[0::2]
        errorlist = []
        for c, m in zip(codes, errors):
            logger.info("{} : {}".format(c, m))
            errorlist.append((c, m))
        return errorlist

    def message(self, message=None):
        """Message display to Python console."""
        if message is not None:
            logger.info(message)

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
        self.inst.write('%GL')           # go to local button
        self._get_ack()
        self.is_local = True


class Dummy(object):
    """Dummy object  for the Thermostreamer.

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    Usable if you have no real Thermostreamer as instance

    """

    def __init__(self, parent, **kwargs):
        """Initialise."""
        # kwargs = {"addr": addr, "interface": interface, "backend": backend, "identify": identify, "instName": instName}
        if 'message' in kwargs:
            logger.error(kwargs['message'])
        else:
            logger.warning('Use Dummy Thermostreamer')
        self._lastcmd = ''
        self.flow = 0
        self.head = 0

    def query(self, cmd):
        if cmd == '*IDN?':
            return f'{self.__class__}\r'
        cmd = cmd[:cmd.find('?')]
        try:
            value = super(__class__, self).__getattribute__(cmd)
            try:
                value = int(value)
            except Exception:
                pass
            logger.debug(f'Dummy Thermostreamer query {cmd} == {value}')
        except Exception:
            value = 0xdeadbeef
            logger.debug(f'Dummy Thermostreamer query {cmd} == {hex(value)}')
        return value

    def write(self, cmd):
        self._lastcmd = cmd[:cmd.find('?')] if cmd.find('?') > -1 else ''
        cmd = cmd.split(' ')
        if len(cmd) > 1:
            object.__setattr__(self, cmd[0], cmd[1])
        logger.debug(f'Dummy Thermostreamer write {cmd}')

    def read(self):
        # value = self.NaN
        value = 0xdeadbeef
        if self._lastcmd in ('SOAK', 'FLWM', 'DSNS'):
            value = 1
        elif self._lastcmd in ('FLOW', 'HEAD'):
            value = 0
        logger.debug('Dummy Thermostreamer read 0x{hex(value)}')
        return value

    def flush(self, arg=None):
        pass
