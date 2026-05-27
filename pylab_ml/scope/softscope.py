# -*- coding: utf-8 -*-
"""
This script defines the Softscope class, which is responsible for communicating with a softscope GUI via MQTT. 
The class allows for starting and stopping data sampling, setting the channel to be monitored, and adjusting the sample time. 
It uses a Timer thread to manage the sampling loop and handles MQTT commands to control its behavior. 
The class also includes error handling for cases where the specified channel is not defined or returns an error.

Created on Thu Jan  7 17:18:03 2021

@author: jung
"""
from ate_common.logger import LogLevel
from pylab_ml.common.mqtt_client import mqtt_deviceattributes
from pylab_ml.common import common
from time import time
from threading import Timer

__author__ = "Zlin526F"
__credits__ = ["Zlin526F"]
__email__ = "Zlin526F@github"


class Softscope(mqtt_deviceattributes):
    """
    Class for the communication with the softcope-GUI.

    via mqtt some command controlled the sending of data:
        start:
            create a Timer-thread with the loop-time = sampleTime
        stop:
            stop the Timer-thread
        setchannel(value):
            call the value as attribute for each timing event
        sampleTime:
            loop time

    TODO: very simple.....
            max sample Time ~50Hz
    """

    def __init__(self, mqttc, logger, instName="softscope"):
        """
        Initialise the softscope class and subscribe for mqtt if mqttc is not None
        
        Parameters
        ----------
            mqttc : MQTT client object
                The MQTT client to use for communication. If None, MQTT functionality will be disabled.
            logger : Logger object
                The logger to use for logging messages.
            instName : str, optional
                The name of the instrument. Default is "softscope".
        """
        self.instName = instName
        self.logger = logger
        super().__init__()
        self.gui = "pylab_ml.gui.instruments.softscope.softscope"  # semi-ctrl use this lib for the scope gui
        self.mqtt_all = ["setchannel()", "on()", "off()", "sampleTime", "test"]  # approved commands for mqtt
        if mqttc is not None:
            self.mqtt_add(mqttc, self)  # subscribe for mqtt and send information about the gui
        self.scopeChannel = None
        self._samplethread = None
        self.sampleTime = 0.1
        self._minSampleTime = 0.01
        self._sawtooth = 0
        self.topinstname = None
        self.busy = False

    def init(self, topinstname):
        """Initialize the topinstname for the strcall to get the value for the scopeChannel"""
        self.topinstname = topinstname

    def setchannel(self, value):
        """Set the scopeChannel via mqtt"""
        result = common.strcall(self.topinstname, value)
        self.scopeChannel = value if result != "ERROR" else "ERROR"
        # print(f'Softscope.setchannel: {value} -> {result}')
        self.publish_set("scopeChannel", self.scopeChannel)

    def on(self):
        """Start the softscope sampling."""
        if self.busy:
            self.off()
        if self.scopeChannel is None:
            self.logger.log_message(LogLevel.Error(), f"{self.instName} scopeChannel not defined")
            return
        self.busy = True
        self._newsample()

    def off(self):
        """Stop the softscope sampling."""
        self.busy = False
        if self._samplethread is not None:
            self._samplethread.cancel()

    @property
    def sampleTime(self):
        """Get the current sample time for the softscope."""
        return self._sampleTime

    @sampleTime.setter
    def sampleTime(self, value):
        """Set the sample time for the softscope."""
        if type(value) not in [int, float]:
            return
        self._sampleTime = value

    def close(self):
        """Close the softscope and disconnect from MQTT."""
        self.off()
        self.mqtt_disconnect()

    def _newsample(self):
        """Internal method to handle the sampling loop."""
        if not self.busy:
            return
        starttime = time()
        # print(f'_newsample: {self.topinstname}, {self.scopeChannel}')
        result = common.strcall(self.topinstname, self.scopeChannel)
        if result == "ERROR":
            self.logger.log_message(LogLevel.Error(), f"{self.instName} get ERROR from {self.scopeChannel}  -->stop sampling")
            return
        # print(result)
        mytime = self._sampleTime - (time() - starttime)
        if mytime <= 0:
            mytime = self._minSampleTime
        self._samplethread = Timer(mytime, self._newsample)
        self._samplethread.start()

    @property
    def test(self):
        """
        Get the current test value for the softscope.
        
        Returns
        -------
            int
                A sawtooth value that increments with each call and resets after reaching 256.
        """
        # print(f'call scope.sawtooth value= {self._sawtooth}')
        self._sawtooth += 1
        if self._sawtooth > 256:
            self._sawtooth = 0
        return self._sawtooth

    def __repr__(self):
        return f"{self.__class__}"


if __name__ == "__main__":
    from pylab_ml.common.mqtt_client import mylogger

    scope = Softscope(mqttc=None, logger=mylogger, instName="softscope")
