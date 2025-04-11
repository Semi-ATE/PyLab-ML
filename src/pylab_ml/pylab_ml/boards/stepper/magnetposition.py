"""Interface to the rotation axis with Teensy-Board.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>


"""
from inputimeout import inputimeout, TimeoutOccurred
from pylab_ml.base_instrument import logger
from pylab_ml.collate_instrument import Interface
from pylab_ml.boards.base_teensy import Teensy


class MagnetPosition (Teensy):
    """Interface to a z-axis and rotation axis with RP2040 Mini-Board.

    .. image:: ../static/rotationaxis.jpg

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    """

    interchoices = [Interface.usbserial]
    boardname = 'Magnet Position Control'
    PRECESSION = 0.0125           # Z-Spindle 4mm/U / 200 (step/U)  / 16 (Microsteps)
    ZMIN = -80

    def __init__(self, addr='2E8A:0005', identify=False, instName=None):
        """Initialise.

        Example: Initialization
           >>> ser = Rotationaxis()         # address not necessary if only one Teensy at USB-Port

        Args:
            addr (int): port number (optional), neccessary if more than 1 Teens at the usb-bus
            instName (string, optional): Instance Name from parent. Defaults to None.

        Raises:
            InvalidInstrumentConnection: something is wrong with the connection.

        Returns:
            None.
        """
        kwargs = {"addr": addr, "interface": None, "backend": None, "identify": identify, "instName": instName}
        self._use = self.boardname
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
        if self.inst is None:
            kwargs['message'] = 'Use Dummy MagnetPosition instead:'
            self.inst = Dummy(self, **kwargs)
            self._use = 'Dummy'
            self.setup_inst()
        self._zspeed = 40000
        self._spindle = 100
        self._zpos = None
        self._lock = True

    @property
    def zpos(self):
        """Set/get absolut position, in mm."""
        return self._zpos

    @zpos.setter
    def zpos(self, value):
        if self._zpos is None:
            self.zref()
        if (value > 0 or value < self.ZMIN) or self._zpos is None:
            logger.error(f'{self.id} set position, {value} is out of range')
            return
        self.zrel(value - self._zpos)

    def zrel(self, value):
        cmd = f'G00 Z{float(value)}'
        result = self.cmd(cmd)
        if result != cmd:
            logger.error(f'set position error: {result}')
            return -1
        self._zpos = self._zpos + value if self._zpos is not None else None
        return 0

    def zref(self):
        if not self.unlock():
            return
        user_input = str(input('drive to reference point:(y/n)'))
        while user_input == 'y':
            if self.zrel(10.0) != 0:
                return
            user_input = str(input('drive to reference point:(y/n)'))
        self._zpos = 0.0

    @property
    def zspeed(self):
        """Set/get speed for z-axis, in step/s."""
        return self._zspeed

    @zspeed.setter
    def zspeed(self, value):
        result = self.cmd(f'F{value}')
        if result == '' or int(result[1:]) != value:
            logger.error(f'{self.id} set zspeed, {value} is out of range')
        self._speed = value

    @property
    def spindle(self):
        return self._spindle

    @spindle.setter
    def spindle(self, value):
        if type(value) is str:
            if value == 'off':
                self.cmd('M03 0')
            elif value == 'on':
                self.cmd(f'M03 {self._spindle}')
            return
        self.cmd(f'M03 {value}')
        self._spindle = value

    def unlock(self):
        if not self._lock or self._lock == 'timeout' or self.id.find('Dummy') > 0:
            return False
        if self.cmd('unlock') == 'True':
            self._lock = False
            return True
        try:
            passwd = inputimeout(prompt=f'unlock {self.id} ?', timeout=10)
        except TimeoutOccurred:
            print('timeout...could not unlock {self.boardname}', flush=True)
            self._lock = 'timeout'
            return False
        if self.cmd(f'unlock {passwd}') != 'unlock':
            return False
        self._lock = False
        return True

    def close(self):
        self.spindle = 0
        self.zpos = 0
        self.zrel(1)
        super(__class__, self).close()

#    def write(self, msg):
#        """Write the instance with msg."""
#        self.inst.write(msg)

#    def read(self):
#        """Read the instance."""
#        return self.inst.read()

#    def query(self, cmd):
#        """Read the instance."""
#        if self._use == 'Dummy':
#            return self.inst.query(cmd)
#        super().query(cmd)


class Dummy(object):
    """Dummy object  for the MagnetPosition.

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    Usable if you have no real MagnetPosition as instance

    """
    boardname = 'Magnet Position Control Dummy'

    def __init__(self, parent, **kwargs):
        """Initialise."""
        # kwargs = {"addr": addr, "interface": interface, "backend": backend, "identify": identify, "instName": instName}
        if 'message' in kwargs:
            logger.error(kwargs['message'])
        else:
            logger.warning('Use Dummy MagnetPosition')
        self._lastcmd = ''
        self.bytes_in_buffer = 0

    def query(self, cmd):
        if cmd == 'v?':
            return self.boardname
        try:
            value = super(__class__, self).__getattribute__(cmd)
            try:
                value = int(value)
            except Exception:
                pass
            logger.debug(f'{self.boardname}: query {cmd} == {value}')
        except Exception:
            value = '0xdeadbeef'
            logger.debug(f'{self.boardname}: query {cmd} == {value}')
        return value

    def write(self, cmd):
        logger.debug(f"{self.boardname}: write '{cmd}'")

    def read(self):
        logger.debug('{self.boardname}: read')
        return "0xdeadbeef\n$OK"


if __name__ == '__main__':
    from pylab_ml.base_instrument import logsetup

    logsetup()

    mfield = MagnetPosition()
    mfield.helpboard
    mfield.zpos = -5.5

    mfield.zref()
    mfield.zpos = -21.5
    mfield.zpos = -10.5

    mfield.zrel(4.0)
    mfield.zrel(-14.0)

    mfield.zspeed = 10000
    mfield.zpos = -1
    mfield.zpos = -30

    mfield.zspeed = 40000
    mfield.zpos = -1
    mfield.zpos = -30

    mfield.spindle = 100
    mfield.spindle = 400
    print(f'Spindle = {mfield.spindle}')
    mfield.spindle = 'off'
    mfield.spindle = 'on'
    print(f'Spindle = {mfield.spindle}')

    mfield.close()
