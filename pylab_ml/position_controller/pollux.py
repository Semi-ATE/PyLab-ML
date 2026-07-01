"""
This script defines the Pollux class, which provides an interface to control the Pollux positioning controller.
The class includes methods for connecting to the device, calibrating it, setting limits, and controlling the position and
speed of each axis (X, Z, and Angular). The status of each axis can also be checked to ensure they are ready for operation.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>
"""

import warnings
from pylab_ml.base_instrument import logger
from pylab_ml.collate_instrument import Interface
from pylab_ml.base_instrument import Instrument


class Pollux(Instrument):
    """ Class to control the Pollux positioning controller."""

    interchoices = [Interface.usbserial]

    def __init__(self, **kwargs):
        """
        Initialize the Pollux controller instance and connect to the device,
        then calibrate the device and set the limits for each axis.
        """
        # kwargs = {"addr" : addr, "interface" : None, "backend" : None, "identify" : identify, "instName" : instName}
        if 'addr' not in kwargs or kwargs['addr'] is None:
            kwargs['addr'] = '0403:6001'
        super().__init__(**kwargs)
        self.logger = logger
        logger.debug("Class {}".format(self.__class__.__name__))
        self.com._init(self)
        self._blocking_mode = False

    def setup_inst(self):
        """Set instrument settings."""
        super().setup_inst()
        if self.inst and self.com.has_visa and not hasattr(self, 'com_para'):
            self.inst.baud_rate = 19200
            self.inst.data_bits = 8
            self.inst.parity = self.com.pyvisa.constants.Parity.none
            self.inst.timeout = 1000
            self.inst.flow_control = 0
            self.inst.stop_bits = self.com.pyvisa.constants.StopBits.one
            self.inst.read_termination = '\n'
            self.inst.write_termination = '\n'
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

    @property
    def id(self):
        """Get IDN string."""
        msg = ''
        answ = self.inst.query('1 nidentify')
        for line in answ.split("\n"):
            if "Pollux" in line:
                msg += line+'\n'
        if msg == '':
            logger.debug(f'get wrong id = {answ}')
        return (msg[:-1])

    def disconnect(self):
        """ Disconnect from the Pollux controller and close the VISA resource. """
        if self.inst:
            self.inst.close()
            logger.info(f"Disconnected from {self.resource_name}")

    def _decode_status(self, status_code):
        """
        Decode the status code from the Pollux controller.

        Parameters
        ----------
            status_code : int
                The status code to decode.

        Returns
        -------
            str
                A human-readable description of the status code.
        """
        reasons = []

        if status_code & 1:
            reasons.append("Move in progress")
        if status_code & 4:
            reasons.append("Machine error occurred")
        if status_code & 16:
            reasons.append("Speed mode not active")
        if status_code & 32:
            reasons.append("Current position within the target window")
        if status_code & 64:
            reasons.append("Motor driver disabled from hardware input")
        if status_code & 128:
            reasons.append("Motion disabled event occurred - reset required")
        if not reasons:
            return "Unknown state or undocumented code"
        return " | ".join(reasons)

    def status(self):
        """
        Check the status of each axis (X, Z, Angular) and return True if all are ready,
        otherwise return False and log the reasons for each axis that is not ready.

        Returns
        -------
            bool
                True if all axes are ready, False otherwise.
        """
        status_x = int(self.inst.query("1 nst"))
        status_z = int(self.inst.query("2 nst"))
        status_ang = int(self.inst.query("3 nst"))

        if status_x == 0 and status_z == 0 and status_ang == 0:
            return True

        else:
            if status_x != 0:
                reason = self._decode_status(status_x)
                logger.warning(f"X-axis not ready. Code {status_x}: {reason}")

            if status_z != 0:
                reason = self._decode_status(status_z)
                logger.warning(f"Z-axis not ready. Code {status_z}: {reason}")

            if status_ang != 0:
                reason = self._decode_status(status_ang)
                logger.warning(f"Angular axis not ready. Code {status_ang}: {reason}")

            return False

    def calibrate(self):
        """ Calibrate each axis of the Pollux controller to determine the origin (lower limit). """
        self.stop()
        self.inst.write("1 ncal")
        self.inst.write("2 ncal")
        self.inst.write("3 ncal")

    def base_position(self):
        """
        Set the base position for each axis of the Pollux controller.
        The base position is set to the following for each axis:
            - X-axis        : 40mm
            - Z-axis        : 100mm
            - Angular axis  : 0 degrees
        """
        self.inst.write("40.0 1 nm")
        self.inst.write("100.0 2 nm")
        self.inst.write("0.0 3 nm")

    def maximum_limits(self):
        """ Determine the maximum limits for each axis of the Pollux controller. """
        if self.status():
            self.inst.write("1 nrm")
            self.inst.write("2 nrm")

    def set_limits(self):
        """
        Set the maximum limits for each axis of the Pollux controller.
        The limits are set to the following for each axis:
            - X-axis        : 60mm
            - Z-axis        : 100mm
            - Angular axis  : 354 degrees
        """
        self.inst.write("0 60 1 setnlimit")
        self.inst.write("0 100 2 setnlimit")
        self.inst.write("0 354 3 setnlimit")

    def stop(self):
        """ Stop any ongoing movement of the Pollux controller. """
        self.inst.write("1 nabort")
        self.inst.write("2 nabort")
        self.inst.write("3 nabort")
        
    @property
    def blocking_mode(self):
        """
        Retrieves the current blocking mode status.
        """
        return self._blocking_mode

    @blocking_mode.setter
    def blocking_mode(self, value):
        """
        Sets the blocking mode for the controller.
        """
        if not isinstance(value, bool):
            raise TypeError("blocking_mode must be a boolean (True or False).")
            
        self._blocking_mode = value
        self.logger.debug(f"Blocking mode set to: {self._blocking_mode}")

    @property
    def pos_x(self):
        """ Get the current position of the X-axis in millimeters. """
        return self.inst.query("1 np")

    @pos_x.setter
    def pos_x(self, value):
        """ Set the position of the X-axis in millimeters, ensuring it does not exceed the maximum limit of 60mm. """
        if value > 60:
            logger.warning("X-axis position cannot exceed 60mm. Setting to 60mm.")
            value = 60
        if self.status():
            self.inst.write(f"{float(value)} 1 nm")
            if self._blocking_mode:
                while not self.status():
                    pass

    @property
    def pos_z(self):
        """ Get the current position of the Z-axis in millimeters. """
        return -float(self.inst.query("2 np"))

    @pos_z.setter
    def pos_z(self, value):
        """ Set the position of the Z-axis in millimeters, ensuring it does not exceed the maximum limit of -100mm. """
        if value < -100:
            logger.warning("Z-axis position cannot exceed -100mm. Setting to -100mm.")
            value = -100
        if self.status():
            self.inst.write(f"{float(abs(value))} 2 nm")
            if self._blocking_mode:
                while not self.status():
                    pass

    @property
    def ang(self):
        """ Get the current angular position in degrees. """
        return self.inst.query("3 np")

    @ang.setter
    def ang(self, value):
        """ Set the angular position in degrees, ensuring it does not exceed the maximum limit of 354 degrees. """
        if value > 354:
            logger.warning("Angular position cannot exceed 354 degrees. Setting to 354 degrees.")
            value = 354
        if self.status():
            self.inst.write(f"{float(value)} 3 nm")
            if self._blocking_mode:
                while not self.status():
                    pass

    @property
    def speed_x(self):
        """ Get the current speed of the X-axis in millimeters per second. """
        return self.inst.query("1 gnv")

    @speed_x.setter
    def speed_x(self, value):
        """ Set the speed of the X-axis in millimeters per second, ensuring it does not exceed the maximum limit of 13mm/s. """
        if value > 13:
            logger.warning("X-axis speed cannot exceed 13mm/s. Setting to 13mm/s.")
            value = 13
        self.inst.write(f"{float(value)} 1 snv")

    @property
    def speed_z(self):
        """ Get the current speed of the Z-axis in millimeters per second. """
        return self.inst.query("2 gnv")

    @speed_z.setter
    def speed_z(self, value):
        """ Set the speed of the Z-axis in millimeters per second, ensuring it does not exceed the maximum limit of 13mm/s. """
        if value > 13:
            logger.warning("Z-axis speed cannot exceed 13mm/s. Setting to 13mm/s.")
            value = 13
        self.inst.write(f"{float(value)} 2 snv")

    @property
    def speed_ang(self):
        """ Get the current angular speed in degrees per second. """
        return self.inst.query("3 gnv")

    @speed_ang.setter
    def speed_ang(self, value):
        """ Set the angular speed in degrees per second, ensuring it does not exceed the maximum limit of 26 degrees per second. """
        if value > 26:
            logger.warning("Angular speed cannot exceed 26 deg/s. Setting to 26 deg/s.")
            value = 26
        self.inst.write(f"{float(value)} 3 snv")

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

    def message(self, message=None):
        """Device has no display, message display to logger.info."""
        if message is None:
            logger.info("{}".format(self.instName))
        else:
            logger.info("{} {}".format(self.instName, message))

    def reset(self):
        """Send reset to Pollux-Drive."""
        self.flush()
        self.stop()
        self.calibrate()
        self.set_limits()
        return


if __name__ == "__main__":

    pos_controller = Pollux()

    if pos_controller.inst:
        print("Current X position:", pos_controller.pos_x)
        print("Current Z position:", pos_controller.pos_z)
        print("Current Angular position:", pos_controller.ang)

        pos_controller.pos_x = 30
        pos_controller.pos_z = -50
        pos_controller.ang = 180

        print("Updated X position:", pos_controller.pos_x)
        print("Updated Z position:", pos_controller.pos_z)
        print("Updated Angular position:", pos_controller.ang)
