"""Interface to the Application Board HAL-APB V1.x.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>

Bugs:
      -

toDo:
   check:
      | vout at real analog out
      | ack  return with last acknowledge pulse
      | pwm   read PWM-Period and Pulse width     only firmware > 2.32, if >2.32 only in mode 9
      | ovcp ??  nur in matlab vorhanden, in dodu aber nicht?  -> emanuell fragen
      | OCPulseLength

"""

from time import sleep
import pyvisa
from pylab_ml.base_instrument import logger
from pylab_ml.collate_instrument import Interface
from pylab_ml.boards.micronas.communication.base_board import BaseBoard
from pylab_ml.attributes import create_attributes


class APBBoardBiPhase:
    """Sub-class, Interface to BiPhase protocol of HAL-APB Device, called from :class:`HALAPBBoard`.

    Example: Read/Write register

        >>> interface = HALAPBBoard(addr=10)
        >>> interface.init()

        >>> interface.biph.writebase(0)
        >>> interface.biph.writereg(0x20, 0b1101)
        >>> interface.biph.writereg(0x20)

    """

    def __init__(self, board):
        """Initialize the bihase protocoll."""
        self.board = board
        self.pcmd = 'xx'            # prefix command
        self.mcmd = ''              # middle command
        self.delay = 0.1
        """delay after each write (default=100ms)"""
        self.crctyp = None
        self.addr_bits = 5
        self.data_bits = 8

    def __repr__(self):
        args = []
        args.append('{!r}'.format(self.board))
        return '{classname}({args})'.format(
            classname=self.__class__.__name__,
            args=', '.join(args),
        )

    def readreg(self, addr):
        """Read register.

        Args:
            addr (TYPE): address.

        Returns:
            value as hexcode

        """
        addr_bits = self.addr_bits
        addr &= 2**addr_bits - 1
        cmd = '{}r{}{:02x}\r'.format(self.pcmd, self.mcmd, addr)
        value = self.board.query(cmd)
        if type(value) is str:
            try:
                hexvalue = int(value[:-1], 16)
                self.board.ReadErrorCount = 0
