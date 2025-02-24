"""Baseclass Interfaces to the TTI Power Supply Instruments.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>

"""
from enum import Enum
from pylab_ml.base_instrument import logger
from pylab_ml.base_instrument import InvalidInstrumentConnection
from pylab_ml.collate_instrument import Interface
from pylab_ml.baseclass.base_measurement import Measure
from pylab_ml.attributes import create_attributes


class TTI (create_attributes, Measure):
    """Baseclass Interface to the TTI Power Supply Instruments.

    The TTI baseclass can connect to TTI Power Supply instruments

    Methods:
        ask=inst.query(':READ?')
            write and read the answer

    """

    # create functions or proberty and call inst.write) or inst.read():
    # if state != necessary state -> switch to the necessary state
    #  proberty/function name -> inst.funcname (get,set)    , range,    call functions
    #                                                         range : None, Enum or range value
    #                                                         call functions: see help in attributes
    # in function self.write() replace $ with channel
    _properties = {
                  'current':   (('I$O?',     None),       None,      {'ga': '_tr2number(value, A, 20)'}),
                  'i_clamp':   (('I$?',      'I$ '),      None,      {'ga': '_tr2number(value, I$, 1)', 'sa': 'errmsg()'}),
                  'onoff':     ((None,       'OP$ '),     [0, 1],    None),
                  'ocp':       (('OCP$?',    'OCP$ '),    None,      {'ga': '_tr2number(value, CP$, 1)', 'sa': 'errmsg()'}),
                  'ovp':       (('OVP$?',    'OVP$ '),    None,      {'ga': '_tr2number(value, VP$, 1)', 'sa': 'errmsg()'}),
                  'sense':     ((None,       'SENSE$ '),  'Sense',   None),
                  'state':     (('*ESE?',    '*ESE '),    None,      None),
                  'voltage':   (('V$?',      'V$ '),      None,      {'ga': '_tr2number(value, V$, 1)', 'sa': 'errmsg()'}),
                  'v_range':   (('RANGE$?',  'RANGE$ '),  [0, 2],    {'ga': '_tr2number(value, R$, 11)'}),
                  }

    class Sense(Enum):
        """Enum for Sense control."""

        local = 0
        """value for sense mode = local"""
        remote = 1
        """value for sense mode = remote"""

    _eer_states = {
               1:   '   Indicates a hardware error has been encountered.',          # 1-99
               116: '   A recall of set up data has been requested but the store specified does not contain any data.',
               117: '   A recall of set up data has been requested but the store specified contains corrupted data. This indicates either a hardware fault or a temporary data corruption which can be corrected by writing data to the store again.',
               120: '   The numerical value sent with the command was too big or too small. Includes negative numbers where only positive numbers are accepted.',
               123: '   A recall/store of set up data has been requested from/to an illegal store number.',
               124: '   A range change has been requested but the current psu settings make it illegal – see manual operation instructions for details.',
               255: '   unknown error'
               }

    def __init__(self, **kwargs):
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

        Example: Initialization
           >>> instrument = TTI(addr=24)   # GPIB or USB address
           >>> instrument.init()           # connect and initialize instrument

        """
        self.is_local = False
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
        self.com._init(self)

    def setup_inst(self):
        """Start setup instrument settings, called from class instruments."""
        super().setup_inst()
        if self.inst:
            if self.interface == Interface.gpib:
                self.inst.read_termination = '\n'
                # self.inst.read_termination = '\r'
                self.inst.write_termination = '\n'
                self.inst.encoding = 'iso8859'
            else:
                self.inst.baud_rate = 19200                  # in USB-Mode: 19200
                self.inst.read_termination = '\n'            # LF (=10d)
                # self.inst.write_termination = '\r\n'       # CR (=13d), LF
                self._endstring = -1                         # string include \r as last character, to ignore this use -1 else 0
                self.inst.write_termination = '\n'
                self.inst.encoding = 'iso8859'
                # self.inst.write('\x04')                      # lock normal RS232-Mode
        self.inst.timeout = 1000
        self.createattributes(self._properties)

    def init(self, identify=False):
        """Connect to TTI instrument and initialize."""
        super().init(identify)

    def reset(self):
        """Reset and switch beep off."""
        self.budget.set_slack(self)
        self.inst.clear()
        self.inst.write('*RST')
        for ch in self.channels:                    # reset shadow-values from _properties
            self[ch]._onoff = 0
            self[ch]._local = 'local'

    def clear(self):
        """Clear error status."""
        self.budget.set_slack(self)
        self.inst.clear()

    def message(self, message=None):
        """Device has no display, message display to logger.info."""
        logger.info(message)

    @property
    def id(self):
        """Query IDN."""
        self.budget.set_slack(self)
        try:
            # value = self.inst.query('*IDN?').split(',')[1]
            value = self.inst.query('*IDN?')
            value = self.inst.read().split(',')[1]
        except Exception:
            value = ""
        if value != self.__class__.__name__:
            if value == "":
                value = "no answer"
            msg = ('{}.id: The connected Device has wrong Model-No, readed Model is: {}'.format(self.__class__.__name__, value))
            raise InvalidInstrumentConnection(msg)
        return value

    def local(self):
        """Switch back to local instrument control."""
        self.budget.set_slack(self)
        self.inst.write('LOCAL')
        self.is_local = True

    def write(self, cmd):
        """
        Write direct to instrument.

        Example: send command reset :
           >>> inst.write('*RST')
        """
        if cmd.find('$') > -1:
            cmd = cmd.replace('$', str(self.channel+1))
        self.inst.write(cmd)

    def read(self):
        """Read the instruent directly."""
        return self.inst.read()

    def errmsg(self):
        """Read Execution Error Register."""
        error = int(self.inst.query('EER?'))
        if error != 0:
            if error < 99:
                error = 1
            if error not in self._eer_states:
                error = 255
            logger.error(self._eer_states[error])

    def _tr2number(self, value):
        """Translate answer from device to float or integer.

        index depence from the function call, see _properties
        """
        value = value.split(',')
        index = int(value[2]) % 10
        convert = round(int(value[2]) / 10)                # 0= float, 1= integer, 2 = A
        verify_target = value[1][1:].replace('$', str(self.channel+1))
        verify_answ = value[0].split(' ')[0]
        result = value[0].split(' ')[index]
        if convert == 0:
            result = float(result)
        elif convert == 1:
            result = int(result)
        elif convert == 2:
            verify_answ = verify_answ[self._endstring-1]
            result = float(result[:self._endstring-1])
        if verify_answ != verify_target:
            logger.error('Unexpected Answer from Device! (got:{})'.format)
        return result

    # ----------------------------------------------------------
    # doc strings for _properties, propertie themselve will create form dictionary _properties
    @property
    def current(self):
        """Measure DC current of actual Channel."""

    @property
    def i_clamp(self):
        """Set the current clamping (A) of actual Channel."""

    @property
    def onoff(self):
        """
        Get/Set the Output-State of actual Channel.

        |  0 = Output off
        |  1 = Output on
        """

    @property
    def ocp(self):
        """Get/Set over current protection trip point at x Amps."""

    @property
    def ovp(self):
        """Get/Set over voltage protection trip point at x Volts."""

    @property
    def sense(self):
        """
        Get/Set sense.

        |  'local'  = Local sensing (2-Wire)
        |  'remote' = Remote sensing (4-Wire)
        """

    @property
    def state(self):
        """
        Get/Set Standard Event Status Enable Register.

        see QL355T Instruction Manual for more details
        """

    @property
    def voltage(self):
        """Get/Set voltage."""

    # end doc strings for _properties
    # ----------------------------------------------------------
