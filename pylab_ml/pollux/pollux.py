"""
This script defines the Pollux class, which provides an interface to control the Pollux positioning controller using NI-VISA. 
The class includes methods for connecting to the device, calibrating it, setting limits, and controlling the position and 
speed of each axis (X, Z, and Angular). The status of each axis can also be checked to ensure they are ready for operation.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>
"""

import pyvisa
import pyvisa.constants as vi_const
from pylab_ml.base_instrument import logger
from pylab_ml.collate_instrument import Interface
from pylab_ml.base_instrument import LocalInstrument


class Pollux(LocalInstrument):
    """ Class to control the Pollux positioning controller via NI-VISA."""

    interchoices = [Interface.usbserial, Interface.gpib]

    def __init__(self, addr=3, instName='pollux'):
        """ 
        Initialize the Pollux controller instance and connect to the device, 
        then calibrate the device and set the limits for each axis.
        
        Parameters
        ----------
            addr : int
                The address of the Pollux controller (default is 3).
            instName : str
                The name of the Pollux controller instance (default is 'pollux').
        """
        super().__init__()
        self.rm = pyvisa.ResourceManager()
        self.resource_name = f"ASRL{addr}::INSTR"
        self.instName = instName
        self.device = None
        self.connect()
        self.calibrate()
        self.set_limits()

    def connect(self):
        """ Connect to the Pollux controller using NI-VISA settings that match LabVIEW's configuration. """
        try:
            self.device = self.rm.open_resource(self.resource_name)
            self.device.timeout = 1000 
            self.device.baud_rate = 19200
            self.device.data_bits = 8
            self.device.stop_bits = vi_const.StopBits.one
            self.device.parity = vi_const.Parity.none
            self.device.flow_control = 0 
            self.device.read_termination = '\n'
            self.device.write_termination = '\n'

            logger.info(f"Successfully connected to {self.resource_name} with LabVIEW settings.")
        except pyvisa.VisaIOError as e:
            logger.error(f"NI-VISA Connection Error: {e}")

    def disconnect(self):
        """ Disconnect from the Pollux controller and close the VISA resource. """
        if self.device:
            self.device.close()
            logger.info(f"Disconnected from {self.resource_name}")

    def _query(self, command):
        """ 
        Send a query command to the Pollux controller and return the response as a float.
        
        Parameters
        ----------
            command : str
                The command to send to the Pollux controller.
        
        Returns
        -------
            float
                The response from the Pollux controller, or None if an error occurs.
        """
        if self.device:
            try:
                response = self.device.query(command)
                logger.debug(f"Query: {command} | Response: {response}")
                return float(response)
            except pyvisa.VisaIOError as e:
                logger.error(f"Query Error: {e}")
                return None
        else:
            logger.warning("Device not connected.")
            return None
        
    def _write(self, command):
        """ 
        Send a write command to the Pollux controller.
        
        Parameters
        ----------
            command : str
                The command to send to the Pollux controller.

        Returns
        -------
            None.
        """
        if self.device:
            try:
                self.device.write(command)
                logger.debug(f"Write: {command}")
            except pyvisa.VisaIOError as e:
                logger.error(f"Write Error: {e}")
        else:
            logger.warning("Device not connected.")

    def _read(self):
        """
        Read a response from the Pollux controller and return it as a float.
        
        Returns
        -------
            float
                The response from the Pollux controller, or None if an error occurs.
        """
        if self.device:
            try:
                response = self.device.read()
                logger.debug(f"Read: {response}")
                return float(response)
            except pyvisa.VisaIOError as e:
                logger.error(f"Read Error: {e}")
                return None
        else:
            logger.warning("Device not connected.")
            return None
        
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
            return f"Unknown state or undocumented code"
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
        status_x = int(self._query("1 nst"))
        status_z = int(self._query("2 nst"))
        status_ang = int(self._query("3 nst"))
        
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
        self._write("1 ncal")
        self._write("2 ncal")
        self._write("3 ncal")

    def maximum_limits(self):
        """ Determine the maximum limits for each axis of the Pollux controller. """
        if self.status():
            self._write("1 nrm")
            self._write("2 nrm")

    def set_limits(self):
        """ 
        Set the maximum limits for each axis of the Pollux controller. 
        The limits are set to the following for each axis:
            - X-axis        : 60mm
            - Z-axis        : 100mm
            - Angular axis  : 354 degrees
        """
        self._write("0 60 1 setnlimit")
        self._write("0 100 2 setnlimit")
        self._write("0 354 3 setnlimit")

    def stop(self):
        """ Stop any ongoing movement of the Pollux controller. """
        self._write("1 nabort")
        self._write("2 nabort")
        self._write("3 nabort")

    @property
    def pos_x(self):
        """ Get the current position of the X-axis in millimeters. """
        return self._query("1 np")
    
    @pos_x.setter
    def pos_x(self, value):
        """ Set the position of the X-axis in millimeters, ensuring it does not exceed the maximum limit of 60mm. """
        if value > 60:
            logger.warning("X-axis position cannot exceed 60mm. Setting to 60mm.")
            value = 60
        if self.status():
            self._write(f"{float(value)} 1 nm")

    @property
    def pos_z(self):
        """ Get the current position of the Z-axis in millimeters. """
        return self._query("2 np")
    
    @pos_z.setter
    def pos_z(self, value):
        """ Set the position of the Z-axis in millimeters, ensuring it does not exceed the maximum limit of 100mm. """
        if value > 100:
            logger.warning("Z-axis position cannot exceed 100mm. Setting to 100mm.")
            value = 100
        if self.status():
            self._write(f"{float(value)} 2 nm")

    @property
    def ang(self):
        """ Get the current angular position in degrees. """
        return self._query("3 np")
    
    @ang.setter
    def ang(self, value):
        """ Set the angular position in degrees, ensuring it does not exceed the maximum limit of 354 degrees. """
        if value > 354:
            logger.warning("Angular position cannot exceed 354 degrees. Setting to 354 degrees.")
            value = 354
        if self.status():
            self._write(f"{float(value)} 3 nm")

    @property
    def speed_x(self):
        """ Get the current speed of the X-axis in millimeters per second. """
        return self._query("1 gnv")
    
    @speed_x.setter
    def speed_x(self, value):
        """ Set the speed of the X-axis in millimeters per second, ensuring it does not exceed the maximum limit of 13mm/s. """
        if value > 13:
            logger.warning("X-axis speed cannot exceed 13mm/s. Setting to 13mm/s.")
            value = 13
        self._write(f"{float(value)} 1 snv")

    @property
    def speed_z(self):
        """ Get the current speed of the Z-axis in millimeters per second. """
        return self._query("2 gnv")
    
    @speed_z.setter
    def speed_z(self, value):
        """ Set the speed of the Z-axis in millimeters per second, ensuring it does not exceed the maximum limit of 13mm/s. """
        if value > 13:
            logger.warning("Z-axis speed cannot exceed 13mm/s. Setting to 13mm/s.")
            value = 13
        self._write(f"{float(value)} 2 snv")

    @property
    def speed_ang(self):
        """ Get the current angular speed in degrees per second. """
        return self._query("3 gnv")
    
    @speed_ang.setter
    def speed_ang(self, value):
        """ Set the angular speed in degrees per second, ensuring it does not exceed the maximum limit of 26 degrees per second. """
        if value > 26:
            logger.warning("Angular speed cannot exceed 26 deg/s. Setting to 26 deg/s.")
            value = 26
        self._write(f"{float(value)} 3 snv")


if __name__ == "__main__":

    pollux = Pollux()

    if pollux.device:
        print("Current X position:", pollux.pos_x)
        print("Current Z position:", pollux.pos_z)
        print("Current Angular position:", pollux.ang)

        pollux.pos_x = 30
        pollux.pos_z = 50
        pollux.ang = 180

        print("Updated X position:", pollux.pos_x)
        print("Updated Z position:", pollux.pos_z)
        print("Updated Angular position:", pollux.ang)
