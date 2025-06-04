"""Base class for communication boards.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>


Bugs:
    Not known

"""

from time import sleep
from pylab_ml.base_instrument import logger
from pylab_ml.base_instrument import Instrument


class BaseBoard(Instrument):
    """Base class for communication boards.

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    A protocol board implements the communication with the sensor device
    under test.

    """

    def __init__(self, **kwargs):
        """Connect and initialize.

        Example: Initialization
           >>> ser = BaseBoard(addr='0403:6001')         # if only one Board with this VID:PID available
           >>> ser = BaseBoard(5)                        # COM-Port

        Args:
            addr (int): port number (optional), neccessary if more than 1 Teens at the usb-bus

        Raises:
           IOError:
              MaxReadErrorCount archieves.

        Returns:
            None.

        """
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
        self.com._init(self)

    def setup_inst(self):
        """Set setup instrument settings."""
        self.error = False             # otherwhile exceptions from registermaster
#        self._protocol_typ = ''
        self.lastcmd = ''
        """Last write command."""
        self.MaxReadErrorCount = 7
        """Maximum of succesive read errors (default = 7)."""
        self.ReadErrorCount = 0
        self._quiet = False
        super().setup_inst()

    def calc_parity(self, cmd, addr):
        """Calculate parity from cmd and addr."""
        value = '{:03b}{:05b}'.format(cmd, addr)
        odd_parity = 0 if value.count('1') % 2 else 1
        return odd_parity

    def calc_crc(self, addr, data, addr_bits=5, cmd=6, typ=None):
        """Calculate crc from addr and data."""
        if addr > 2**addr_bits - 1:
            msg = 'addr = 0x{:x} needs more than {} bits'.format(addr, addr_bits)
            raise ValueError(msg)
        value = '{:03b}{:05b}{}0{:016b}'.format(
            cmd, addr,
            self.calc_parity(cmd, addr),
            data,
        )
        if typ == 'only data':
            value = '0{:016b}'.format(data)
        crc = [0] * 4
        for bit in value:
            x = int(bit) ^ crc[3]
            crc[3] = crc[2]
            crc[2] = crc[1]
            crc[1] = crc[0] ^ x
            crc[0] = x
        return int(''.join(str(bit) for bit in reversed(crc)), 2)

    @property
    def id(self):
        """Get IDN string."""
        return (self.query('?v'))

    def message(self, message=None):
        """Device has no display, message display to logger.info."""
        if message is not None:
            logger.info(message)

    def read(self):
        """Return answer from Boad as string.

        if timeout -> result = '-1' and logger.error
        if Board not available -> result='deadbeef'
        """
        if self.inst is not None:
            try:
                value = self.inst.read()
                self.ReadErrorCount = 0
            except Exception:
                logger.error("{}: the value isn't readable".format(self.instName))
                value = '-1'
                self.ReadErrorCount += 1
        else:
            value = 'deadbeef'
        logger.debug('{}.base_board.read:  {!r}'.format(self.instName, value))
        return value

    def readbuffer(self):
        """Return complette buffer and return as string."""
        buffer = ''
        if self.inst is not None:
            while (self.inst.bytes_in_buffer > 0):
                buffer += self.inst.read() + '\n'
        return buffer

    def write(self, value):
        """Write cmd string to Board."""
        self.flush()
        logger.debug('{}.base_board.write: {!r}'.format(self.instName, value))
        if self.inst is not None:
            self.inst.write(value)
        self.lastcmd = value
        self.delay

    def query(self, value):
        """Write cmd string to Board and return answer."""
        self.write(value)
        return self.read()

    def flush(self):
        """Flush input buffer."""
        value = self.readbuffer()
        if value != '':
            logger.debug('{} read discarded: {!r}'.format(self.instName, value))

    def reset(self):
        """Reset vom the class."""
        self.ReadErrorCount = 0
        return 0

    @property
    def quiet(self):
        """Set/get quiet.

        switch off/on error-messages
        | on = True
        | off = False
        """
        return self._quiet

    @quiet.setter
    def quiet(self, value):
        self._quiet = value
        logger.info(f'{self.instName}.quit = {value}')

    @property
    def version(self):
        """Get version string."""
        self.write('?v')
        sleep(0.1)
        answer = self.read()
        if type(answer) is int and answer == -1:
            answer = '0'
        return answer

    @property
    def classname(self):
        """Get class name as string."""
        return self.__class__.__name__

    @property
    def delay(self):
        return self.__getattribute__(self._protocol_typ).delay

    @delay.setter
    def delay(self, value):
        self.__getattribute__(self._protocol_typ).delay = value

    @property
    def protocol_typ(self):
        """Set/get protocol typ."""
        return self._protocol_typ

    @protocol_typ.setter
    def protocol_typ(self, value):
        self._protocol_typ = value
        self.delay = self.__getattribute__(value).delay

    @property
    def ReadErrorCount(self):
        """Counter for Communication Errors, exception if MaxReadErrorCount archieves."""
        return self._readerrorcount

    @ReadErrorCount.setter
    def ReadErrorCount(self, value):
        self._readerrorcount = value
        if hasattr(self, 'MaxReadErrorCount') and self.ReadErrorCount > self.MaxReadErrorCount:
            raise IOError('{} MaxReadErrorCount reached = {}'.format(self.instName, self.MaxReadErrorCount))