#                if calc_crc(addr, hexvalue)!=int(value[-1]):self.board.geterror(32)
            except ValueError:
                hexvalue = -1
        elif type(value) is int and value == -1:
            logger.error('Error, {} could not read adr=0x{:04x}'.format(self.board.instName, addr))
            hexvalue = value
            self.board.ReadErrorCount += 1
        else:
            hexvalue = value
        return hexvalue

    def writereg(self, addr, data):
        """Write data to register addr.

        Parameters
        ----------
        addr : int,hex
            address.
        data : int,hex
            value.

        Returns
        -------
        None.

        """
        addr_bits = self.addr_bits
        addr &= 2**addr_bits - 1
        data &= 2**self.data_bits - 1
        cmd = '{}w{}{:02x}{:0{width}x}{:0x}\r'.format(self.pcmd, self.mcmd, addr, data,
                                                      self.board.calc_crc(addr, data, addr_bits, typ=self.crctyp),
                                                      width=self.data_bits//4)
        result = self.board.query(cmd)
        if type(result) is int and result == -1:
            logger.error('{} could not write adr=0x{:04x} with data=0x{:04x}'.format(self.board.instName, addr, data))

    def writebase(self, bank):
        """Set register bank."""
        if self.pcmd == 'xx':
            cmd = '{}sb00{:04x}{:0x}\r'.format(self.pcmd, bank, self.board.calc_crc(0, bank, cmd=3, typ=self.crctyp))
        elif self.pcmd == 'px':
            cmd = '{}sb{:04x}{:0x}\r'.format(self.pcmd, bank, self.board.calc_crc(0, bank, cmd=3, typ=self.crctyp))
        result = self.board.query(cmd)
        if type(result) is int and result == -1:
            logger.error('{} could not writebase adr=0x{:04x}'.format(self.board.instName, bank))

    def reset(self):
        """Protocoll has no reset."""
        logger.warning('{}.biph.reset not implemented -> do nothing'.format(self.board.instName))

    @property
    def delay(self):
        """Set/get delay time."""
        sleep(self.tdelay)
        return self.tdelay

    @delay.setter
    def delay(self, value):
        self.tdelay = value


class HALAPBBoard(create_attributes, BaseBoard):
    """Main Class, Interface to the HAL-APB Communication Board.

    .. image:: ../static/halapb.jpg

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    This protocol board implements the communication with the sensor device
    under test. The communication is realized via one of the following
    serial protocols:

    +---------------------------+----------------------------------+--------------------------------------+
    | 8   Lin-mode              | HAL 2810                         |  not implemented!                    |
    +---------------------------+----------------------------------+--------------------------------------+
    | 9   Biphase via DIO-Pin   | HAL 283x/50                      |  implemented, but not checked!       |
    +---------------------------+----------------------------------+--------------------------------------+
    | A   Biphase via Vsup Pin  | HAL 1820, 24xy, 3625, 3675, 38xy |                                      |
    +---------------------------+----------------------------------+--------------------------------------+
    | C   Biphase via Out       | HAL       24xy, 3625, 3675, 38xy |                                      |
    +---------------------------+----------------------------------+--------------------------------------+
    see Manual 'Application Board HAL-APB V1.x'

    Attributes:
       biph :
          interface object for :class:`APBBoardBiPhase` BiPhase protocol.

    """

    interchoices = [Interface.usbserial]
    _protocol_typ = 'biph'      # necessary for base_board

    _ERROR_CODES = {
            -1:   'no read answer',
            '0':  'ok',
            '1':  'acknowledge error (Errorcode=1)',
            '2':  'ok',  # 2’nd Acknowledge error (Errorcode=2)',   # nd Acknolage is not an Error is an Bug in APB-Firmware
            '3':  'invalid command for selected Mode (Errorcode=3)',
            '4':  'PID in running table cannot be modified (LIN) (Errorcode=4)',
            '5':  'LIN communication Error (Errorcode=5)',
            '6':  'LIN interface connection Error (Errorcode=6)',
            '7':  'no PWM (at PWM Duty Cycle read command) (Errorcode=7)',
            '8':  'Errorcode=8 no Definition exist in this Class.',
            '9':  'Errorcode=9 no Definition exist in this Class.',
            'A':  'Errorcode=10 no Definition exist in this Class.',
            'B':  'Errorcode=11 no Definition exist in this Class.',
            'C':  'Errorcode=12 no Definition exist in this Class.',
            'D':  'data read error (Errorcode=13)',
            'E':  'invalid command parameter (Errorcode=14)',
            'F':  'invalid command (Errorcode=15)',
            '20': 'read crc error (Errorcode=32)',
            '21': 'command respone frame error',
            }
    _VSUP = {5.0:   (0, 0, 0),       # ftvdp, ftvdh, ftvdl
             6.0:   (0, 0, 1),
             7.5:   (0, 1, 0),
             8.0:   (0, 1, 1),
             12.0:  (1, 0, 0),       # LIN MODE (8)
             12.5:  (1, 0, 1),       # "
             14.5:  (1, 1, 0),       # "
             15.0:  (1, 1, 1)        # "
             }

    # create functions or proberty and wrap it to the inst.funcname:
    # if state != necessary state -> switch to the necessary state
    #  proberty/function name -> inst.funcname (get,set)    , range,    call functions
    #                                                         range : None, Enum or range value
    #                                                         call functions: see help in attributes
    _properties = {
                  'ack':      (('?ack',  None),     None,         {'ga': '_hex2dec(value)'}),
                  'bitTime':  (('?bt',  'sbt'),     [10, 3400],   {'ga': '_hex2dec(value)', 'sac': '_dec2hex(value)', 'sa': '_readresult(0)'}),
                  'channel':  ((None,   'ftses'),   [1, 2],       {'sa': '_wait(0.1)'}),
                  'force':    ((None,   'ftsme'),   [0, 1],       {'sa': '_wait(0.1)'}),
                  'pmms':     (('pmms',  None),     None,         None),
                  'pullup':   ((None,   'ftpon'),   [0, 1],       {'sa': '_wait(0.1)'}),
                  'pwmf':     (('pr0',  None),      None,         {'ga': '_pwm(value)'}),
                  'pwmr':     (('pr1',  None),      None,         {'ga': '_pwm(value)'}),
                  'onoff':    ((None,   'vho'),     [0, 1],       {'sa': '_wait(0.1)'}),
                  'ovcp':     ((None,   'ovcp'),    [0, 1],       {'sa': '_wait(0.1)'}),
                  'vout':     (('ftana2', None),    None,         {'ga': '_vout(value)'}),
                  }

    def __init__(self, addr='0403:6001', backend=None, identify=False, instName=None):
        """Initialize.

        Args:
           addr (int):
               | serial comport address
               | Defaults to '0403:6001', this is the vid:pid from the UART-to/USB chip, than automatically found the associated comport
           backend (str):
               Defaults to None. Not necessary, automatically found the correct backend
           identify (bool, optional):
               Defaults to False.
           instName (string):
               Instance Name from top.

        Example: Initialization
           >>> interface = HALAPBBoard(5, instName='interface')
           >>> interface = HALAPBBoard(instName='interface')

        Example: Get version of Board-Firmware
           >>> interface.version
           '3.0.3'

        Example: Configuration
           >>> interface.onoff = 0        # switch supply voltage off
           >>> interface.vsup = 5.0         # configure voltage levels
           >>> interface.onoff = 1          # switch supply voltage on
           >>> interface.clock_MHz(0.1)     # set clock frequency

        Example: Read/Write register via BiPhase protocol
           >>> interface.biph.writebase(0)          # select register bank
           >>> interface.biph.writereg(0x20, 0b1101)
           >>> interface.biph.writereg(0x20)
           13

        Example: low level commands
           >>> interface.query('?v')
           '3.0.3'
           >>> interface.write('?v')
           >>> interface.read()
           '3.0.3'

        Returns:
            None.

        """
        create_attributes.__init__(self)
        kwargs = {"addr": addr, "interface": None, "backend": None, "identify": identify, "instName": instName}
        BaseBoard.__init__(self, **kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))

    def setup_inst(self):
        """Set setup instrument settings."""
        self.biph = APBBoardBiPhase(board=self)
        self.clockMhz = 1.0
        self.delay
        self.errortext = 'ok'
        """Get last access-code"""
        if not hasattr(self, '_is_initialized'):
            self.createattributes(self._properties)
        super().setup_inst()
        if self.inst is not None:
            self.inst.baud_rate = 38400
            self.inst.parity = pyvisa.constants.Parity.even
            self.inst.timeout = 2000
            self.inst.read_termination = '\r\n'
            self.inst.write_termination = '\n'
        self.protocol_typ = self._protocol_typ
        self.has_visa = self.com.has_visa
        self._is_initialized = True

    # ----------------------------------------------------------
    # doc strings for _properties, propertie themselve will create form dictionary _properties
    @property
    def ack(self):
        """Return the width of last acknowledge pulse."""

    @property
    def bitTime(self):
        """Set/Get Bit time (in us) from 0x000A- 0x0D48 (10us-3.4ms)."""

    @property
    def channel(self):
        """Set/get select I/O channel.

        | 1= HAL 1.
        | 2= Hall2.
        | get read only shadow value.
        """

    @property
    def force(self):
        """Force the output stage to value .

        | 1: force output voltage to high state
        | 0: release output
        | get, read only shadow value
        """

    @property
    def pmns(self):
        """?."""

    @property
    def pmf(self):
        """Get Period/Pulstime/Duty Cycle from PWM.

        Trigger on falling edge, time in ms, Duty Cyle in %
        """

    @property
    def pmnr(self):
        """Get Period/Pulstime/Duty Cycle from PWM.

        Trigger on rising edge, time in ms, Duty Cyle in %
        """

    @property
    def pullup(self):
        """Set pullup.

        | on=1
        | off=0
        | get read only shadow value
        """

    @property
    def onoff(self):
        """Set/get supply voltage.

        | on = 1
        | off = 0
        | get, read only shadow value
        """

    # end doc strings for _properties
    # ----------------------------------------------------------
    def read(self):
        """Return answer from HAP-APB as string."""
        value = super().read()
        value = self._extractvalue(value)
        return value

    def _extractvalue(self, value):
        """Remove ERROR-code from value."""
        error = ''
        if type(value) is str and value.find(':') > 0:                 # is string format =='0:value' ?
            error = value[:value.find(':')]
            value = value[2:]
        else:
            try:
                error = int(value)
            except Exception:
                error = -2
        if error in self._ERROR_CODES:
            self.errortext = self._ERROR_CODES[error]
        else:
            self.errortext = 'unknown Error {}'.format(value)
        if self.errortext != 'ok':
            msg = f'{self.instName}: {self.errortext},   last command was {self.lastcmd}'
            if error != -1 and not self.quiet:
                logger.error(msg)
                self.ReadErrorCount += 1
            else:
                logger.debug(f'ERROR-quiet: {msg}')
            return value
        self.ReadErrorCount = 0
        return value

    def on(self):
        """Switch supply voltage on."""
        self.onoff = 1
        logger.debug('{}.on()'.format(self.instName))

    def off(self):
        """Switch supply voltage off."""
        self.onoff = 0
        logger.debug('{}.off()'.format(self.instName))

    @property
    def mode(self):
        """Set/get available board modes.

        values are:
           | '9' = Biphase via DIO-Pin.
           | 'A' = Biphase via Vsup Pin.
           | 'C' = Biphase via Out.
        """
        self.write('?m')
        result = self.readbuffer()
        logger.debug('{}.mode == {}'.format(self.instName, result))
        logger.info(f' mode == {self._mode}')
        return result

    @mode.setter
    def mode(self, value):
        logger.debug('{}.mode := {}'.format(self.instName, value))
        self.write('sm{}'.format(value))
        self._readresult(int(value, 16))
        if value == 'A' or value == 'C':
            self.biph.pcmd = 'xx'
            self.biph.mcmd = ''
        elif value == '9':
            self.biph.pcmd = 'px'
            self.biph.mcmd = 'b'
        self._mode = value

    def _dec2hex(self, value):
        return '{:04x}'.format(int(value))

    def _hex2dec(self, value):
        return (int(value, 16))

    def _pwm(self, value):
        """Calculate something from value.

        | Period/Pulstime/Duty Cycle
        | Period and Pulstime in ms, Duty Cyle in %

        """
        width = (int(value, 16) & 0xfffff) / 10000
        period = ((int(value, 16) & 0xfffff00000) >> 20) / 10000
        duty = 0
        if period != 0:
            duty = width / period * 100
        return (period, width, duty)

    def _vout(self, value):
        if self._channel != 1:
            logger.error('{}.vout measure not possible, only at channel=1'.format(self.instName))
            return 0
        return int(value, 16) * 5/1024

    def config_get(self):
        """Get info about board settings."""
        version = self.version
        channel = self.channel
        bitTime = self.bitTime
        pullup = self.pullup
        force = self.force
        vsup = self.vsup
        return version, channel, bitTime,  pullup, force, vsup

    @property
    def vsup(self):
        """Get/set supply voltage.

        Parameters
        ----------
        | 5.0, 6.0, 7.5, 8.0 :  Mode 9,A,C
        | 12.0, 12.5, 14.5, 15.0 :  LIN MODE (8)

        """
        value = self.query('ftana1')
        if type(value) is str:
            value = int(value, 16)*15/1024
        else:
            value = -1
        logger.measure('{}.vsup== {}'.format(self.instName, value))
        return value

    @vsup.setter
    def vsup(self, value):
        """Set ftvdp, ftvdh, ftvdl) depend from value."""
        if value in self._VSUP:
            ftvdp, ftvdh, ftvdl = self._VSUP[value]
            self.query('ftvdp{}'.format(ftvdp))
            self.query('ftvdh{}'.format(ftvdh))
            self.query('ftvdp{}'.format(ftvdl))
        else:
            msg = '{}.vsup not possible with {}\n'.format(self.instName, value)
            msg += '  allowed values are:'
            for values in self._VSUP:
                msg += '{}/ '.format(values)
            msg += 'Volt'
            logger.error(msg)
        logger.measure('{}.vsup:={}'.format(self.instName, value))

    def _readresult(self, targetvalue):
        result = self.read()
        if result == '-1':
            return 'ERROR'
        if targetvalue is None:
            targetvalue = self.attrLastvalue
        elif isinstance(targetvalue, str):
            targetvalue = int(targetvalue, 16)
        elif int(result, 16) != targetvalue:
            logger.error('{} = {} , should be {} '.format(self._ERROR_CODES['21'], result, targetvalue))

    def _wait(self, value):
        sleep(float(value))
        return self._readresult(None)

    @property
    def helpboard(self):
        """Get information about available modes."""
        logger.info(self.mode)

    def reset(self):
        """Set some values to default"""
        super().reset()
        version = self.version
        if version == '-1':
            self.errortext = 'no connection'
            logger.error(f"{self.instName}: {self.errortext} with addr={self.addr}")
            return -1
        logger.measure(f"{self.instName}.Version: {version}")
        self.onoff = 0
        self.flush()
        self.channel = 1
        self.bitTime = 1000
        # self.vsup = 5.0       # use default values from the board!!
        self.pullup = 0
        self.force = 0
        return 0


