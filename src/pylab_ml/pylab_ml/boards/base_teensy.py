"""Base Interface to the teensy board.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>

"""
import os
import warnings
from time import time
from pylab_ml.base_instrument import logger
from pylab_ml.collate_instrument import Interface
from pylab_ml.base_instrument import Instrument


class Teensy (Instrument):
    """Base Interface to the teensy board.

    .. image:: ../static/teensy32.png

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    Base USB Teensy driver


    more info to the hardware: https://www.pjrc.com/store/teensy32.html

    """

    interchoices = [Interface.usbserial]
    boardname = "Teensy"

    def __init__(self, **kwargs):
        """
        Initialise.

        Example: Initialization
           >>> ser = Teensy()         # if only one Teensy-Board available

        Args:
            addr (int): port number (optional), neccessary if more than 1 Teens at the usb-bus

            answer_mode: 'RH_teensy'   - answer like Teensy from Rolf Hakenes

        Returns:
            None.

        """
        # kwargs = {"addr" : addr, "interface" : None, "backend" : None, "identify" : identify, "instName" : instName}
        if 'addr' not in kwargs or kwargs['addr'] is None:
            kwargs['addr'] = '16C0:0483'
        super().__init__(**kwargs)
        self.logger = logger
        logger.debug("Class {}".format(self.__class__.__name__))
        self.com._init(self)

    def setup_inst(self):
        """Set instrument settings."""
        super().setup_inst()
        if self.inst and self.com.has_visa and not hasattr(self, 'com_para'):
            self.inst.baud_rate = 12000000
            self.inst.parity = self.com.pyvisa.constants.Parity.even
            self.inst.timeout = 2000
            self.inst.read_termination = '\r'
        elif self.inst and self.com.has_visa:
            self.inst.baud_rate = self.com_para['baud_rate']
            if self.com_para['Parity'] == 'none':
                parity = self.com.pyvisa.constants.Parity.none
            elif self.com_para['Parity'] == 'even':
                parity = self.com.pyvisa.constants.Parity.even
            elif self.com_para['Parity'] == 'odd':
                parity = self.com.pyvisa.constants.Parity.odd
            self.inst.parity = parity
            self.inst.timeout = 2000
            self.inst.read_termination = self.com_para['read_termination']
        self.has_visa = self.com.has_visa
        self.timeout = 5
        self.error = False
        self.errortext = ""
        self._ledmode = 'status'

    @property
    def id(self):
        """Get IDN string."""
        msg = ''
        answ = self.query('v?')
        for line in answ.split("\n"):
            if self.boardname in line or "Version" in line or "instance" in line:
                msg += line+'\n'
        if msg == '':
            logger.debug(f'get wrong id = {answ}')
        return (msg[:-1])

    def message(self, message=None):
        """Device has no display, message display to logger.info."""
        if message is None:
            logger.info("{}".format(self.instName))
        else:
            logger.info("{} {}".format(self.instName, message))

    def read(self, readline=False):
        """Get data from Teensy."""
        starttime = time()
        if self.inst is not None:
            value = ''
            while '$OK\r\n' not in value and "$Error\r\n" not in value:
                count = self.inst.bytes_in_buffer
                if self.has_visa is True and not readline and count > 0:
                    ans = self.inst.read_bytes(1)
                elif self.has_visa is True and readline and count > 0:
                    ans = self.inst.read()
                    self.inst.read_bytes(1)
                elif self.has_visa is True and count == 0:
                    if (time()-starttime) > self.timeout:
                        if len(value) == 0:
                            value = 'timeout'
                        break
                    else:
                        continue
                else:
                    ans = self.inst.read(1)
                value += ans.decode('utf-8') if not readline else ans
                if ans == b'' or readline:
                    break
            value = value.replace('\r', '')
        else:
            value = '-1'
        # if self.debug:
        logger.debug(' {}.read: {!r}'.format(self.instName, value))
        return value

    def write(self, value):
        """Send data to Teensy-Board."""
        # if self.debug:
        logger.debug(' {}.write: {!r}'.format(self.instName, value))
        if self.inst is not None:
            if self.has_visa is True:
                self.inst.write(value)
            else:
                if (os.sys.platform == 'linux'):
                    value += '\n'
                else:
                    value += '\r'
                self.inst.write(value.encode('utf-8'))

    def query(self, value):
        """Send write(value) and read the answer.

        Args:
            value (str): send to Teensy-Board

        Raises:
            ValueError: no response from Teensy-Board.

        Returns:
            TYPE: answer from Teensy-Board.

        """
        if self.inst is not None:
            self.write(value)
            value = ""
            val = self.read()
            starttime = time()
            while "$OK" not in val and "$Error" not in val:
                value = "%s%s" % (value, val)
                val = self.read()
                if (time()-starttime) > self.timeout:
                    logger.error('{} no response from Teensy-Board for {}s-> timeout and return'.format(self.instName, self.timeout))
                    self.error = True
                    # raise ValueError("%s%s" % (value, val))
                    break
            value = "%s%s" % (value, val)
            if "$OK" in val:
                self.error = False
            else:
                self.error = True
            return value
        else:
            return 'no instance\n$Error\n'

    def cmd(self, cmd, noresult=False):
        """Send <cmd> string to Teensy.

        returning filtered data
        """
        value = self.query(cmd)
        zline = ""
        z2line = ""
        result = ''
        instr = ''
        if self.debug > 1:
            logger.debug('{} {!r}'.format(self.instName, value))
        for line in value.split("\n"):
            if line.find('dbg') > -1:
                instr = line
            if "$OK" in line:
                if noresult is False:
                    result = zline
            if "$Error" in line:
                self.errortext = f'{zline}: {z2line}'
                result = '-1'
            z2line = zline
            zline = line
        if self.debug > 0:
            logger.debug('{} {} {}'.format(self.instName, instr, result))
        return (result)

    def flush(self):
        """Flush the USB buffer."""
        if self.inst is not None:
            if self.has_visa is True:
                logger.debug(f'{self.instName} flush Teensy USB read Buffer...')
                warnings.simplefilter("ignore")
                value = ''
                val = ''
                while (True):
                    # read out untill empty srting
                    val = ''
                    if self.inst.bytes_in_buffer > 0:
                        try:
                            val = self.inst.read()
                            value = "%s%s" % (value, val)
                        except Exception:
                            value = ''
                    if self.debug:
                        logger.debug('read:  {!r}'.format(value))
                    if val == '':
                        break
                logger.debug(f'{self.instName} Buffer flushed successfully!')
                warnings.simplefilter("default")
            else:
                self.inst.reset_output_buffer()
                self.inst.reset_input_buffer()
        else:
            logger.debug('{} no instance'.format(self.instName))

    @property
    def led(self):
        """Get/set led standby/status mode.

        Args:
           value (int):
              | 1          -> switch to led-standby mode and set Teensy led on
              | 1, 1-1000  -> switch to led-standby mode and set Teensy led on for 0-1000 ms
              | 0          -> switch to led-standby mode and set Teensy led off
              | 0, 1-1000  -> switch to led-standby mode and set Teensy led off for 0-1000 ms
              | stby       -> switch to led-standby mode and set Teensy led on
              | status     -> switch to led-status mode

        Returns:
           result (str): led mode
              | stby or status

        """
        result = self.cmd('led get_mode')[4:]
        return result

    @led.setter
    def led(self, value):
        error = False
        if isinstance(value, (int)):
            if self.led == 'status':
                self.cmd('led set_mode led_stby')
            if value == 0:
                self.cmd('led sleep')
            elif value == 1:
                self.cmd('led wakeup')
            else:
                error = True
        elif isinstance(value, (tuple)):
            if self.led == 'status':
                self.cmd('led set_mode led_stby')
            if value[0] == 0:
                self.cmd('led sleep {}'.format(value[1]))
            elif value[0] == 1:
                self.cmd('led wakeup {}'.format(value[1]))
        elif isinstance(value, (str)):
            if value.find('stby') == 0:
                self.cmd('led set_mode led_stby')
            elif value.find('status') == 0:
                self.cmd('led set_mode led_status')
            else:
                error = True
        if error:
            logger.error("{!r} wrong value {}, could be 0,1,'stby','status'".format(self.instName, value))

    def reset(self):
        """Send reset to Teensy-Board."""
        self.flush()
        if self.query('reset').split('$')[-1] != 'OK\n':
            logger.error("{!r} reset couldn't execute".format(self.instName))
        return

    @property
    def version(self):
        """Get firmware version."""
        result = self.id
        logger.info(result)
        return result

    @property
    def helpboard(self):
        """Read available commands from the Teesy-Board.

        Returns:
            None.

        """
        for line in self.query('?').split("\n"):
            print(line)


if __name__ == '__main__':
    from pylab_ml.base_instrument import logsetup
    logsetup()

    teensy = Teensy()
    logger.info(teensy.led)
    teensy.led = 1
    teensy.led = 0
    teensy.led = 'stby'

    teensy.help
    teensy.version
    logger.info(teensy.id)
    teensy.close()
