"""Interface to the Power-Measuremet-Unit (SMU) NI PXIe-41xx (e.q. 4138, 4141).

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>

"""

import os
import numpy as np
import math
import time
import hightime
import matplotlib.pyplot as plt

from pylab_ml.collate_instrument import Interface
from pylab_ml.base_instrument import InvalidInstrumentConnection
from pylab_ml.baseclass.base_natinst import NatInst
from pylab_ml.base_instrument import logger


class PXIe41xx(NatInst):
    """
    Interface to the Power-Measuremet-Unit (SMU) NI PXIe-41xx (e.q. 4138, 4141).

    .. image:: ../_static/pxie_4138.jpg

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    todo:
        add sequence_loop_count


    The National Instruments PXIe-41xx can source and sink power in all four voltage/current quadrants and
    measure voltage and current precisely

    This Module supports (=tested) the National Instruments
       * PXIe-4138
       * PXIe-4141

    known Bugs:
       * wenn eine mqtt message von extern empfangen wird, so kann ein aktuelles Artribute
         set/get unterbrochen werden, und es kann dadurch zu Problemen mit dem aktuellen state geben.
         z.bsp aperture_time=2, es kommt aber ein voltage von extern (weil gui aufgerufen wird),
         state war auf uncommited, voltage setzt state auf running
         aperture_time wird weiter verarbeitet, brauch state aber uncommited
         ==> setzen von Attribute darf nicht unterbrochen werden...
       * Source Mode must be configured to Single Point when multiple channels are present
         in the same session (e.q. PXIe4141) -> Workaround for stair_sweep, which is implemented :

         1. rescue all adjustments
         2. close session (source remain their state)
         3. reopen only one channel
         4. write adjustements to this channel
         5. run stair_sweep
         6. close session
         7. reopen the channels again and write all adjustements to the channels

         * --> if you know a better solution, please improve the stair_sweep

    some functions of the PXIe41xx are not implemented now,
       see: http://nimi-python.readthedocs.io/en/master/nidcpower.html
       or read the manual http://zone.ni.com/reference/en-XX/help/370736U-01/

          * self.ch[0].source_delay = 0.01667
          * self.ch[0].sequence_loop_count = run count x sequence

    for generell measurement: http://www.ni.com/de-de/innovations/white-papers/14/top-measurement-considerations-for-modular-source-measure-units-.html

    """

    try:
        import nidcpower

        _has_nidcpower = True
    except ImportError:
        _has_nidcpower = False
        if os.sys.platform != "win32":
            logger.error("import nidcpower not found")
        else:
            logger.error("no import nidcpower can be found on non Windows platforms")

    # create functions or proberty and wrap it to the inst.funcname:
    # if state != necessary state -> switch to the necessary state
    #  proberty/function name -> inst.funcname (get,set)    , range,    call functions
    #                                                         range : None, Enum or range value
    #                                                         call functions: see help in attributes
    _properties = {
        "auto_zero": ("auto_zero", "backend.AutoZero", {"sac": "checkstate(uncommitted)"}),
        "aperture_time_units": ("aperture_time_units", "backend.ApertureTimeUnits", {"sac": "checkstate(uncommitted)"}),
        "aperture_time": ("aperture_time", None, {"sac": "checkstate(uncommitted)"}),
        "dc_noise_rejection": ("dc_noise_rejection", "backend.DCNoiseRejection", {"sac": "checkstate(uncommitted)"}),
        "output_function": ("output_function", "backend.OutputFunction", {"sac": "checkstate(uncommitted)"}),
        "sense": ("sense", "backend.Sense", {"sac": "checkstate(uncommitted)"}),
        "i_autorange": ("current_level_autorange", None, {"sac": "checkstate(uncommitted)"}),
        "I_autorange": ("current_limit_autorange", None, {"sac": "checkstate(uncommitted)"}),
        "v_autorange": ("voltage_level_autorange", None, {"sac": "checkstate(uncommitted)"}),
        "V_autorange": ("voltage_limit_autorange", None, {"sac": "checkstate(uncommitted)"}),
        "sequenceLoopCount": ("sequence_loop_count", [1, 134217727], {"sac": "checkstate(uncommitted)"}),
        "transientResponse": ("transient_response", "backend.TransientResponse", {"sac": "checkstate(uncommitted)"}),
        "onoff": ("output_enabled", [0, 1, True, False], {"sac": "checkstate(running)"}),
    }

    interchoices = [Interface.pxie]

    def __init__(self, addr=None, channels="0", identify=False, instName=None, runningmode="auto"):
        """
        Initialise.

        Args:
           addr (string):
              name from the PXI-Slot e.q. 'PXI1Slot3' or 'SMU'.
           channels (string, optional): (only 4141).
              Specifies which output channel(s) to include to this module.
              Specify multiple channels by using a channel list or a channel range.
              A channel list is a comma (,) separated sequence of channel names.
              For example, '0,2' specifies channels 0 and 2.
           identify (bool, optional):
              Defaults to False.
           instName (string, optional):
              Instance Name from top.
           runningmode (string, optional):
              handle state of the instrument automaticall or manual. Defaults to 'auto'.

        Raises:
           InvalidInstrumentConnection: something is wrong with the connection.

        .. note::
           For Instrument handling it is much easier to set runningmode = 'auto' (default).
           Otherwise you have to handle commit, initiate and abort by yourselve,
           and often you will raise an Excepetion by the instrument.

        *Examples:*
           * Initialization
              >>> vdd = PXIe41xx(addr=3,instName='vdd')   # connect and initialize instrument PXI-4138 or one channel fro PXI-4141
              >>> vdd = PXIe41xx(addr=3,channel='0,1',instName='vdd')   # connect and initialize instrument PXI-4141 with channel 0,1

           * Use instrument as voltage source
              >>> vdd.i_clamp = 0.01           # current protection
              >>> vdd.voltage = 3.3            # set output voltage
              >>> i = vdd.current              # measure (supply) current

           * Use instrument as current source
              >>> vdd.v_clamp = 5              # voltage protection
              >>> vdd.current = 0.1            # set output current_range
              >>> v = vdd.voltage              # measure voltage

           * detailed example of usage:
              * common for PXIe4138: :download:`examples/smu/PXIe4138.py <../../../examples/smu/PXIe4138.py>`
              * common for PXIe4141: :download:`examples/smu/PXIe4141.py <../../../examples/smu/PXIe4141.py>`
              * measure loops : :download:`examples/smu/PXIe4141_2.py <../../../examples/smu/PXIe4141_2.py>`
              * loops and stairsweep combined (2x faster as the example before), for PXIe4141/PXIe4138: :download:`examples/smu/PXIe4141_3.py <../../../examples/smu/PXIe4141_3.py>`
              * and an example, how you should not used this module: :download:`examples/smu/PXIe4141_badexample.py <../../../examples/smu/PXIe4141_badexample.py>`

        """
        if not self._has_nidcpower:
            msg = "\nPXIe41xx not usable!! missing nidcpower\n"
            msg = msg + "for installing nidcpower:\n"
            msg = msg + "    Start anaconda prompt and write: python –m pip install nidcpower\n"
            msg = msg + "For more infomation see:   http://nimi-python.readthedocs.io\n"
            raise InvalidInstrumentConnection(msg)
        kwargs = {"addr": addr, "channels": channels, "backend": self.nidcpower, "identify": identify, "instName": instName, "runningmode": runningmode}
        self.gui = "labml_adjutancy.gui.instruments.smu.smu"
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
        self.msg_row_col = (1, 20)

    def setup_inst(self):
        """Set the instrument settings and intialise some variable."""
        super().setup_inst()
        self.mqtt_all = [
            "id",
            "output_function",
            "onoff",
            "on()",
            "off()",
            "voltage",
            "current",
            "Voltage",
            "Current",
            "v_autorange",
            "i_autorange",
            "V_autorange",
            "I_autorange",
            "v_clamp",
            "i_clamp",
            "v_range",
            "i_range",
            "V_range",
            "I_range",
            "sense",
            "cmpl",
            "channel",
            "measure",
            "stime",
            "sweepto",
        ]
        # self.inst.supported_instrument_models
        self.onAfterset = True
        self.compliance = True
        """Check compliance after each single measurment.

           | True: check compliance after each single measurment (voltage or current), (default=True)
           | False: no compliance after measurement (if you want more speed)
        """
        self._measure = "vir"
        self._sweepto = 0.0
        self._v_clamp = 6.0  # reset value = 6V
        self._v_range = 6.0  # reset value = 6V
        self._stair_delay = 10  # in us, for calculate  rise/fall time stair_sweep
        self._stair_mintime = 100  # in microseconds, mninimum rise/fall time for stair_sweep
        self.stair_step_set = [[0, 0, 0.1], {"typ": "V"}]
        self.stair_step_get = np.array([])
        self.stair_measure = ""
        channels = []
        for ch in self.channels.split(","):
            channels.append(int(ch))
        self.channels = channels
        self._create_channelinst(channels)
        self.channel = channels[0]

    # ----------------------------------------------------------
    # doc strings for _properties, propertie themselve will create form dictionary _properties
    @property
    def aperture_time(self):
        """Specifiy the measurement aperture time for the channel configuration.

        Aperture time is specified in the units set by the aperture_time_units property
        """

    @property
    def aperture_time_units(self):
        """Specifiy the units of the aperture_time property for the channel configuration.

        SECONDS or POWER_LINE_CYCLES.
        see: http://nimi-python.readthedocs.io/en/master/nidcpower/class.html#aperture-time-units
        """

    @property
    def auto_zero(self):
        """Specifiy the auto-zero method to use on the device.

        OFF, ON or ONCE.
        see: http://nimi-python.readthedocs.io/en/master/nidcpower/class.html#auto-zero
        """

    @property
    def dc_noise_rejection(self):
        """Determine the relative weighting of samples in a measurement.

        NORMAL or SECOND_ORDER
        see: https://nimi-python.readthedocs.io/en/master/nidcpower/class.html#dc-noise-rejection
        """

    @property
    def i_autorange(self):
        """Get/set current measurement autorange."""

    @property
    def I_autorange(self):
        """Get/set current drive autorange."""

    @property
    def onoff(self):
        """Get/set on state (True), for set 1 or 'on' always possible."""

    @property
    def output_function(self):
        """Configure the output funkction.

        DC_CURRENT or DC_VOLTAGE
        """

    @property
    def sense(self):
        """Get/set local or remote sensing of the output voltage.

        LOCAL or 'REMOTE'
        """

    @property
    def v_autorange(self):
        """Get/set voltage measurement autorange.

        True or False
        """

    @property
    def V_autorange(self):
        """Get/set voltage drive autorange."""

    # end doc strings for _properties
    # ----------------------------------------------------------'

    def checkstate(self, value):
        """
        Compare actual state with value and set it to value if compare false.

        Parameters
        ----------
        value : :mod:`NatInst.State`
            expected status.

        Returns
        -------
        None.

        """
        self.state = value

    def reset(self):
        """
        reset, and all channels set to.

          * current_limit_autorange=True
          * voltage_limit_autorange=True
          * power_line_frequency = 50.0
          * aperture_time_units=POWER_LINE_CYCLES
          * aperture_time=2
          * inst.auto_zero=OFF
          * dc_noise_rejection=SECOND_ORDER
        """
        super().reset()
        self.inst.reset_device()
        for inst in self.ch:
            if inst is not None:
                inst.current_limit_autorange = True  # set to default, it ist much easiere to set the current/voltage limit with limit_autorange=True
                inst.voltage_limit_autorange = True
                inst.power_line_frequency = 50.0
                inst.aperture_time_units = self.nidcpower.ApertureTimeUnits.POWER_LINE_CYCLES
                inst.aperture_time = 2  # set aperture time to 2 PLC
                inst.auto_zero = self.nidcpower.AutoZero.OFF  # disable auto zero
                try:  # not possible for PXI-4138
                    inst.dc_noise_rejection = self.nidcpower.DCNoiseRejection.SECOND_ORDER  # set dc noise rejection to "second order"
                except Exception:
                    pass
                inst.output_enabled = False
        # self.initiate()
        # self.commit()

    def close(self):
        """Disable all outputs and terminate interface."""
        self.disable()
        super().close()

    def on(self):
        """Switch output on."""
        self.onoff = True

    def off(self):
        """Switch output off."""
        self.onoff = False

    @property
    def onAfterset(self):
        """
        Define behaving after change voltage/curret setting.

        Args: if set
           value (bool):
              * True : enable output after voltage/current setting (default).
              * False : output not switching after voltage/current setting.

        Returns: if get
            value (bool):
                True or False.

        """
        return self._onAfterset

    @onAfterset.setter
    def onAfterset(self, value):
        self._onAfterset = value

    @property
    def measure(self):
        """Get voltage and current together without delay, or set the measure typ.

        Returns:
           * float: mesasured voltage.
           * float: measured current.

        Tip:
            measure is 2x faster as separate voltage and current.

        """
        # measure=self.ch[self.channel].fetch_multiple(1)    # in sequence mode
        if not self.onoff_cache:
            logger.error("{self.instName}.measure not possible if instrument = off")
            return 0, 0
        self.checkstate("running")
        elements = self.ch[self.channel].measure_multiple()[0]
        # if len(elements == 1):
        if self.compliance:
            logger.measure("{!r}.voltage == {}, current = {}, Cmpl={}".format(self.instName, elements[0], elements[1], self.cmpl))
        else:
            logger.measure("{!r}.voltage == {}, current = {}".format(self.instName, elements[0], elements[1]))
        return elements[0], elements[1]

    @measure.setter
    def measure(self, typ="vir"):
        self._measure = typ

    @property
    def cmpl(self):
        """
        Check compliance from Device.

        Returns
        -------
        value : bool
           * False no compliance
           * True  compliance, limit accomplished

        """
        self.checkstate("running")
        value = self.ch[self.channel].query_in_compliance()
        if value:
            logger.warning("{!r} Compliance == {}".format(self.instName, value))
        return value

    @property
    def sweepto(self):
        """
        This is the end value if you run a sweep.

        Returns
        -------
        None.

        """
        return self._sweepto

    @sweepto.setter
    def sweepto(self, value):
        self._sweepto = value

    @property
    def voltage(self):
        """
        Get or set output voltage.

        If the voltage is set, the output is switched on immediately (if self.onAfterset == True).

        Args:
           value (float): set to voltage (in V).
        Returns:
           value (float): output voltage (in V).

        """
        self.checkstate("running")
        value = self.ch[self.channel].measure(self.nidcpower.MeasurementTypes["VOLTAGE"])
        if self.compliance:
            logger.measure("{!r}.voltage == {}, Cmpl={}".format(self.instName, float(value), self.cmpl))
        else:
            logger.measure("{!r}.voltage == {}".format(self.instName, float(value)))
        return value

    @voltage.setter
    def voltage(self, value):
        if self.output_function != self.backend.OutputFunction.DC_VOLTAGE:
            self.output_function = self.backend.OutputFunction.DC_VOLTAGE
        if isinstance(value, (int, float)):  # set static voltage
            self.ch[self.channel].voltage_level = float(value)
            logger.measure("{!r}.voltage := {}".format(self.instName, float(value)))
            if self.onAfterset:
                self.onoff = True
        elif isinstance(value, (tuple, list)):  # set voltage ramp
            # self.stair_sweep (value[0], value[1], dstep=None, stime=0.01, typ='V', stair='Lin')
            if len(self.stair_step_set) > 2:
                del self.stair_step_set[2]  # remove old values
            stair_set_args, stair_set_kwargs = self.stair_step_set[:2]
            stair_set_args[0] = value[0]
            stair_set_args[1] = value[1]
            if len(value) > 2:
                stair_set_args[2] = value[2]
                stair_set_kwargs["aperture_time"] = None
            else:
                stair_set_args[2] = None
                stair_set_kwargs["aperture_time"] = 0.0
            stair_set_kwargs["wait"] = True
            stair_set_kwargs["typ"] = stair_set_kwargs["typ"].replace("-", "")

            self.stair_step_get = self.stair_sweep(*stair_set_args, **stair_set_kwargs)
        else:
            logger.error("{!r}.voltage={} not possible, unknown format {}".format(self.instName, value, type(value)))

    @property
    def Voltage(self):
        """
        Get driver Voltage.

        Returns:
           value(float) : driver Voltage (in V).

        """
        value = self.ch[self.channel].voltage_level
        return value

    @property
    def current(self):
        """
        Get/set output current.

        If the current is set, the output is switched on immediately (if self.onAfterset == True).

        Args:
           value (float): set to current (in A).

        Returns:
           value (float): current (in A).

        """
        self.checkstate("running")
        value = self.ch[self.channel].measure(self.nidcpower.MeasurementTypes["CURRENT"])
        if self.compliance:
            logger.measure("{!r}.current == {}, Cmpl={}".format(self.instName, float(value), self.cmpl))
        else:
            logger.measure("{!r}.current == {}".format(self.instName, float(value)))
        return value

    @current.setter
    def current(self, value):
        if self.output_function != self.backend.OutputFunction.DC_CURRENT:
            self.output_function = self.backend.OutputFunction.DC_CURRENT
        self.ch[self.channel].current_level = value
        logger.measure("{!r}.current := {}".format(self.instName, float(value)))
        if self.onAfterset:
            self.onoff = 1

    @property
    def Current(self):
        """
        Get driver current.

        Returns:
           value (float): driver current (in A).

        """
        value = self.ch[self.channel].current_level
        return value

    # i_clamp and i_range:
    # inst.current_lmit:      max current in DC_voltage mode
    #      max values defined in inst.current_limit_range
    #
    # inst.current_level_autorange ON/OFF
    # inst.current_level_range   only in DC_CURRENT mode

    @property
    def i_clamp(self):
        """
        Set the current clamping (A), will adjust current measurement range.

        Current Limit Range and Current Limit are :
           * i_clamp 0.000001 A (int) / 1 µA = Limit +0.00000001 A to +0.000001 A (int) / +10 nA to +1 µA
           * i_clamp 0.00001 A (int) / 10 µA = Limit +0.0000001 A to +0.00001 A (int) / +100 nA to +10 µA
           * i_clamp 0.0001A (int) / 100 µA = Limit +0.000001 A to +0.0001 A (int) /  +1 µA to +100 µA
           * i_clamp 0.001 A (int) / 1 mA = Limit +0.00001 A to +0.001 A (int) / +10 µA to +1 mA
           * i_clamp 0.01 A (int) / 10 mA = Limit +0.0001 A to +0.01 A (int) / +100 µA to +10 mA
           * i_clamp 0.1 A (int) / 100 mA = Limit +0.001 A to +0.1 A (int) / +1 mA to +100 mA
           * i_clamp 1 A (int) / 1 A = Limit +0.01 A to +1 A (int) / +10 mA to +1 A
           * i_clamp 3 A (int) / 3 A = Limit +0.1 A to +3 A (int) / +100 mA to +3 A
           * i_clamp 10 A (int) / 10 A = Limit +0.1 A to +10 A pulsing only (int) / +100 mA to +10 A

        """
        # self.ch[self.channel].compliance_limit_symmetry=self.backend.ComplianceLimitSymmetry.SYMMETRIC
        limit = self.ch[self.channel].current_limit
        logger.measure("{!r}.i_clamp == {}A".format(self.instName, limit))
        return limit

    @i_clamp.setter
    def i_clamp(self, imax):  # imax in A
        if imax < 10.0e-9:
            imax = 10.0e-9
        # setting the current range, needs to enable the voltage source modus
        if self.output_function != self.backend.OutputFunction.DC_VOLTAGE:
            self.onoff = False
            self.output_function = self.backend.OutputFunction.DC_VOLTAGE
        oldstate = self._state
        if self.ch[self.channel].current_limit_autorange == 1:
            current_limit_range_old = self.ch[self.channel].current_limit_range
            self.checkstate("uncommitted")
            self.ch[self.channel].current_limit = imax
            if oldstate == self.State.running and self._runningmode == self.Runningmode.auto:
                self.initiate()
            if self.ch[self.channel].current_limit_range != current_limit_range_old:
                logger.info(
                    "{!r}.i_clamp {}A, i_range accomodating {}A from {}A".format(
                        self.instName, imax, self.ch[self.channel].current_limit_range, current_limit_range_old
                    )
                )
        else:
            self._i_clamp = imax
            i_range = self.i_range
            new_i_range = i_range
            if i_range > 100 * imax:
                # cannot have compliance (i_clamp) to less than 1% of range
                new_i_range = 10 ** (int(math.log10(imax)) + 1)
            elif i_range < imax:
                # cannot set compliance (i_clamp) to more than range
                new_i_range = imax
            if i_range != new_i_range:
                self._i_range = new_i_range
                self.checkstate("uncommitted")
                self.ch[self.channel].current_limit_range = new_i_range
                self.ch[self.channel].current_limit = imax
                if oldstate == self.State.running and self._runningmode == self.Runningmode.auto:
                    self.initiate()
                new_i_range = self.ch[self.channel].current_limit_range  # read back, instrument set limit_range to the next range value
                logger.info("{!r}.i_clamp {}A, i_range accomodating {}A from {}A".format(self.instName, imax, new_i_range, i_range))
            self.ch[self.channel].current_limit = imax
        logger.measure("{!r}.i_clamp := {}A".format(self.instName, imax))

    @property
    def i_range(self):
        """
        Set/Get the current range (A), will adjust current clamping.

        Current Value Range and Current Value are :
           * i_range 0.000001 A (int) / 1 µA = Value ±0.000001 A (int) /  ±1 µA
           * i_range 0.00001 A (int) / 10 µA = Value ±0.00001 A (int) / ±10 µA
           * i_range 0.0001 A (int) / 100 µA = Value ±0.0001 A (int) /  ±100 µA
           * i_range 0.001 A (int) / 1 mA = Value ±0.001 A (int) / ±1 mA
           * i_range 0.01 A (int) / 10 mA = Value ±0.01 A (int) / ±10 mA
           * i_range 0.1 A (int) / 100 mA = Value ±0.1 A (int) / ±100 mA
           * i_range 3 A (int) / 3 A = Value ±3 A (int) / ±3 A
           * i_range 10 A (int) / 10 A = Value ±10 A pulsing only (int) / ±10 A
        """
        val = self.ch[self.channel].current_level_range
        logger.measure("{!r}.i_range == {}A".format(self.instName, val))
        return val

    @i_range.setter
    def i_range(self, imax):
        """
        Set measure current range.

        parameter: imax (in A)
        """
        current_level_old = self.ch[self.channel].current_level
        if current_level_old > imax:
            self.ch[self.channel].current_level = imax
            logger.info("{!r}.i_range {}A, current accomodating {}A from {}A".format(self.instName, imax, imax, current_level_old))
        self.ch[self.channel].current_level_range = imax
        logger.measure("{!r}.i_range := {}A".format(self.instName, imax))

    @property
    def I_range(self):
        """
        Set/get current drive range.

        Returns
        -------
            val (float): current drive range (in A).

        """
        val = self.ch[self.channel].current_limit_range
        logger.measure("{!r}.I_range == {}A".format(self.instName, val))
        return val

    @I_range.setter
    def I_range(self, imax):  # imax in A
        self.ch[self.channel].current_limit_range = imax
        logger.measure("{!r}.I_range := {}A".format(self.instName, imax))

    # V_clamp and v_range:
    # inst.voltage_lmit:      max voltage in DC_currente mode
    #      max values defined in inst.voltage_limit_range
    #
    # inst.voltage_level_autorange ON/OFF
    # inst.voltage_level_range   only in DC_VOLTAGE mode
    @property
    def v_clamp(self):
        """
        Set the voltage clamping (V), will adjust voltage measurement range.

        Voltage Limit Range and Voltage Limit
           * v_clamp 0.6 V (int) / 600 mV = Limit +0.006 V to +0.6 V (int) / +6 mV to +600 mV
           * v_clamp 6 V (int) / 6 V = Limit +0.06 V to +6 V (int) / +60 mV to +6 V
           * v_clamp 60 V (int) / 60 V = Limit +0.6 V to +60 V (int) / +600 mV to +60 V

        """
        limit = self.ch[self.channel].voltage_limit
        logger.measure("{!r}.v_clamp == {}V".format(self.instName, limit))
        return limit

    @v_clamp.setter
    def v_clamp(self, vmax):
        if self.output_function != self.backend.OutputFunction.DC_CURRENT:
            self.onoff = False
            self.output_function = self.backend.OutputFunction.DC_CURRENT
        oldstate = self._state
        if self.ch[self.channel].voltage_limit_autorange == 1:
            voltage_limit_range_old = self.ch[self.channel].voltage_limit_range

            self.checkstate("uncommitted")
            self.ch[self.channel].voltage_limit = vmax
            if self.ch[self.channel].voltage_limit_range != voltage_limit_range_old:
                logger.info(
                    "{!r}.v_clamp {}V, v_range accomodating {}V from {}V".format(
                        self.instName, vmax, self.ch[self.channel].voltage_limit_range, voltage_limit_range_old
                    )
                )
        else:
            self._v_clamp = vmax
            v_range = self.v_range
            new_v_range = v_range
            if v_range > 100 * vmax:
                # cannot have compliance (v_clamp) to less than 1% of range
                new_v_range = 10 ** (int(math.log10(vmax)) + 1)
            elif v_range < vmax:
                # cannot set compliance (v_clamp) to more than range
                new_v_range = vmax
            if v_range != new_v_range:
                self._v_range = new_v_range
                self.checkstate("uncommitted")
                self.ch[self.channel].voltage_limit_range = new_v_range
                self.ch[self.channel].voltage_limit = vmax
                if oldstate == self.State.running and self._runningmode == self.Runningmode.auto:
                    self.initiate()
                new_v_range = self.ch[self.channel].voltage_limit_range  # read back, instrument set limit_range to the next range value
                logger.info("{!r}.v_clamp {}V, v_range accomodating {}V from {}V".format(self.instName, vmax, new_v_range, v_range))
            self.ch[self.channel].voltage_limit = vmax
        logger.measure("{!r}.v_clamp := {}V".format(self.instName, vmax))

    @property
    def v_range(self):
        """
        Set the voltage range, will adjust voltage clamping.

        Voltage Value Range and Voltage Value are:
           * PXIe4138:
              * v_range 0.6 V (int) / Value ±0.6 V
              * v_range 6 V   (int) / Value ±6 V
              * v_range 60 V  (int) / Value ±60 V
           * PXIe4141:
              * v_range 10.0 V (int) / Value ±10 V

        """
        val = self.ch[self.channel].voltage_level_range
        logger.measure("{!r}.v_range == {}V".format(self.instName, val))
        return val

    @v_range.setter
    def v_range(self, vmax):
        """
        Set voltage measure range.

        vmax in V
        """
        self.ch[self.channel].voltage_level_range = vmax
        logger.measure("{!r}.v_range := {}V".format(self.instName, vmax))

    @property
    def V_range(self):
        """Get/set voltage drive range."""
        val = self.ch[self.channel].voltage_limit_range
        logger.measure("{!r}.V_range == {}V".format(self.instName, val))
        return val

    @V_range.setter
    def V_range(self, vmax):  # vmax in V
        self.ch[self.channel].voltage_limit_range = vmax
        logger.measure("{!r}.V_range := {}V".format(self.instName, vmax))

    def stair_sweep(self, start, stop, dstep=None, stime=0, typ="V", stair="Lin", aperture_time=None, wait=True):
        """
        Make a stait sweep beetween start and stop.

        Parameters
        ----------
        start : float
            Start value in volts or amps.
        stop : TYPE
            Stop value in volts or amps.
        dstep : TYPE, optional
            Delta amplitude for Lin, Points to interpolate for Log, if "None" than take minimum dstep and stime= time for the whole sweep(=rising,falling time). The default is None.
        stime : TYPE, optional
            Delay between steps, if dstep='None' than stime is the whole time for the sweep (=rising,falling time). The default is 0.
        typ : TYPE, optional
            'V-', 'I-'  = Voltage / Current sourced, '-' changes direction,
            volts, amps, timestamp  are sensed. The default is 'V'.
        stair : TYPE, optional
            ('Lin','Log) = linear or log source. The default is 'Lin'.
        aperture_time : TYPE, optional
            Specifies the measurement aperture time for the channel configuration.
                   Aperture time is specified in the units set by aperture_time_units (default is seconds).
                   more help: http://zone.ni.com/reference/en-XX/help/370736U-01/nidcpowercref/nidcpower_attr_aperture_time/. The default is None.
        wait : TYPE, optional
            not implemented yet. The default is True.

        Returns
        -------
        TYPE
            original data from the instrument (Voltage, Current, Compliance).

        """
        self.sweepto = stop
        if start is not None and typ == "V":
            self.voltage = start
        elif start is not None and typ == "I":
            self.current = start
        args = [None, stop, dstep]
        kwargs = {"stime": stime, "typ": typ, "stair": stair, "aperture_time": aperture_time}
        self.stair_step_set = [args, kwargs]
        if start is None or str(start) == "?":
            start = self.ch[self.channel].voltage_level
            if start > stop and isinstance(dstep, (int, float)) and dstep > 0:
                dstep = -1.0 * dstep
        direction = "UP"
        steptime = stime
        if "-" in typ:
            direction = "DOWN"
            # start, stop = stop, start
            # dstep *= -1.0
        if stair.upper() == "LIN" and isinstance(dstep, (int, float)):
            if stop <= start and dstep > 0 or stop >= start and dstep < 0 or dstep == 0:
                return
            if (stop - start) / dstep <= 1.0:
                dstep = (stop - start) / 1.0
                logger.debug("{!r} dstep adjusted to {} on this sweep".format(self.instName, dstep))
            pts = int((stop - start) / dstep + 1)
        elif isinstance(dstep, (int, float)):
            pts = dstep + 1
            logger.error("{!r} stair_sweep: stair=log not yet implemented, please ask for implementation".format(self.instName))
            return
        else:  # dstep=None -> calculate points from stime
            pts = round(stime / self._stair_delay * 1e6)
            if pts > self.ch[self.channel].measure_buffer_size:  # pts should be < maximum points
                pts = self.ch[self.channel].measure_buffer_size
            steptime = 0
            pts += 1
        if pts < 2:
            pts = 2
        # calculate points:
        value_pts = []
        delay_pts = []
        if direction == "UP":
            delta = (stop - start) / (pts - 1)
            first = start
            last = stop
        else:
            delta = (start - stop) / (pts - 1)
            first = stop
            last = start
        for i in range(pts):  # create ramp with voltage and time
            value_pts.append(first + i * delta)
            delay_pts.append(float(steptime))
        if len(self.stair_step_set) != 3:
            self.stair_step_set.append({"value": value_pts, "delay": delay_pts})
        else:
            self.stair_step_set[2] = [{"value": value_pts, "delay": delay_pts}]
        if self._state == self.State.running:
            self.abort()
        if (
            self.inst.channel_count > 1
        ):  # workaround for PXIe4141 lmitation: Source Mode must be configured to Single Point when multiple channels are present in the same session.
            setup_attr = []
            for attr in self._properties:  # create list for all values which are rescuing
                setup_attr.append(self._properties[attr][0])
            setup_attr += ["power_line_frequency", "dc_noise_rejection"]
            lastsetup = {}
            for i in self.channels:
                lastsetup.update({i: {}})
                for attr in setup_attr:
                    value = getattr(self.inst.channels[i], attr)
                    lastsetup[i].update({attr: value})
            self.close_session()
            self.reopen_session(self.channel)  # create session only for current channel
            for attr in lastsetup[self.channel]:
                setattr(self.inst, attr, lastsetup[self.channel][attr])  # set all attributes for current channel again
            resume = True
        else:
            resume = False
        if "V" in typ:
            self.output_function = self.backend.OutputFunction.DC_VOLTAGE
        elif "I" in typ:
            self.output_function = self.backend.OutputFunction.DC_CURRENT
        if dstep is None:
            self.ch[self.channel].aperture_time = 0
            self.ch[self.channel].source_delay = 0
        else:
            if aperture_time is not None:
                self.ch[self.channel].aperture_time = aperture_time
        if self.ch[self.channel].aperture_time_units == self.nidcpower.ApertureTimeUnits.POWER_LINE_CYCLES:
            timeout = self.ch[self.channel].aperture_time * 0.02 * pts
        else:
            timeout = self.ch[self.channel].aperture_time * pts
        if steptime == 0:
            timeout += self._stair_delay * 1e-6 * pts
        else:
            timeout += steptime * pts
        self.inst.source_mode = self.nidcpower.SourceMode["SEQUENCE"]
        self.inst.set_sequence(value_pts, delay_pts)
        self.initiate()
        if not wait:
            # self.ch[self.channel].measure_when = nidcpower.MeasureWhen.AUTOMATICALLY_AFTER_SOURCE_COMPLETE
            logger.error("{!r} stair_sweep: wait=false not yet implemented, please ask for implementation".format(self.instName))
        if True:
            self.stair_measure = self.inst.fetch_multiple(len(value_pts), timeout=timeout)
            self.abort()
            if resume:
                self.close_session()
                self.reopen_session(self.channels)
                for i in self.channels:  # write back value which are rescue
                    for attr in lastsetup[self.channel]:
                        setattr(self.inst.channels[i], attr, lastsetup[self.channel][attr])  # set all attributes for all channel again
            else:
                self.inst.source_mode = self.nidcpower.SourceMode["SINGLE_POINT"]
            if "V" in typ:
                self.ch[self.channel].voltage_level = float(last)
            else:
                self.ch[self.channel].current_level = float(last)
            self.initiate()
            return self.stair_measure

    def get_values(self, typ=""):
        """
        Get response of previous stair_sweep(), choosing result rows from previous request typ.

        get info about calculated divergence to target sweep values, for checking ramping time is ok
        Transfer last requested measurement sweep results

        Parameters
        ----------
        typ : TYPE, could be 'VITS'
              V = Voltage
              I = current
              T = time
              S = status(compliance)
              The default is ''.

        Returns
        -------
        TYPE
            numpy array from the values.

        """
        measure = np.array(self.stair_measure)
        cnt_cmpl = measure[0:, 2].sum()
        if cnt_cmpl > 0.0:
            logger.warning("{!r}.get_values: found Compliance ({}x) in measurement".format(self.instName, cnt_cmpl))
        divergence_array = measure[0:, 0] - np.array(self.stair_step_set[2]["value"])
        dmax = divergence_array.max()
        dmin = divergence_array.min()
        divergence = max([dmax, dmin], key=abs)
        if divergence == dmax:
            index = divergence_array.argmax()
        else:
            index = divergence_array.argmin()
        logger.info(
            "{} stair_sweep divergence = {}V, @ set Voltage = {}, measure = {} V, {} A, cmp = {}".format(
                self.instName, divergence, self.stair_step_set[2]["value"][index], measure[index][0], measure[index][1], measure[index][2]
            )
        )
        index = []
        if "V" in typ.upper():
            index += [0]
        if "I" in typ.upper():
            index += [1]
        if "T" in typ.upper():
            logger.error("{!r} get_value: typ 't' not yet implemented, please ask for implementation".format(self.instName))
        if "S" in typ.upper():
            index += [2]
        return measure[0:, index]

    @property
    def stair_step(self):
        """stair_step to target or target, dstep or target, dstep,stime, using previous stair_sweep() parameters."""
        return self.stair_step_get

    @stair_step.setter
    def stair_step(self, stair_set):
        if not type(stair_set) in [type(tuple()), type(list())]:
            stair_set_args, stair_set_kwargs = self.stair_step_set[:2]
            stair_set_args[0] = None
            stair_set_args[1] = stair_set
            stair_set_kwargs["wait"] = False
            stair_set_kwargs["typ"] = stair_set_kwargs["typ"].replace("-", "")
            self.stair_step_get = self.stair_sweep(*stair_set_args, **stair_set_kwargs)
        else:
            if len(stair_set) == 2:
                stair_set_args, stair_set_kwargs = self.stair_step_set[:2]
                stair_set_args[0] = None
                stair_set_args[1] = stair_set[0]
                stair_set_args[2] = stair_set[1]
                stair_set_kwargs["wait"] = False
                stair_set_kwargs["typ"] = stair_set_kwargs["typ"].replace("-", "")
                self.stair_step_get = self.stair_sweep(*stair_set_args, **stair_set_kwargs)
            if len(stair_set) == 3:
                stair_set_args, stair_set_kwargs = self.stair_step_set[:2]
                stair_set_args[0] = None
                stair_set_args[1] = stair_set[0]
                stair_set_args[2] = stair_set[1]
                stair_set_kwargs["wait"] = False
                stair_set_kwargs["stime"] = stair_set[2]
                stair_set_kwargs["typ"] = stair_set_kwargs["typ"].replace("-", "")
                self.stair_step_get = self.stair_sweep(*stair_set_args, **stair_set_kwargs)

    @property
    def stair_slope(self):
        """stair_slope to target or target,slope_time using previous stair_sweep() parameters."""
        return self.stair_step_get

    @stair_slope.setter
    def stair_slope(self, stair_set):
        if not type(stair_set) in [type(tuple()), type(list())]:
            stair_set_args, stair_set_kwargs = self.stair_step_set[:2]
            stair_set_args[0] = None
            stair_set_args[1] = stair_set
            stair_set_args[2] = None
            stair_set_kwargs["wait"] = False
            stair_set_kwargs["typ"] = stair_set_kwargs["typ"].replace("-", "")
            self.stair_step_get = self.stair_sweep(*stair_set_args, **stair_set_kwargs)
        else:
            stair_set_args, stair_set_kwargs = self.stair_step_set[:2]
            stair_set_args[0] = None
            stair_set_args[1] = stair_set[0]
            stair_set_args[2] = None
            stair_set_kwargs["stime"] = stair_set[1]
            stair_set_kwargs["wait"] = False
            stair_set_kwargs["typ"] = stair_set_kwargs["typ"].replace("-", "")
            self.stair_step_get = self.stair_sweep(*stair_set_args, **stair_set_kwargs)

    @property
    def stime(self):
        """
        Set/get delay between steps.

        if dstep='None' than stime is the whole time for the sweep (=rising or falling time).
        """
        stair_set_args, stair_set_kwargs = self.stair_step_set[:2]
        if "stime" not in stair_set_kwargs:
            return 0
        return stair_set_kwargs["stime"]

    @stime.setter
    def stime(self, value):
        stair_set_args, stair_set_kwargs = self.stair_step_set[:2]
        stair_set_kwargs["stime"] = value
        self.stair_step_set = [stair_set_args, stair_set_kwargs]

    def list_PXIdevices(self):
        """
        List all PXIe devices.

        but it's not running correcly....
        how can we make a list from all devices on PXIe ?
        """
        import pyvisa

        rm = pyvisa.ResourceManager()
        rm.list_resources()
        # ('PXI11::13::INSTR', 'ASRL1::INSTR', 'ASRL3::INSTR', 'ASRL5::INSTR', 'ASRL7::INSTR', 'ASRL8::INSTR')
        #    PCI-Buss 11, PCI-Geraet 13
        #  -> list only PXI11::13::INSTR  PXISLOT6    ??
        # {'PXI11::13::INSTR': ResourceInfo(interface_type=<InterfaceType.pxi: 5>, interface_board_number=11, resource_class='INSTR',
        #   resource_name='PXI11::13::0::INSTR', alias='PXI1Slot6'),
        #                                     in NIMAX:
        #                                                PXI0::1::BACKPLANE"
        #                                                and more....
        for resource in rm.list_resources():
            print(resource)
            # rm.opten_resource(resource)
            # print (resource.model_name
        rm.close()
        # blind-scan.... but found only dcpower devices :-(
        for i in range(0, 10):
            try:
                resource = self.nidcpower.Session(resource_name="PXI1Slot" + str(i))
            except Exception:
                continue
            print("PXI1Slot{}     {}    {}".format(i, resource.instrument_model, resource.instrument_manufacturer))
            resource.close()

    def smu_fetch_settings(self, record_length=5_000_000, aperture_time=0.001):
        self.inst.measure_when = self.nidcpower.enums.MeasureWhen.ON_MEASURE_TRIGGER
        self.inst.measure_trigger_type = self.nidcpower.enums.TriggerType.SOFTWARE_EDGE
        self.inst.measure_buffer_size = record_length
        self.inst.measure_record_length = record_length
        self.inst.aperture_time = aperture_time

    def fetch_data(self, npoints, measure="voltage"):
        start_time = time.time()
        self.inst.send_software_edge_trigger(self.nidcpower.enums.SendSoftwareEdgeTriggerType.MEASURE)
        temp = self.inst.fetch_multiple(npoints, timeout=hightime.timedelta(seconds=20))
        total_time = time.time() - start_time
        time_array = np.linspace(0, total_time, npoints)
        time_pts = time_array.tolist()
        voltage = []
        current = []

        if measure == "voltage":
            for i in range(0, npoints):
                voltage.append(temp[i].voltage)
            return time_pts, voltage
        elif measure == "current":
            for i in range(0, npoints):
                current.append(abs(temp[i].current * 1000))
            return time_pts, current
        elif measure == "both":
            for i in range(0, npoints):
                voltage.append(temp[i].voltage)
                current.append(abs(temp[i].current * 1000))
            return time_pts, voltage, current

    def plot_smu_data(self, time, voltage=None, current=None):
        if (voltage is not None) and (current is not None):
            plt.figure(figsize=(6.4, 4.8), dpi=300)
            plt.title("SMU Measurements")
            plt.subplot(2, 1, 1)
            plt.plot(time, voltage, "ro", markersize=0.1, alpha=0.1)
            plt.ylabel("Voltage (V)")
            plt.grid(linestyle="--")

            plt.subplot(2, 1, 2)
            plt.plot(time, current, "go", markersize=0.1, alpha=0.1)
            plt.xlabel("Time (s)")
            plt.ylabel("Current (mA)")
            plt.grid(linestyle="--")

        else:
            plt.figure(figsize=(6.4, 4.8), dpi=300)
            if voltage != None:
                plt.plot(time, voltage, "ro", markersize=0.1, alpha=0.1)
                plt.ylabel("Voltage (V)")
            elif current != None:
                plt.plot(time, current, "go", markersize=0.1, alpha=0.1)
                plt.ylabel("Current (mA)")
            plt.xlabel("Time (s)")
            plt.title("SMU Measurements")
            plt.grid(linestyle="--")

        plt.show()


