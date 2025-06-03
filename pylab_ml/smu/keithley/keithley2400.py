"""Interface to the Power-Measuremet-Unit (SMU) Keithley2400.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>

"""
import re
import numpy as np
import math
from pylab_ml.base_instrument import logger
from pylab_ml.collate_instrument import Interface
from pylab_ml.smu.keithley.base_keithley import Keithley


class Keithley2400(Keithley):
    """Interface to the Power-Measuremet-Unit (SMU) Keithley2400.

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    .. image:: ../static/kethley2400.jpg

    The Keithley2400 can
    source and sink power in all four voltage/current quadrants and
    measure voltage and current precisely

    """

    interchoices = [Interface.usbserial, Interface.gpib]

    def __init__(self, addr=None, interface=None, backend=None, identify=True, instName=None):
        """Connect and initialize.

        Args:
           addr (int):
              interface address
           interface (Interface):
              gpib, usbserial

           backend (str):
              visa backend is either '@ni' for NI-Library or
              '@py' for pure python pyvisa-py backend.
              On default it uses '@ni' on win32 and '@py' on
              other platforms.
           instName (string):
              Instance Name from parent.

        Example: Initialization
           >>> vdd = Keithley2400(addr=24)  # GPIB or USB address
           >>>                              #  validate displayed message Id on device
           >>> vdd.init()                   # connect and initialize instrument

        Example: Voltage source
            >>> vdd.i_clamp = 0.01           # current protection
            >>> vdd.voltage = 3.3            # set output voltage
            >>> i = vdd.current              # measure (supply) current

        Example: Current source
            >>> vdd.v_clamp = 5              # voltage protection
            >>> vdd.current = 0.1            # set output current_range
            >>> v = vdd.voltage              # measure voltage

        """
        kwargs = {"addr": addr, "interface": interface, "backend": backend, "identify": identify, "instName": instName}
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
        self.msg_row_col = (1, 20)

    def setup_inst(self):
        """Start setup instrument settings, called from class instruments."""
        super().setup_inst()
        self.mqtt_all = ['id', 'output_function', 'onoff', 'voltage', 'current', 'Voltage', 'Current', 'v_autorange', 'i_autorange',
                         'V_autorange', 'I_autorange', 'v_clamp', 'i_clamp', 'v_range', 'i_range', 'V_range', 'I_range']
        if self.inst:
            if self.interface == Interface.gpib:
                self.inst.read_termination = '\n'
                self.inst.write_termination = '\n'
            else:
                self.inst.read_termination = '\r'
                self.inst.write_termination = '\r'
        self._measure = "vir"
        self._nplc = 0.1
        self._i_clamp = 105e-6                  # max current (A) set to reset value=100uA
        self._i_range = 105e-6                  # current range (A) set to 100uA
        self._v_clamp = 21.0
        self._v_range = 21.0
        self.inst.write(':SOUR:VOLT:PROT:LEV 20')
        self.stair_step_set = [[0, 0, 0.1], {"typ": "V"}]
        self.stair_step_get = np.array([])
        self.stair_measure = ""

    def on(self):
        """Reactivate outputs."""
        self.budget.set_slack(self)
        self.inst.write(':OUTP ON')

    def off(self):
        """Deactivate outputs."""
        self.budget.set_slack(self)
        self.inst.write(':OUTP OFF')

    @property
    def onoff(self):
        """Set/get on state (True)."""
        self.budget.set_slack(self)
        result = int(self.inst.query(':OUTPUT:STATE?')) == 1
        return (result)

    @onoff.setter
    def onoff(self, value):
        if value:
            self.on()
        else:
            self.off()

    @property
    def output_function(self):
        self.budget.set_slack(self)
        if self.inst.query(':SOURce:FUNCtion:MODE?') == 'VOLT':
            return 'DC_VOLTAGE'
        elif self.inst.output_function.name == 'CURR':
            return 'DC_CURRENT'
        else:
            return self.inst.output_function.name

    @property
    def measure(self):
        """Get or set measure.

        where the measurements are defined by "vir" flags (VOLTAGE,CURRENT,RESISTANCE)

        """
        if not self.onoff:
            return
        self.budget.set_slack(self)
        form = ""
        sense = ""
        formS = " "
        senseS = " "
        # measv = False
        # measi = False
        measr = False
        if "v" in self._measure:
            form += formS + 'VOLT'
            sense += senseS + '"VOLT:DC"'
            formS = ","
            senseS = ","
            # measv = True
        if "i" in self._measure:
            form += formS + 'CURR'
            sense += senseS + '"CURR:DC"'
            formS = ","
            senseS = ","
            # measi = True
        if "r" in self._measure:
            form += formS + 'RES'
            sense += senseS + '"RES"'
            formS = ","
            senseS = ","
            measr = True
        senses = sense.split(",")
        lnf = len(senses)
        if lnf <= 0:
            self.budget.set_slack(self)
            return ([])
        self.budget.set_slack(self, lnf * 0.2)
        self.inst.write(':SENS:FUNC:CONC ON')
        if sense != "":
            self.inst.write(':SENS:FUNC {}'.format(sense))
        if measr:
            self.inst.write(':SENS:RES:MODE MAN')
        self.inst.write(':TRIG:COUN 1')
        if form != "":
            self.inst.write(':FORM:ELEM {}'.format(form))
        elements = self.inst.query(':FORM:ELEM?').split(",")
        logger.info("{!r} measure returns {}".format(self.instName, elements))
        lne = len(elements)
        if lne > 0:
            value = self.inst.query(':READ?')
            res = [float(i) for i in value.split(",")]
            logger.measure("{!r} {} == {}".format(self.instName, elements, res))
            self.budget.set_slack(self)
            return (res)
        else:
            self.budget.set_slack(self)
            return ([])

    @measure.setter
    def measure(self, typ="vir"):
        self._measure = typ

    @property
    def voltage(self):
        """Get or set output voltage.

        If the voltage is set the output is switched on immediately.
        """
        self.budget.set_slack(self)
        if not self.onoff:
            return
        self.inst.write(':SENS:FUNC "VOLT"')
        self.inst.write(':TRIG:COUN 1')
        self.inst.write(':FORM:ELEM VOLT')
        value = self.inst.query(':READ?')
        logger.measure("{!r} voltage == {}".format(self.instName, float(value)))
        return float(value)

    @voltage.setter
    def voltage(self, value):
        self.budget.set_slack(self)
        self.inst.write(':SOUR:FUNC VOLT')
        self.inst.write(':SOUR:VOLT:MODE FIXED')
        # self.inst.write(':SOUR:VOLT:RANG {}'.format(1.1*value))
        self.inst.write(':SOUR:VOLT:LEV {}'.format(value))
        self._Voltage = value
        logger.measure("{!r} voltage := {}".format(self.instName, float(value)))
        self.onoff = True
        if self.is_local:
            self.voltage

    @property
    def Voltage(self):
        """
        Get driver Voltage.

        Returns:
           value(float) : driver Voltage (in V).

        """
        value = self._Voltage
        return value

    @property
    def current(self):
        """Get or set output current.

        If the current is set the output is switched on immediately.
        """
        self.budget.set_slack(self)
        if not self.onoff:
            return
        self.inst.write(':SENS:FUNC "CURR"')
        self.inst.write(':TRIG:COUN 1')
        self.inst.write(':FORM:ELEM CURR')
        value = self.inst.query(':READ?')
        logger.measure("{!r} current == {}".format(self.instName, float(value)))
        return float(value)

    @current.setter
    def current(self, value):
        self.budget.set_slack(self)
        self.inst.write(':SOUR:FUNC CURR')
        self.inst.write(':SOUR:CURR:MODE FIXED')
        # self.inst.write(':SOUR:CURR:RANG {}'.format(1.1*value))
        self.inst.write(':SOUR:CURR:LEV {}'.format(value))
        logger.measure("{!r} current := {}".format(self.instName, float(value)))
        self.onoff = True
        if self.is_local:
            self.current

    @property
    def nplc(self):
        """Set the conversion number of power line cycles accuracy, for all converters.

        for a plc of 1.0, conversion rate is 1/50s = 20ms. Accuracy max 10, min 0.01
        """
        self.budget.set_slack(self)
        val = self.inst.query(':SENS:VOLT:NPLC?')
        return float(val)

    @nplc.setter
    def nplc(self, cycles):            # cycles are number of power line cycles for conversion
        self._nplc = cycles
        self.budget.set_slack(self)
        # in Keithley 2400 each measurement (v,i,r) is common accuracy
        self.inst.write(':SENS:VOLT:NPLC {}'.format(cycles))
        # so implicitly self.inst.write(':SENS:CURR:NPLC {}'.format(cycles))

    @property
    def v_autorange(self):
        """Autorange voltage measurement on or off."""
        self.budget.set_slack(self)
        res = self.inst.query(':SENS:VOLT:RANG:AUTO?')
        return (float(res) != 0)

    @v_autorange.setter
    def v_autorange(self, on):
        self.budget.set_slack(self)
        if on:
            self.inst.write(':SENS:VOLT:RANG:AUTO ON')
        else:
            self.inst.write(':SENS:VOLT:RANG:AUTO OFF')

    @property
    def i_autorange(self):
        """Autorange current measurement on or off."""
        self.budget.set_slack(self)
        res = self.inst.query(':SENS:CURR:RANG:AUTO?')
        return (float(res) != 0)

    @i_autorange.setter
    def i_autorange(self, on):
        self.budget.set_slack(self)
        if on:
            self.inst.write(':SENS:CURR:RANG:AUTO ON')
        else:
            self.inst.write(':SENS:CURR:RANG:AUTO OFF')

    @property
    def V_autorange(self):
        """Autorange drive voltage on or off."""
        self.budget.set_slack(self)
        res = self.inst.query(':SOUR:VOLT:RANG:AUTO?')
        return (float(res) != 0)

    @V_autorange.setter
    def V_autorange(self, on):
        self.budget.set_slack(self)
        if on:
            self.inst.write(':SOUR:VOLT:RANG:AUTO ON')
        else:
            self.inst.write(':SOUR:VOLT:RANG:AUTO OFF')

    @property
    def I_autorange(self):
        """Autorange drive current on or off."""
        self.budget.set_slack(self)
        res = self.inst.query(':SOUR:CURR:RANG:AUTO?')
        return (float(res) != 0)

    @I_autorange.setter
    def I_autorange(self, on):
        self.budget.set_slack(self)
        if on:
            self.inst.write(':SOUR:CURR:RANG:AUTO ON')
        else:
            self.inst.write(':SOUR:CURR:RANG:AUTO OFF')

    @property
    def I_range(self):
        """Set the current drive range (A)."""
        self.budget.set_slack(self)
        val = float(self.inst.query(':SOUR:CURR:RANG?'))
        return val

    @I_range.setter
    def I_range(self, imax):            # imax in A
        self._I_range = imax
        self.budget.set_slack(self)
        self.inst.write(':SOUR:CURR:RANG {}'.format(imax))
        logger.info("{!r} I_range {}A".format(self.instName, imax))

    @property
    def V_range(self):
        """Set the voltage drive range (V)."""
        self.budget.set_slack(self)
        val = float(self.inst.query(':SOUR:VOLT:RANG?'))
        return val

    @V_range.setter
    def V_range(self, vmax):            # vmax in V
        self._V_range = vmax
        self.budget.set_slack(self)
        self.inst.write(':SOUR:VOLT:RANG {}'.format(vmax))
        logger.info("{!r} V_range {}V".format(self.instName, vmax))

    @property
    def i_clamp(self):
        """Set the current clamping (A), will adjust current measurement range."""
        self.budget.set_slack(self)
        limit = float(self.inst.query(':SENS:CURR:PROT?'))
        return limit

    @i_clamp.setter
    def i_clamp(self, imax):            # imax in A
        self._i_clamp = imax
        i_range = self.i_range
        new_i_range = i_range
        self.budget.set_slack(self)
        self.inst.write(':SENS:CURR:PROT {}'.format(imax))
        # setting the current range needs to enable the voltage source modus
        self.inst.write(':SOUR:FUNC VOLT')
        if i_range > 100 * imax:
            # cannot have compliance (i_clamp) to less than 1% of range
            new_i_range = 100 * imax
        elif i_range < imax:
            # cannot set compliance (i_clamp) to more than range
            new_i_range = imax
        if i_range != new_i_range:
            logger.warning("{!r} i_clamp {}A, i_range accomodating {}A from {}A".format(self.instName, imax, new_i_range, i_range))
            self._i_range = new_i_range
            self.inst.write(':SENS:CURR:RANG {}'.format(new_i_range))
        else:
            logger.info("{!r} i_clamp {}A".format(self.instName, imax))

    @property
    def i_range(self):
        """Set the current measurement range (A), will adjust current clamping."""
        self.budget.set_slack(self)
        val = float(self.inst.query(':SENS:CURR:RANG?'))
        return val

    @i_range.setter
    def i_range(self, imax):            # imax in A
        self._i_range = imax
        i_clamp = self.i_clamp
        new_i_clamp = i_clamp
        if imax / 100 > i_clamp:
            # cannot have compliance (i_clamp) to less than 1% of range
            new_i_clamp = imax / 100
        elif i_clamp > imax:
            # cannot set compliance (i_clamp) to more than range
            new_i_clamp = imax
        self.budget.set_slack(self)
        self.inst.write(':SENS:CURR:RANG {}'.format(imax))
        if i_clamp != self._i_clamp:
            logger.warning("{!r} i_range {}A, i_clamp accomodating {}A from {}A".format(self.instName, imax, new_i_clamp, i_clamp))
            self.i_clamp = i_clamp
        else:
            logger.info("{!r} i_range {}A".format(self.instName, imax))

    @property
    def v_clamp(self):
        """Set the voltage clamping (V), will adjust voltage measurement range."""
        self.budget.set_slack(self)
        limit = float(self.inst.query(':SENS:VOLT:PROT?'))
        return limit

    @v_clamp.setter
    def v_clamp(self, vmax):
        self._v_clamp = vmax
        v_range = self.v_range
        new_v_range = v_range
        self.budget.set_slack(self)
        self.inst.write(':SENS:VOLT:PROT {}'.format(vmax))
        # setting the voltage range needs to enable the current source modus
        self.inst.write(':SOUR:FUNC CURR')
        if v_range > 100 * vmax:
            # cannot have compliance (v_clamp) to less than 1% of range
            new_v_range = 100 * vmax
        elif v_range < vmax:
            # cannot set compliance (v_clamp) to more than range
            new_v_range = vmax
        if v_range != new_v_range:
            logger.warning("{!r} v_clamp {}V. v_range accomodating {}V from {}V".format(self.instName, vmax, new_v_range, v_range))
            self._v_range = new_v_range
            self.inst.write(':SENS:VOLT:RANG {}'.format(new_v_range))
        else:
            logger.info("{!r} v_clamp {}V".format(self.instName, vmax))

    @property
    def v_range(self):
        """Set the voltage measurement range, will adjust voltage clamping."""
        self.budget.set_slack(self)
        val = float(self.inst.query(':SENS:VOLT:RANG?'))
        return val

    @v_range.setter
    def v_range(self, vmax):            # vmax in V
        self._v_range = vmax
        v_clamp = self.v_clamp
        new_v_clamp = v_clamp
        if (vmax / 100) > v_clamp:
            # cannot have compliance (v_clamp) to less than 1% of range
            new_v_clamp = vmax / 100
        elif v_clamp > vmax:
            # cannot set compliance (v_clamp) to more than range
            new_v_clamp = vmax
        self.budget.set_slack(self)
        self.inst.write(':SENS:VOLT:RANG {}'.format(vmax))
        if v_clamp != new_v_clamp:
            logger.warning("{!r} v_range {}V, v_clamp accomodating {}V from {}V".format(self.instName, vmax, new_v_clamp, v_clamp))
            self.v_clamp = new_v_clamp
        else:
            logger.info("{!r} v_range {}V".format(self.instName, vmax))

    @property
    def v_protection(self):
        """Set the voltage protection limit|default|min|max, get 4 value tuple."""
        self.budget.set_slack(self)
        lim = self.inst.query(':SOUR:VOLT:PROT:LEV?')
        lim_def = self.inst.query(':SOUR:VOLT:PROT:LEV? DEF')
        lim_min = self.inst.query(':SOUR:VOLT:PROT:LEV? MIN')
        lim_max = self.inst.query(':SOUR:VOLT:PROT:LEV? MAX')
        return ((float(lim), float(lim_def), float(lim_min), float(lim_max)))

    @v_protection.setter
    def v_protection(self, lim):
        self.budget.set_slack(self)
        if re.match("def.*", str(lim), re.I):
            lim = "DEF"
        elif re.match("min.*", str(lim), re.I):
            lim = "MIN"
        elif re.match("max.*", str(lim), re.I):
            lim = "MAX"
        self.inst.write(':SOUR:VOLT:PROT:LEV {}'.format(lim))

    def stair_sweep(self, start, stop, dstep, stime=0, typ='V', stair='Lin', wait=False):
        """Sweep V or I, measure v,i,r at time t with state s, change by dstep, steptime stime, wait for response.

        if dstep is None then stime is slopetime (>1ms) & nplc is min : 0.01

           typ:    'Vvirts-', 'Ivirts-'  = Voltage / Current sourced, '-' changes direction,
                   volts, amps, ohms, timestamp, status are sensed
           start:  Start value in volts or amps, None implies incremental
           stop:   Stop value in volts or amps
           dstep:  Delta amplitude for Lin, Points to interpolate for Log, stime is slope time for None (>1ms)
           stime:  Delay between steps or slope time if dstep == None
           stair:  ('Lin','Log) = linear or log source

        """
        args = [None, stop, dstep]
        kwargs = {'stime': stime, 'typ': typ, 'stair': stair}
        self.stair_step_set = [args, kwargs]
        self.budget.set_slack(self)
        form = ""
        sense = ""
        measure = ""
        formS = ""
        senseS = ""
        measv = False
        measi = False
        measr = False
        if "v" in typ:
            form += formS + 'VOLT'
            sense += senseS + '"VOLT:DC"'
            formS = ","
            senseS = ","
            measv = True
            measure += "v"
        if "i" in typ:
            form += formS + 'CURR'
            sense += senseS + '"CURR:DC"'
            formS = ","
            senseS = ","
            measi = True
            measure += "i"
        if "r" in typ:
            form += formS + 'RES'
            sense += senseS + '"RES"'
            formS = ","
            senseS = ","
            measr = True
            measure += "r"
        if "t" in typ:
            form += formS + 'TIME'
            formS = ","
            measure += "t"
        if "s" in typ:
            form += formS + 'STAT'
            formS = ","
            measure += "t"
        if start is None or str(start) == '?':
            start = self.voltage
            if start is None:
                start = 0
                logger.warning("{!r} initial start assumed to be 0".format(self.instName))
            if dstep is not None:
                if start > stop and dstep > 0:
                    dstep = -1.0 * dstep
        direction = "UP"
        final = stop
        if "-" in typ:
            direction = "DOWN"
            final = start
        if dstep is None:
            # stime is slope time
            # No measurement
            # 1001 points for 10V == 805ms
            # 1001 points for 1V == 805ms
            # 101 points for 1V == 81ms
            # 11 points for 1V == 8.2ms
            # V measurement, nplc = 0.01
            # 1001 points for 10V == 1300ms
            # 1001 points for 1V == 1300ms
            # 101 points for 1V == 132ms
            # 11 points for 1V == 13.6ms
            # I measurement, nplc = 0.01
            # 1001 points for 10V == 1480ms
            # 1001 points for 1V == 1440ms
            # 101 points for 1V == 142ms
            # 11 points for 1V == 14.6ms
            # VI (+R) measurement, nplc = 0.01
            # 1001 points for 10V == 2680ms
            # 1001 points for 1V == 2625ms
            # 101 points for 1V == 265ms
            # 11 points for 1V == 27ms
            # R measurement, nplc = 0.01
            # 101 points for 1V == 150ms
            nplc = 0.01
            rang = abs(stop - start)
            max_pts = int(math.log(rang + 1.05) * 50)
            if measv and measi or measv and measr or measi and measr:
                meas_cost = 2.66e-3
            elif measv:
                meas_cost = 1.33e-3
            elif measi or measr:
                meas_cost = 1.45e-3
            else:
                meas_cost = 0.8e-3
            meas_pts = int(stime / meas_cost) + 2
            if meas_pts < max_pts:
                pts = meas_pts
                step_time = 0
            else:
                pts = max_pts
                step_time = (stime - pts * meas_cost) / pts
            if pts < 2:
                dstep = (stop - start)
                step_time = 0
            else:
                dstep = (stop - start) / (pts - 1)
            logger.debug("{!r} rang {}  max_pts {}   meas_pts {}   pts {}   dstep {}   step_time {}".format(self.instName, rang, max_pts, meas_pts, pts, dstep, step_time))
        else:
            nplc = self._nplc
            step_time = stime
            if stair.upper() == 'LIN':
                if stop <= start and dstep > 0 or stop >= start and dstep < 0 or dstep == 0:
                    return
                if (stop-start) / dstep <= 1.0:
                    dstep = (stop-start) / 1.0
                    logger.debug("{!r} dstep adjusted to {} on this sweep".format(self.instName, dstep))
                pts = int((stop-start)/dstep + 1)
            else:
                pts = dstep + 1
        if pts < 2:
            pts = 2
        self.budget.set_slack(self, 2)
        self.inst.write(':STATUS:QUE:CLE')           # clear error queue
        senses = sense.split(",")
        lnf = len(senses)
        if lnf > 1:
            self.inst.write(':SENS:FUNC:CONC ON')
            logger.measure("{!r} stair_sweep {} concurrently".format(self.instName, senses))
        else:
            self.inst.write(':SENS:FUNC:CONC OFF')
            logger.measure("{!r} stair_sweep {} individually".format(self.instName, senses))
        if measr:
            # resistance measurement
            self.inst.write(':SENS:RES:MODE MAN')
        if measv or measi or measr:
            self.inst.write(':SENS:FUNC {}'.format(sense))
        else:
            self.inst.write(':SENS:FUNC:OFF:ALL')
        if form != "":
            self.inst.write(':FORM:ELEM {}'.format(form))
        elements = self.inst.query(':FORM:ELEM?').split(",")
        if measv or measi or measr:
            logger.info("{!r} stair_sweep returns {} * {}".format(self.instName, elements, pts))
        else:
            logger.info("{!r} stair_sweep drives {} stepoints".format(self.instName, pts))
        lne = len(elements)
        self.inst.write(':SOUR:SWE:DIR {}'.format(direction))
        if "V" in typ:
            # self.voltage = start
            self.inst.write(':SOUR:FUNC VOLT')
            self.inst.write(':SOUR:VOLT:START {}'.format(start))
            self.inst.write(':SOUR:VOLT:STOP {}'.format(stop))
            self.inst.write(':SOUR:VOLT:MODE SWE')
            self.inst.write(':SYSTEM:AZER:STAT 0')
            self.inst.write(':SENS:CURR:NPLC {}'.format(nplc))
            if stair.upper() == 'LIN':
                self.inst.write(':SOUR:SWE:SPAC LIN')
                self.inst.write(':SOUR:VOLT:STEP {}'.format(dstep))
                logger.measure("{!r} stair_sweep lin voltage {} points".format(self.instName, pts))
            else:
                self.inst.write(':SOUR:SWE:SPAC LOG')
                self.inst.write(':SOUR:SWE:POIN {}'.format(pts))
                logger.measure("{!r} stair_sweep log voltage {} points".format(self.instName, pts))
        elif "I" in typ:
            # self.current = start
            self.inst.write(':SOUR:FUNC CURR')
            self.inst.write(':SOUR:CURR:START {}'.format(start))
            self.inst.write(':SOUR:CURR:STOP {}'.format(stop))
            self.inst.write(':SOUR:CURR:MODE SWE')
            self.inst.write(':SYSTEM:AZER:STAT 0')
            self.inst.write(':SENS:VOLT:NPLC {}'.format(nplc))
            if stair.upper() == 'LIN':
                self.inst.write(':SOUR:SWE:SPAC LIN')
                self.inst.write(':SOUR:CURR:STEP {}'.format(dstep))
                logger.measure("{!r} stair_sweep lin current {} points".format(self.instName, pts))
            else:
                self.inst.write(':SOUR:SWE:SPAC LOG')
                self.inst.write(':SOUR:SWE:POIN {}'.format(pts))
                logger.measure("{!r} stair_sweep log current {} points".format(self.instName, pts))
        self.inst.write(':SOUR:DEL {}'.format(step_time))
        self.on()
        self.inst.write(':SYST:TIME:RES')
        self.stair_measure = measure
        if wait:
            self.inst.write(':TRIG:COUN {}'.format(pts))
            if measv or measi or measr:
                value = self.inst.query(':READ?')
                if "V" in typ:
                    self.inst.write(':SOUR:VOLT:MODE FIXED')
                    self.inst.write(':SOUR:VOLT:LEV {}'.format(final))
                    self.inst.write(':SENS:VOLT:NPLC {}'.format(self._nplc))
                else:
                    self.inst.write(':SOUR:CURR:MODE FIXED')
                    self.inst.write(':SOUR:CURR:LEV {}'.format(final))
                    self.inst.write(':SENS:CURR:NPLC {}'.format(self._nplc))
                self.budget.set_slack(self)
                res = [float(i) for i in value.split(",")]
                na = np.array(res)
                nb = na.reshape((len(na))//lne, lne)
                nc = nb.transpose()
                return (nc)
            else:
                self.inst.write(':INIT')
                if "V" in typ:
                    self.inst.write(':SOUR:VOLT:MODE FIXED')
                    self.inst.write(':SOUR:VOLT:LEV {}'.format(final))
                    self.inst.write(':SENS:VOLT:NPLC {}'.format(self._nplc))
                else:
                    self.inst.write(':SOUR:CURR:MODE FIXED')
                    self.inst.write(':SOUR:CURR:LEV {}'.format(final))
                    self.inst.write(':SENS:CURR:NPLC {}'.format(self._nplc))
        else:
            self.budget.set_slack(self, pts * (step_time * 1.0 + lne * 0.1))
            self.inst.write(':TRAC:FEED SENS')
            self.inst.write(':TRAC:POIN {}'.format(pts))
            self.inst.write(':TRAC:CLE')
            self.inst.write(':TRAC:FEED:CONT NEXT')
            self.inst.write(':TRIG:COUN {}'.format(pts))
            self.inst.write(':INIT')
            if "V" in typ:
                self.inst.write(':SOUR:VOLT:MODE FIXED')
                self.inst.write(':SOUR:VOLT:LEV {}'.format(final))
                self.inst.write(':SENS:VOLT:NPLC {}'.format(self._nplc))
            else:
                self.inst.write(':SOUR:CURR:MODE FIXED')
                self.inst.write(':SOUR:CURR:LEV {}'.format(final))
                self.inst.write(':SENS:CURR:NPLC {}'.format(self._nplc))

    def get_values(self, typ=''):
        """Transfer last requested measurement sweep results.

        get response of previous stair_sweep(), choosing result rows from previous request typ
        """
        if not typ or typ == '':
            typ = self.stair_measure
        unknown_measure = [tm for tm in typ if not tm in "VI" + self.stair_measure]
        if unknown_measure:
            logger.error("{!r} get_values '{}' for stair_sweep of '{}' unknown".format(self.instName, unknown_measure, self.stair_measure))
            return np.array(None)
        lne = len(self.stair_measure)
        length = self.inst.query(':TRAC:POIN?')
        length = int(float(length))
        if length > 0 and lne > 0:
            self.budget.set_slack(self, length * lne)
            smL = []
            for smi in range(lne):
                if self.stair_measure[smi] in typ:
                    smL.append(smi)
            value = self.inst.query(':TRAC:DATA?')
            res = [float(i) for i in value.split(",")]
            self.budget.set_slack(self)
            na = np.array(res)
            nb = na.reshape((len(na))//lne, lne)
            nc = nb.transpose()
            if smL != list(range(lne)):
                nc = nc[smL]
        else:
            self.budget.set_slack(self)
            nc = np.array(None)
        return (nc)

    @property
    def stair_step(self):
        """Set incremental ramp to target or (target,dstep) or (target,dstep,stime).

        Stair_step to target or target,dstep or target,dstep,stime, using previous stair_sweep() parameters.
        """
        return (self.stair_step_get)

    @stair_step.setter
    def stair_step(self, stair_set):
        if not type(stair_set) in [type(tuple()), type(list())]:
            stair_set_args, stair_set_kwargs = self.stair_step_set
            stair_set_args[0] = None
            stair_set_args[1] = stair_set
            stair_set_kwargs['wait'] = False
            stair_set_kwargs['typ'] = stair_set_kwargs['typ'].replace('-', '')
            self.stair_step_get = self.stair_sweep(*stair_set_args, **stair_set_kwargs)
        else:
            if len(stair_set) == 2:
                stair_set_args, stair_set_kwargs = self.stair_step_set
                stair_set_args[0] = None
                stair_set_args[1] = stair_set[0]
                stair_set_args[2] = stair_set[1]
                stair_set_kwargs['wait'] = False
                stair_set_kwargs['typ'] = stair_set_kwargs['typ'].replace('-', '')
                self.stair_step_get = self.stair_sweep(*stair_set_args, **stair_set_kwargs)
            if len(stair_set) == 3:
                stair_set_args, stair_set_kwargs = self.stair_step_set
                stair_set_args[0] = None
                stair_set_args[1] = stair_set[0]
                stair_set_args[2] = stair_set[1]
                stair_set_kwargs['wait'] = False
                stair_set_kwargs['stime'] = stair_set[2]
                stair_set_kwargs['typ'] = stair_set_kwargs['typ'].replace('-', '')
                self.stair_step_get = self.stair_sweep(*stair_set_args, **stair_set_kwargs)

    @property
    def stair_slope(self):
        """Set incremental ramp to target or (target,slopetime).

        Stair_slope to target or target,slope_time using previous stair_sweep() parameters.
        """
        return (self.stair_step_get)

    @stair_slope.setter
    def stair_slope(self, stair_set):
        if not type(stair_set) in [type(tuple()), type(list())]:
            stair_set_args, stair_set_kwargs = self.stair_step_set
            stair_set_args[0] = None
            stair_set_args[1] = stair_set
            stair_set_args[2] = None
            stair_set_kwargs['wait'] = False
            stair_set_kwargs['typ'] = stair_set_kwargs['typ'].replace('-', '')
            self.stair_step_get = self.stair_sweep(*stair_set_args, **stair_set_kwargs)
        else:
            stair_set_args, stair_set_kwargs = self.stair_step_set
            stair_set_args[0] = None
            stair_set_args[1] = stair_set[0]
            stair_set_args[2] = None
            stair_set_kwargs['stime'] = stair_set[1]
            stair_set_kwargs['wait'] = False
            stair_set_kwargs['typ'] = stair_set_kwargs['typ'].replace('-', '')
            self.stair_step_get = self.stair_sweep(*stair_set_args, **stair_set_kwargs)
