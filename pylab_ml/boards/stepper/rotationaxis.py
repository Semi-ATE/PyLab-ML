"""Interface to the rotation axis with Teensy-Board.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>


"""
from time import sleep
from pylab_ml.base_instrument import logger
from pylab_ml.collate_instrument import Interface
from pylab_ml.boards.base_teensy import Teensy


class Rotationaxis (Teensy):
    """Interface a rotation axis with Teensy-Board.

    .. image:: ../static/rotationaxis.jpg

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    """

    interchoices = [Interface.usbserial]
    PRECESSION = 0.028125           # 360/ 4 (gear transmission ratio) *200 (step/U)  *16 (Microsteps)
    # PRECESSION = 0.1125            # stepper motor without gear

    def __init__(self, addr=0, identify=False, instName=None):
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
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))

    @property
    def position(self):
        """Set/get absolut position, in steps (200*16 = 1 turn)."""
        value = self.cmd('step get_pos')
        return int(value.split('=')[-1])

    @position.setter
    def position(self, value):
        self.onoff = 1
        while (self.running == 1):
            sleep(0.5)
        result = self.cmd('step set_pos {}'.format(value))
        if int(result.split('=')[-1]) != value:
            logger.error('set position error')

    @property
    def onoff(self):
        """Set/get motor current on(=1) or off(=0)."""
        value = self.cmd('step get_enable')
        return int(value.split('=')[-1])

    @onoff.setter
    def onoff(self, value):
        result = self.cmd('step set_enable {}'.format(value))
        if int(result.split('=')[-1]) != value:
            logger.error('set onoff error')

    @property
    def speed(self):
        """Set/get speed, in step/s (default=16*200*2 Step/s)."""
        value = self.cmd('step get_speed')
        return int(value.split('=')[-1])

    @speed.setter
    def speed(self, value):
        result = self.cmd('step set_speed {}'.format(value))
        if int(result.split('=')[-1]) != value:
            logger.error('set speed error')

    @property
    def acceleration(self):
        """Get/set acceleration, in step/s² (default=4000)."""
        value = self.cmd('step get_acceleration')
        return int(value.split('=')[-1])

    @acceleration.setter
    def acceleration(self, value):
        result = self.cmd('step set_acceleration {}'.format(value))
        if int(result.split('=')[-1]) != value:
            logger.error('set acceleration error')

    @property
    def running(self):
        """Stepper is busy(=1) or stopped(=0)."""
        value = self.cmd('step running')
        return int(value.split('=')[-1])

    @property
    def angle(self):
        """Set/get rotation axis to absolut angle value in Grad (max=+-).

        precession = 4 (gear transmission ratio) *200 (step/U)  *16 (Microsteps) --> 1 step = 0,028125°
        """
        result = self.position*self.PRECESSION
        if result < 0:
            result = -(-result % 360)
        else:
            result = result % 360
        return result

    @angle.setter
    def angle(self, value):
        vz = 1
        if value < 0:
            vz = -1
        value = (abs(value) % 360) * vz
        angle2step = round(value / self.PRECESSION)
        if value != angle2step * self.PRECESSION:
            logger.info('{}° not possible, adjust to {:.6f}'.format(value, angle2step * self.PRECESSION))
        self.position = angle2step


if __name__ == '__main__':
    from pylab_ml.base_instrument import logsetup

    logsetup()

    rot = Rotationaxis()
    print(rot.led)
    rot.led = 1
    rot.led = 0
    rot.led = 'stby'

    rot.angle = 90
    rot.angle = 0
    rot.angle = -90
    rot.angle = 180

    rot.position = 16 * 200 * 5
    print('running = ', rot.running)
    sleep(3)
    print('running = ', rot.running)
    print('position = ', rot.position)
    rot.reset()
    print('position after reset= ', rot.position)
    print('current = ', rot.onoff)
    rot.position = -16*200*5
    print('new position= ', rot.position)
    rot.speed = 8000
    rot.position = 16 * 200 * 5 + 1
    print('new position= ', rot.position)
    rot.onoff = 0
    print('current = ', rot.onoff)

    rot.reset()
    print('angle = {}°'.format(rot.angle))
    rot.angle = 3.4
    print('angle = {}°'.format(rot.angle))