if __name__ == '__main__':
    from pylab_ml.base_instrument import logsetup
    # from pylab_ml.base_instrument import createDummyifInvalid
    logsetup()

    def check(value, cmpvalue, msg):
        if value != cmpvalue:
            logger.error('{} = {}, target = {}'.format(msg, value, cmpvalue))

    # createDummyifInvalid(True)
    interface = HALAPBBoard(instName='interface')
    interface.reset()
    interface.biph.addr_bits = 5
    interface.biph.data_bits = 16
    interface.pullup = 1
    interface.mode = 'A'

    logger.info(interface.id)
    logger.info(interface.mode)

    interface.bitTime = 340
    check(interface.bitTime, 340, 'bitTime not correct')

    interface.channel = 0
    interface.channel = 1

    interface.force = 1
    check(interface.force, 1, 'force not correct')
    interface.force = 0

    interface.pullup = 1
    interface.pullup
    interface.pullup = 0

    interface.vsup = 5.2
    interface.vsup = 5.0

    interface.onoff = 1
    interface.off()
    interface.on()
    interface.onoff
    interface.vsup
    interface.vout

    interface.ack
    logger.info('PWM on falling edge == {}'.format(interface.pwmf))
    logger.info('PWM on raising edge == {}'.format(interface.pwmr))

    interface.pmms

    interface.close()
