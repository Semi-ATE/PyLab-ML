"""Thermostreamer MPI_TA5000.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>

todo:
   MPI_TA5K send no acknowledge,
   check if this module is running for other Thermostreamer
"""
import time
from enum import Enum
from datetime import datetime
from pylab_ml.common.spinner import spinner
from pylab_ml.base_instrument import logger
from pylab_ml.collate_instrument import Interface
from pylab_ml.thermostreamer.base_thermostreamer import Base_Thermostreamer
from pylab_ml.attributes import create_attributes


class MPI_TA5K(create_attributes, Base_Thermostreamer):
    """
    Interface to the Thermostreamer MPI_TA5000.

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    .. image:: ../static/mpi_ta5000.jpg

    """

    # create functions or proberty and wrap it to the inst.funcname:
    # if state != necessary state -> switch to the necessary state
    #  proberty/function name -> inst.funcname (get,set)    , range,    call functions
    #                                                         range : None, Enum or range value
    #                                                         call functions: see help in attributes
    _properties = {
                  'airtemp':         (('TMPA?',  None),     None,           None),
                  'compressor':      (('COOL?', 'COOL '),   'Compressor',   {'sac': '_compressor(value)'}),
                  'dutsensortype':   (('DSNS?', 'DSNS '),   [0, 4],         None),
                  'dutmode':         (('DUTM?', 'DUTM '),   [0, 2],         None),
                  'duttemp':         (('TMPD?',  None),     None,           None),
                  'flow':            (('FLOW?', 'FLOW '),   'Flow',         {'sa':  '_wait4flow(value)'}),
                  'flowrate':        (('FLWM?', 'FLWM '),   [5, 18],        None),
                  'head':            (('HEAD?', 'HEAD '),   'Head',         {'sac': '_head(value)'}),
                  'headlock':        (('HDLK?', 'HDLK '),   'Headlock',     None),
                  'llim':            (('LLIM?', 'LLIM '),   [-150.0, 25.0], None),
                  'ramp':            (('RAMP?', 'RAMP '),   [0.0, 99.9],    None),
                  'setn':            (('SETN?', 'SETN '),   [0-17],         None),
                  'setupfile':       (('SFIL?', 'SFIL '),   None,           None),
                  'soak':            (('SOAK?', 'SOAK '),   [0, 9999],      None),
                  'state':           (('TECR?',  None),     None,           {'gac':  '_trstate(value)'}),
                  'Temp':            (('SETP?', 'SETP '),   None,           None),
                  'ulim':            (('ULIM?', 'ULIM '),   [25.0, 225.0],  None),
                  'window':          (('WNDW?', 'WNDW '),   [0.1, 9.9],     None),
                  'what':            (('WHAT?',  None),     None,           None),
                  }

    _states = {1:   '   at temperature (soak time has elapsed)',
               2:   '   not at temperature',
               4:   '   end of test (test time has elapsed',
               8:   '   end of one cycle',
               16:  '   end of all cycle',
               32:  '   stopped cycling ("stop on fail" signal was received',
               128: '   datalogging on',
               }

    interchoices = [Interface.usbserial, Interface.gpib]

    class Flow(Enum):
        """Enum for Flow control."""

        off = 0
        """value for flow off"""
        on = 1
        """value for flow on"""

    class Head(Enum):
        """Enum for Head control."""

        up = 0
        """value for head up"""
        down = 1
        """value for head down"""

    class Headlock(Enum):
        """Enum for Headlock control."""

        off = 0.0
        on = 1.0

    class Compressor(Enum):
        """Enum for Compressor control."""

        off = 0
        on = 1

    def __init__(self, addr=None, interface=None, backend=None, identify=True, instName=None):
        """Initialise.

        Args:
           addr (int):
              interface address
           interface (dev_interface.Instrument):
              gpib, usbserial
           instName (string):
              Instance Name from parent.

        Raises:
           TimeoutError:
              timeout after set temp.
           InvalidInstrumentConnection:
              something is wrong with the connection.

        Examples:
           >>> # Initialization
           >>> thermo = Thermo(addr=1)   # GPIB address

        more detailed examples:
           common for MPI_TA5k.py: :download:`examples/thermostreamer/mpi_ta5k <../../../examples/thermostreamer/mpi_ta5k.py>`

        """
        create_attributes.__init__(self)
        kwargs = {"addr": addr, "interface": interface, "backend": backend, "identify": identify, "instName": instName}
        Base_Thermostreamer.__init__(self, **kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
        self.setdefault()

    def setup_inst(self):
        """Set for instrument settings."""
        self.createattributes(self._properties)
        super().setup_inst()
        self.__is_initialized = True

    def setdefault(self):
        """Set for default values."""
        logger.measure("{} set default values".format(self.instName))
        # self.head=0                # head sould be hold in it' old position
        self.flow = self.Flow.off
        self.llim = -85             # lower temperature limit
        self.ulim = 180             # upper temperature limit
        self.window = 1.0           # temp window: 0.1 .. 9.9
        self.soak = 20              # tsoak time: 0 .. 9999s
        self.flowrate = 10          # flow rate: 4 .. 18
        self.dut_mode = 0           # 0: off (air control)
        self._setpoint = None
        self.dutsensortype = 0      # 0: no dut sensor
        self.get_state()

    # ----------------------------------------------------------
    # doc strings for _properties, propertie themselve will create form dictionary _properties
    @property
    def airtemp(self):
        """Current air temperture."""

    @property
    def compressor(self):
        """Set/get compressor on/off.

        | 'off'(=0, Compressor.off).
        | 'on'(=1, Compressor.on)

        """

    @property
    def dutsensortype(self):
        """Set/get dut sensortype.

        |  0: no dut sensor
        |  1: type T thermocouple
        |  2: type K thermocouple
        |  3: RTD
        """

    @property
    def dutmode(self):
        """Set/get dut mode.

        | 0: off (air control)
        | 1: on (dut control)
        | 2: TC Meter mode

        """

    @property
    def duttemp(self):
        """Get current dut temperture."""

    @property
    def flow(self):
        """Set/get flow.

        | 'off'(=0, Flow.off).
        | 'on'(=1, FLow.on).

        """

    @property
    def flowrate(self):
        """Set/get air flow rate."""

    @property
    def head(self):
        """Set/get head.

        | 'up'(=0, Head.up)
        | 'down'(=1, Head.down)

        """

    @property
    def headlock(self):
        """Set/get head lock.

        | 'off' (=0, Headlock.off) -> unlock
        | 'on' (=1, Headlock.on) -> lock

        """

    @property
    def llim(self):
        """Set/get lower limit."""

    @property
    def ramp(self):
        """Set/get ramp rate for the currently selected setpoint."""

    @property
    def setn(self):
        """Set/get setpoint.

        | set: select a setpoint to the current setpoint
        | get: read the current setpoint number

        """

    @property
    def setupfile(self):
        """Set/get filename for setup file.

        | get the filename,
        | set = load the  test setup file with the filename

        """

    @property
    def soak(self):
        """Set/get soak time for a given setpoint."""

    @property
    def state(self):
        """Get temperature status register."""

    @property
    def Temp(self):
        """Get/set the currently selected setpoint temperatur."""

    @property
    def ulim(self):
        """Set/get upper limit."""

    @property
    def window(self):
        """set/get setpoint temperature window."""

    # end doc strings for _properties
    # ----------------------------------------------------------

    def _compressor(self, value):
        self.flow = self.Flow.off

    def _head(self, value):
        if self.headlock == self.Headlock.on:
            logger.error("{}.Head  is locked! Can not move Head".format(self.instName))
            return self.ATTR_ERROR
        return None

    def _wait4flow(self, value):
        # logging.disable(logging.MEASURE)
        # if value==self.flow.on and self.head==self.Head.up: self.head=self.Head.down
        if value == self.Flow.on and float(self.inst.query('HDLK?')) == 0 and self.inst.query('HEAD?') == '0':
            logger.error("{}.Head  is up and not locked! Can not set Flow.on".format(self.instName))
            return self.ATTR_ERROR
        start = time.time()
        with spinner():
            while int(self.inst.query('FLOW?')) != value.value:
                time.sleep(0.5)
                if time.time()-start > 20:
                    logger.error("{}.Flow  couln't set flow := {}".format(self.instName, value))
                    return self.ATTR_ERROR

    def _trstate(self, value):
        for bit in range(0, 7):
            mask = value & (1 << bit)
            if mask > 0 and mask in self._states:
                print(self._states[mask])

    @property
    def id(self):
        """Query IDN."""
        value = self.inst.query('*IDN?')
        return value.replace('\r', '').replace('\n', '')

    def get_id(self):
        """
        Get identifikation from Thermostreamer.

        Returns:
            string: identifikation.
        """
        self.inst.write('*IDN?')
        return self.inst.read()

    @property
    def temp(self):
        """
        Set/get DUT sensor or air temperature.

        - get temperature
        - or set the currently selected setpoint temperatur and wait until temperture is reached.

        Args:
            value (float): set dut sensor or air temperature
            timeout (int, optional): timeout time. Defaults to 600s.

        Returns:
            float:
               * in Air mode: get main air temperature
               * in Dut mode: get DUT sensor temperatur
               * in TC Meter mode: siehe TEMP? in Manual.

        Example:
           >>> thermo.temp = -10, 100   # -> set temperatur=-10 and timeout to 100s (default 600s)
           >>> thermo.temp = 80         # -> set temperatur=80 and timeout is default = 600s
           >>> print(thermo.temp)      # get temperature

        """
        return float(self.inst.query('TEMP?'))

    @temp.setter
    def temp(self, value, timeout=600):
        if isinstance(value, tuple):
            timeout = value[1]
            value = value[0]
        newvalue = self._temp_set(value, timeout)
        logger.measure("{}.temp == {}".format(self.instName, newvalue))
        self._setpoint = float(value)

    def _temp_set(self, temp=None, timeout=600):
        """get/set the setpoint temperature."""
        if temp is None:
            return float(self.inst.query('SETP?'))
        # elif self._setpoint==None or float(temp) != self._setpoint:
        if -99.9 <= temp <= 225.0:
            self.inst.write('SETP {}'.format(temp))
        else:
            fmtstr = 'temp value {} must be in [-99.9, 225.0]'.format(temp)
            logger.error(fmtstr)
            raise ValueError(fmtstr)
        # if int(self.inst.query('HEAD?'))==self.Head.up.value:
        #    fmtstr = "{}.temp: Thermo Stream can set Temperature, if head is 'Up'".format(self.instName)
        #    logger.error(fmtstr)
        #    raise ValueError(fmtstr)
        if int(self.inst.query('FLOW?')) == self.Flow.off.value:
            self.flow = self.Flow.on
        logger.measure("{}.temp := {}".format(self.instName, temp))
        # wait until steady state of desired temperature
        start = datetime.now()
        with spinner():
            while 1:
                lifesign = False
                self.inst.write('TECR?')    # read temperature event condition register
                if self.inst.read() == '1':
                    break
                if ((datetime.now() - start).seconds) % 30 == 0:
                    print('\r  {} not at temperature or soak time not elapsed {}°C != {}°C, timeout in {}s    \r'
                          .format(self.instName, float(self.inst.query('TEMP?')), temp, timeout-(datetime.now() - start).seconds), end='')
                    lifesign = True
                if timeout > 0 and (datetime.now() - start).seconds > timeout:
                    fmtstr = 'timeout: T_set = {},  T_meas = {}'
                    raise TimeoutError(fmtstr.format(temp, self.temp))
                time.sleep(2)
            if lifesign:
                print(' ')
        self._setpoint = float(temp)
        return self.temp

    def get_state(self):
        """Get actual state and configuration."""
        lines = []
        lines.append('Setup File:  {}'.format(self.setupfile))
        lines.append('lower temp limit:  {}'.format(self.llim))
        lines.append('upper temp limit:  {}'.format(self.ulim))
        lines.append('temp window:       {}'.format(self.window))
        lines.append('soak time:         {}s'.format(self.soak))
        lines.append('flow rate:         {}'.format(self.flowrate))
        lines.append('flow:              {}'.format(self.flow))
        lines.append('head:              {}'.format(self.head))
        lines.append('temp:              {}'.format(self.temp))
        lines.append('temp_set:          {}'.format(self._temp_set()))
        _dutmode = {
            0: 'off (air control)',
            1: 'on (dut control)',
            2: 'TC meter mode',
        }
        val = self.dut_mode
        lines.append('dut mode:          {}: {}'.format(val, _dutmode[val]))
        lines.append('dut sensor type:   {}'.format(self.dutsensortype))
        for i in lines:
            logger.info(i)
        return lines


if __name__ == '__main__':
    from pylab_ml.base_instrument import logsetup

    logsetup()
    thermo = MPI_TA5K(addr=1, instName='thermo')
    # thermo.setupfile='GPIB-Config'
    thermo.get_state()
    # thermo.headlock                     # for Thermostreamer at 3d-Coil
    thermo.flow = 1
    thermo.head = 'up'

    thermo.head = 'down'
    thermo.flow = 'on'
    thermo.flow
    thermo.flow = 1
    thermo.flow = thermo.Flow.on
    thermo.flow = "sjflskjf"

    thermo.state
    thermo.temp = 20, 100
    thermo.state

    thermo.ulim
    thermo.ulim = 450

    thermo.llim
    thermo.window
    thermo.soak
    thermo.ramp
    thermo.flow
    thermo.dutsensortype
    thermo.dutmode

    print('Temperatur= {}°C'.format(thermo.temp))
    thermo.temp = 30, 100
    thermo.temp = 20
    thermo.flow = 'off'
    thermo.close()
