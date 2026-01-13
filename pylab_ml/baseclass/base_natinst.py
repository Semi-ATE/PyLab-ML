#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Intialize Basic Interface to the National Instruments PXIe.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>

"""
from datetime import datetime
from enum import Enum
from pylab_ml.base_instrument import logger
from pylab_ml.collate_instrument import Interface
from pylab_ml.baseclass.base_measurement import Measure
from pylab_ml.attributes import create_attributes


class NatInst (create_attributes, Measure):
    """
    Intialize Basic Interface to the National Instruments PXIe.

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    .. image:: ../_static/pxie_.jpg

    The NatInst baseclass can connect to National Instruments
    """

    def __init__(self, **kwargs):
        """Initialize.

        Args:
           **kwargs

        Example Initialization:
           >>> kwargs = {"addr": 3, "backend": backend, "identify": False, "instName": 'smu'}
           >>> instrument = NatInst(**kwargs)
        """
        create_attributes.__init__(self)
        if not hasattr(self, 'interchoices'):
            self.interchoices = [Interface.pxie]
        self.is_local = False
        if "runningmode" in kwargs:
            self.runningmode = kwargs["runningmode"]
        else:
            self.runningmode = 'auto'
        Measure.__init__(self, **kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
        self._state = self.State.disabled
        self.com._init(self)
        # self.self_cal(False)

    class State(Enum):
        """
        Possible states for the instrument.

           +-------------------+---------------------+----------------------+---------------------------------------------------+
           | actual state      | send command        |    new state         |  Comment                                          |
           +===================+=====================+======================+===================================================+
           | uncommitted state | commit              | committed state      |                                                   |
           +-------------------+---------------------+----------------------+---------------------------------------------------+
           | uncommitted state | initiate            | running state        |                                                   |
           +-------------------+---------------------+----------------------+---------------------------------------------------+
           | committed state   | modify any property | uncommitted state    | laut Beschreibung, ist das wirklich so?? es wird  |
           |                   |                     |                      | normalerweise immer eine exception ausglöst       |
           +-------------------+---------------------+----------------------+---------------------------------------------------+
           | running state     | abort               | uncommitted state    |                                                   |
           +-------------------+---------------------+----------------------+---------------------------------------------------+
           | running state     | commit              | running state        |                                                   |
           +-------------------+---------------------+----------------------+---------------------------------------------------+
        """

        disabled = -1
        """ reset instrument, output switched off"""
        uncommitted = 0
        """ uncommitted state """
        committed = 1
        """ committed state """
        running = 2
        """ running  state """

    class Runningmode(Enum):
        """Possible Modes for state handling."""

        auto = 0
        """handle commit, uncommit, running automatically"""
        man = 1
        """do it by yourselve"""

    # def init(self, identify=False):
    #    """Connect to NatInst instrument and initialize."""
    #    super().init(identify)

    def setup_inst(self):
        """Will call from class base_instrument.

        Set the instrument settings and intialise some variable to a startvalue.
        """
        self.createattributes(self._properties)
        self._state = self.State.uncommitted
        self.self_cal(False)

    def self_cal(self, force=True):
        """
        Perform self calibration if last self calibration is older than 1 day.

        Parameters
        ----------
        force : TYPE, optional
            if force==True -> perform self calibration independent from last calibration. The default is True.

        Returns
        -------
        None.
        gives information about the calibration

        """
        today = datetime.now()
        if self.__class__.__name__ == 'PXIe40xx':
            last_cal = self.inst.get_cal_date_and_time(0)
        elif self.__class__.__name__ == 'PXIe41xx':
            last_cal = self.inst.get_self_cal_last_date_and_time()
            self.inst.self_calibration_persistence = self.backend.SelfCalibrationPersistence.WRITE_TO_EEPROM
        else:                           # e.q. for Scope PXIe51xx found no last calibration date? ->so disable
            logger.warning('{!r} no calibration function found'.format(self.instName))
            last_cal = datetime.now()   # for other instruments self_cal on init is disalbed, check if last calibration date exist!
        # perform self calibration if last self calibration is older than 1 day
        if today.year != last_cal.year or today.month != last_cal.month or today.day != last_cal.day:
            logger.info("{!r} last calibration older than 1 day".format(self.instName))
        else:
            logger.info("{!r} last self calibration was today {}".format(self.instName, last_cal))
            if not force:
                return
            logger.info("{!r} anyway force == True -> do self calibration".format(self.instName))
        logger.info("{!r} self calibration ongoing ...".format(self.instName))
        try:
            self.inst.self_cal()
        except Exception:
            logger.error("\n\n{!r} self calibration error\n\n".format(self.instName))
            return
        logger.info("{!r} self calibration done".format(self.instName))

    @property
    def selftest(self):
        """
        Perform the device self-test routine and return pass, otherwise raise an exception.

        After selftest the device is in reset state.

        Returns
        -------
        result : bool
            state from selftest.
        """
        result = self.inst.self_test()        # if fail self_test make a raise
        if result is None:
            result = '{!r} selftest passed'.format(self.instName)
        self.reset()
        return result

    def reset(self):
        """
        Do nothing.

        Each Instrument has its own reset-routine

        """
        pass

    def clear(self):
        """Clear error status."""
        self.inst.clear()

    def commit(self):
        """Set state from Instrument to commit.

        usually handle automatically, if runningmode=='auto'.
        """
        oldstate = self.state
        self.inst.commit()
        self._state = self.State.committed
        logger.measure('{!r}.set state to {}, (old state = {})'.format(self.instName, self.state, oldstate))

    def abort(self):
        """Set state from Instrument to uncommitted.

        usually handle automatically, if runningmode=='auto'.
        """
        oldstate = self.state
        self.inst.abort()
        self._state = self.State.uncommitted
        logger.measure('{!r}.set state to {}, (old state = {})'.format(self.instName, self.state, oldstate))

    def initiate(self):
        """Set state from Instrument to running.

        usually handle automatically, if runningmode=='auto'.
        """
        oldstate = self.state
        self.inst.initiate()
        self._state = self.State.running
        logger.measure('{!r}.set state to {}, (old state = {})'.format(self.instName, self.state, oldstate))

    def disable(self):
        """Set state from Instrument to uncommitted.

        usually handle automtically, if runningmode=='auto'.
        """
        oldstate = self.state
        if self.inst is not None:
            self.inst.disable()
        self._state = self.State.uncommitted
        logger.measure('{!r}.set state to {}, (old state = {})'.format(self.instName, self.state, oldstate))

    def close_session(self):
        """Close the session (=inst)."""
        self.inst.close()
        self.inst = None

    def reopen_session(self, channels):
        """Reopen last session with channels."""
        if isinstance(channels, list):   # session needs stringlist, so create from array a string
            ch = ''
            for channel in channels:
                ch += str(channel)+','
            ch = ch[:-1]
        else:
            ch = channels
        self.inst = self.backend.Session(resource_name=self.addr, reset=False, channels=str(ch))
        self._create_channelinst(channels)

    def _create_channelinst(self, channels):
        self.ch = []
        i = 0
        if isinstance(channels, int) or len(channels) == 1:     # session has only one channel
            if isinstance(channels, list):
                channels = channels[0]
            self.ch.append(self.inst)
            while i != channels:                             # if channels not starts with 0 than create dummy inst
                self.ch.append(self.inst)
                i += 1
            self.channel = channels
        else:
            self.ch.append(self.inst)
            for index in channels:                              # session has more than 1 channel
                while i != index:
                    self.ch.append(None)
                    i += 1
                self.ch.append(self.inst.channels[index])
                i += 1
            channels.append(len(channels))
            self.channel = channels[0]

    def error_list(self):
        """List of outstanding errors."""
        errormsgs = self.inst.query(':SYST:ERR:ALL?')
        errors = errormsgs.split(",")[1::2]
        codes = errormsgs.split(",")[0::2]
        errorlist = []
        for c, m in zip(codes, errors):
            print("{} : {}".format(c, m))
            errorlist.append((c, m))
        return errorlist

    def message(self, message=None):
        """Device has no display, message display to logger.info."""
        if message is not None:
            logger.info(message)

    @property
    def id(self):
        """Get the id from the device."""
        msg = ('{}:  {} at PXI1Slot{}, Firmware:{}'.format(self.inst.instrument_manufacturer, self.inst.instrument_model,
                                                           self.addr, self.inst.instrument_firmware_revision))
        return msg

    def local(self):
        """Not possible, always remote control."""
        logger.warning("set local not possible, always remote control")
        self.is_local = False

    def _call_instance(self, function, rw, value=None):
        # func_for_channel_switch = ['channel_enabled', 'vertical_coupling', 'vertical_range', 'vertical_offset']
        if rw == "wr":
            # if function not in func_for_channel_switch:
            #     self.channel = self.channels[0]
            self.ch[self.channel].__setattr__(function, value)     # call inst.function=val enum[name.name]
            self.channel = 0
            # else:
            #     self.ch[self.channel].__setattr__(function, value)
        elif rw == "rd":
            value = self.ch[self.channel].__getattribute__(function)
            self.channel = 0
            return (value)

    @property
    def state(self):
        """
        Set/get state, only set state if necessary.

        Args:
           newstate (State): mod:`State`.

        Returns:
            (State)
        """
        return self._state

    @state.setter
    def state(self, newstate):
        for state in self.State:
            if newstate == state.name:
                newstate = state
        if self.runningmode == self.Runningmode.auto and self.inst is not None:
            oldstate = self.state
            if newstate == self.State.uncommitted:
                self.inst.abort()
                self._state = self.State.uncommitted
            elif newstate == self.State.committed:
                self.inst.commit()
                if oldstate != self.State.running:
                    self._state = self.State.committed
                else:
                    return
            elif newstate == self.State.running:
                if newstate != oldstate:
                    self.inst.initiate()
                self._state = self.State.running
            else:
                self._enum_error('state', newstate, self.State)
                return
            if oldstate != newstate and oldstate.name != newstate:
                logger.measure('{!r}.set state to {}, (old state = {})'.format(self.instName, self.state, oldstate))

    @property
    def runningmode(self):
        """Set/get runningmode."""
        return self._runningmode

    @runningmode.setter
    def runningmode(self, mode):
        found = False
        for i in self.Runningmode:
            if i.name == mode:
                self._runningmode = i
                found = True
        if not found:
            self._enum_error('runningmode', mode, self.Runningmode)