# ---------------------------


if __name__ == "__main__":
    from pylab_ml.base_instrument import logsetup

    logsetup()

    vdd = PXIe41xx(addr="PXI1Slot2", instName="vdd")
    # vdd.list_PXIdevices()
    # vdd.init()

    # vdd.smu_fetch_settings(record_length=30_000, aperture_time=0.001)
    #vdd.initiate()
    #time_pts, voltage, current = vdd.fetch_data(30_000, "both")
    #vdd.plot_smu_data(time_pts, voltage, current)
    #vdd.abort()

    # # print(vdd.selftest)
    # vdd.auto_zero
    # vdd.aperture_time
    # vdd.auto_zero = "OFF"

    # vdd.on()
    # logger.info(vdd.state)
    # vdd.voltage = 0.5
    # vdd.v_range = 0.6
    # current = vdd.current
    # logger.info("current= {} mA".format(current * 1000))
    # logger.info(vdd.state)
    # vdd.onoff = 0
    # vdd.onoff = 1
    # vdd.v_range = 6
    # vdd.voltage = 2

    # vdd.current = 0.000001
    # vdd.i_range = 0.0001
    # vdd.v_clamp = 10
    # logger.info(vdd.current)
    # logger.info(vdd.voltage)

    vdd.stair_sweep(0, 5, dstep=None, stime=1.00)
    # vdd.stair_sweep(0, 5, dstep=None, stime=1, typ="V-", stair="Lin")
    # vdd.stair_sweep(0, 5, dstep=None, stime=0.1, typ="V", stair="Lin", aperture_time=0.1, wait=False)

    # vdd.i_clamp = 0.005
    # vdd.i_range = 0.1

    # logger.info("sense={}".format(vdd.sense))
    # vdd.sense = "REMOTE"
    # logger.info("sense={}".format(vdd.sense))
    # vdd.sense = "LOCAL"

    # logger.info(vdd.dc_noise_rejection)
    # logger.info(vdd.aperture_time_units)
    # logger.info(vdd.auto_zero)

    # vdd.voltage = 0, 4  # sweep from 0 to 4V with min rise time
    # vdd_voltage = vdd.get_values("v")
    # vdd_current = vdd.get_values("v")
    # vdd_sense = vdd.get_values("s")

    # vdd.time = 0.0005  # set rise/fall time to 500us
    # vdd.voltage = 0
    # vdd.voltage = 0, 4.2  # sweep from 0 to 4.2V with 500us rise time

    # vdd.time = 0.01  # set rise/fall time to 10ms
    # vdd.voltage = 0
    # vdd.voltage = 0, 4.8  # sweep from 0 to 4.8V with 10ms rise time

    # vdd.time = 0.001
    # vdd.voltage = 0
    # # vdd.voltage=0, 5, 3     # set some nodes,  min rise/fall time,  delay=500us

    # # vdd.time = [0.0005, 0.001, 0.003, 0.001, 0.005, 0.001]      #define delay for each node
    # # vdd.voltage=0, 5, 4.3, 2.1, 5, 0

    # vdd.voltage = 3

    # vdd.off()
    vdd.close()
