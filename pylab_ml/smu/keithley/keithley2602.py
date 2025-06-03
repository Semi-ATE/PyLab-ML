"""Interface to the dual channel Power-Measuremet-Unit (SMU) Keithley2602.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>

"""
import re
import numpy as np
import math
from pylab_ml.base_instrument import logger
from pylab_ml.collate_instrument import Interface
from pylab_ml.smu.keithley.base_keithley import Keithley


class Keithley2602 (Keithley):
    """Interface to the dual channel Power-Measuremet-Unit (SMU) Keithley2602.

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    .. image:: ../static/kethley2602.jpg

    The Keithley2602 can
    source and sink power in all four voltage/current quadrants and
    measure voltage and current precisely on dual channels a & b

    """

    A = "a"    # channel A
    B = "b"    # channel B

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
        self.has_scripts = False
        kwargs = {"addr": addr, "interface": interface, "backend": backend, "identify": identify, "instName": instName}
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
        self.msg_row_col = (1, 20)

    def setup_inst(self):
        """Start setup instrument settings, called from class instruments."""
        super().setup_inst()
        self._measure = "virp"
        if self.inst is not None:
            self.inst.read_termination = '\n'
            self.inst.write_termination = '\n'
        self.chab = self.A
        self._nplc = 0.01
        self._i_clamp = {'a': 1e-3, 'b': 1e-3}
        self._v_clamp = {'a': 20,   'b': 20}
        self._i_range = {'a': 1e-3, 'b': 1e-3}
        self._v_range = {'a': 20,   'b': 20}
        self._I_range = {'a': 1e-3, 'b': 1e-3}
        self._V_range = {'a': 20,   'b': 20}
        self.stair_step_set = [[0, 0, 0.1], {"typ": "V"}]
        self.stair_step_get = np.array([])
        self.stair_measure = ""

    def reset(self):
        """Reset and switch beep off."""
        self.inst.write('localnode.prompts = 0')
        self.inst.write('reset()')
        self.inst.write('beeper.enable = 0')
        self.clearbuffer(self.A)
        self.clearbuffer(self.B)
        self.inst.clear()
        self.i_clamp = self._i_clamp[self.A]
        self.v_clamp = self._v_clamp[self.A]
        self.i_clamp = self._i_clamp[self.B]
        self.v_clamp = self._v_clamp[self.B]
        self.i_range = self._i_range[self.A]
        self.v_range = self._v_range[self.A]
        self.I_range = self._I_range[self.B]
        self.V_range = self._V_range[self.B]
        self.ch = self.A

    def close(self):
        """Close the connection and switch off all outputs."""
        self.ch = self.A
        self.onoff = False
        self.ch = self.B
        self.onoff = False
        super().close()

    def on(self):
        """Reactivate output."""
        self.budget.set_slack(self)
        msg = 'smu{ch}.source.output = smu{ch}.OUTPUT_ON'
        self.inst.write(msg.format(ch=self.chab))

    def off(self):
        """Deactivate output."""
        self.budget.set_slack(self)
        msg = 'smu{ch}.source.output = smu{ch}.OUTPUT_OFF'
        self.inst.write(msg.format(ch=self.chab))

    @property
    def onoff(self):
        """Set/get on state from output (True)."""
        self.budget.set_slack(self)
        msg = 'print(smu{ch}.source.output)'
        self.inst.write(msg.format(ch=self.chab))
        result = float(self.inst.read()) > 0
        return (result)

    @onoff.setter
    def onoff(self, value):
        if value:
            self.on()
        else:
            self.off()

    def clearbuffer(self, ch):
        """Clear the instrument buffer."""
        self.budget.set_slack(self)
        self.inst.write('smu{}.nvbuffer1.clear()'.format(ch.lower()))
        self.inst.write('smu{}.nvbuffer2.clear()'.format(ch.lower()))

    def message(self, message=None):
        """Message display.

        instrument message ("string") or ()
        """
        self.budget.set_slack(self)
        if message is None:
            self.inst.write('display.clear()')
        else:
            linlen = self.msg_row_col[0] * self.msg_row_col[1]
            msg = message[:linlen]
            self.inst.write('display.clear()')
            self.inst.write('display.settext("{message}")'.format(message=msg))

    @property
    def id(self):
        """Query IDN."""
        self.budget.set_slack(self)
        try:
            value = self.inst.query('*IDN?')
        except Exception:
            value = ""
        return value.replace('\r', '').replace('\n', '')

    def error_list(self):
        """List of instrument errors."""
        self.budget.set_slack(self)
        errorlist = []
        while True:
            errormsg = self.inst.query('print(errorqueue.next())')
            if errormsg is None or errormsg == "":
                break
            errors_cmsn = errormsg.split("\t")
            if len(errors_cmsn) == 4:
                (c, m, s, n) = errormsg.split("\t")
                print("{} : {} : {} : {}".format(c, m, s, n))
                errorlist.append((c, m, s, n))
            else:
                print("{} : {} : {} : {}".format(-1, errormsg, -1, -1))
                errorlist.append((-1, errormsg, -1, -1))
            if errormsg == '0.00000e+00\tQueue Is Empty\t0.00000e+00\t0.00000e+00':
                break
        return errorlist

    def channel(self, ch='A'):
        """Set channel A or B."""
        self.chab = ch.lower()

    @property
    def ch(self):
        """Get or Set channel A or B."""
        return (self.chab)

    @ch.setter
    def ch(self, ch):
        self.channel(ch)

    @property
    def nplc(self):
        """Set the conversion number of power line cycles accuracy, for all converters.

        for a plc of 0.1, conversion rate is 0.1/50s = 2ms. Accuracy max 25, min 0.001
        """
        self.budget.set_slack(self)
        val = self.inst.query('print(smu{ch}.measure.nplc)'.format(ch=self.chab))
        return float(val)

    @nplc.setter
    def nplc(self, cycles):            # cycles are number of power line cycles for conversion
        self._nplc = cycles
        self.budget.set_slack(self)
        # in Keithley 2400 each measurement (v,i,r) is common accuracy
        self.inst.write('smu{ch}.measure.nplc =  {nplc}'.format(ch=self.chab, nplc=cycles))

    @property
    def v_autorange(self):
        """Autorange voltage measurement on or off."""
        self.budget.set_slack(self)
        msg = 'print(smu{ch}.measure.autorangev)'
        res = self.inst.query(msg.format(ch=self.chab))
        return (float(res) != 0)

    @v_autorange.setter
    def v_autorange(self, on):
        self.budget.set_slack(self)
        if on:
            msg = 'smu{ch}.measure.autorangev = smu{ch}.AUTORANGE_ON'
        else:
            msg = 'smu{ch}.measure.autorangev = smu{ch}.AUTORANGE_OFF'
        self.inst.write(msg.format(ch=self.chab))

    @property
    def i_autorange(self):
        """Autorange current measurement on or off."""
        self.budget.set_slack(self)
        msg = 'print(smu{ch}.measure.autorangei)'
        res = self.inst.query(msg.format(ch=self.chab))
        return (float(res) != 0)

    @i_autorange.setter
    def i_autorange(self, on):
        self.budget.set_slack(self)
        if on:
            msg = 'smu{ch}.measure.autorangei = smu{ch}.AUTORANGE_ON'
        else:
            msg = 'smu{ch}.measure.autorangei = smu{ch}.AUTORANGE_OFF'
        self.inst.write(msg.format(ch=self.chab))

    @property
    def V_autorange(self):
        """Autorange drive voltage on or off."""
        self.budget.set_slack(self)
        msg = 'print(smu{ch}.source.autorangev)'
        res = self.inst.query(msg.format(ch=self.chab))
        return (float(res) != 0)

    @V_autorange.setter
    def V_autorange(self, on):
        self.budget.set_slack(self)
        if on:
            msg = 'smu{ch}.source.autorangev = smu{ch}.AUTORANGE_ON'
        else:
            msg = 'smu{ch}.source.autorangev = smu{ch}.AUTORANGE_OFF'
        self.inst.write(msg.format(ch=self.chab))

    @property
    def I_autorange(self):
        """Autorange drive current on or off."""
        self.budget.set_slack(self)
        msg = 'print(smu{ch}.source.autorangei)'
        res = self.inst.query(msg.format(ch=self.chab))
        return (float(res) != 0)

    @I_autorange.setter
    def I_autorange(self, on):
        self.budget.set_slack(self)
        if on:
            msg = 'smu{ch}.source.autorangei = smu{ch}.AUTORANGE_ON'
        else:
            msg = 'smu{ch}.source.autorangei = smu{ch}.AUTORANGE_OFF'
        self.inst.write(msg.format(ch=self.chab))

    @property
    def measure(self):
        """Get or set measure.

        where the measurements are defined by "virp" flags (VOLTAGE,CURRENT,RESISTANCE,POWER).
        """
        if not self.onoff:
            return
        msg = ""
        sep = ""
        measv = False
        measi = False
        measr = False
        measp = False
        if "v" in self._measure:
            measv = True
        if "i" in self._measure:
            measi = True
        if "r" in self._measure:
            measr = True
        if "p" in self._measure:
            measp = True
        if measv and measi:
            msg += sep + 'smu{ch}.measure.iv()'.format(ch=self.chab)
            sep = ","
        elif measv:
            msg += sep + 'smu{ch}.measure.v()'.format(ch=self.chab)
            sep = ","
        elif measi:
            msg += sep + 'smu{ch}.measure.i()'.format(ch=self.chab)
            sep = ","
        if measr:
            msg += sep + 'smu{ch}.measure.r()'.format(ch=self.chab)
            sep = ","
        if measp:
            msg += sep + 'smu{ch}.measure.p()'.format(ch=self.chab)
            sep = ","
        if msg == "":
            logger.error("{!r} measure undefined measurements '{}'".format(self.instName, self._measure))
            return
        logger.info("{!r} measure returns {}".format(self.instName, self._measure))
        self.budget.set_slack(self, 0.3)
        msg = "print({})".format(msg)
        res = self.inst.query(msg)
        res = res.split("\t")
        res = [float(f) for f in res]
        if measv and measi:
            if measr:
                v = res[0] * res[1]
                res = [v] + res
            elif measp:
                v = res[1] / res[0]
                res = [v] + res
        logger.measure("{!r} {} == {}".format(self.instName, self._measure, res))
        self.budget.set_slack(self)
        return (res)

    @measure.setter
    def measure(self, typ="virp"):
        self._measure = typ

    @property
    def voltage(self):
        """Get or set output voltage.

        If the voltage is set the output is switched on immediately.
        """
        self.budget.set_slack(self)
        if not self.onoff:
            return
        msg = 'display.screen = display.SMU{CH}'
        self.inst.write(msg.format(CH=self.chab.upper()))
        msg = 'display.smu{ch}.measure.func = display.MEASURE_DCVOLTS'
        self.inst.write(msg.format(ch=self.chab))
        msg = 'smu{ch}.measure.nplc = 1'
        self.inst.write(msg.format(ch=self.chab))
        msg = 'print(smu{ch}.measure.v())'
        self.inst.write(msg.format(ch=self.chab))
        value = self.inst.read()
        logger.measure("{!r} voltage@{} == {}".format(self.instName, self.chab, float(value)))
        return float(value)

    @voltage.setter
    def voltage(self, value):
        self.budget.set_slack(self)
        msg = 'display.screen = display.SMU{CH}'
        self.inst.write(msg.format(CH=self.chab.upper()))
        # Select voltage source
        msg = 'smu{ch}.source.func = smu{ch}.OUTPUT_DCVOLTS'
        self.inst.write(msg.format(ch=self.chab))
        # Select voltage level
        msg = 'smu{ch}.source.levelv = {val}'
        self.inst.write(msg.format(ch=self.chab, val=value))
        logger.measure("{!r} voltage@{} := {}".format(self.instName, self.chab, float(value)))
        self.onoff = True
        if self.is_local:
            self.voltage

    @property
    def current(self):
        """Get or set output current.

        If the current is set the output is switched on immediately.
        """
        self.budget.set_slack(self)
        if not self.onoff:
            return
        msg = 'display.screen = display.SMU{CH}'
        self.inst.write(msg.format(CH=self.ch.upper()))
        # Current measure function
        msg = 'display.smu{ch}.measure.func = display.MEASURE_DCAMPS'
        self.inst.write(msg.format(ch=self.chab))
        msg = 'smu{ch}.measure.nplc = 1'
        self.inst.write(msg.format(ch=self.chab))
        msg = 'print(smu{ch}.measure.i())'
        self.inst.write(msg.format(ch=self.chab))
        value = self.inst.read()
        logger.measure("{!r} current@{} == {}".format(self.instName, self.chab, float(value)))
        return float(value)

    @current.setter
    def current(self, value):
        self.budget.set_slack(self)
        msg = 'display.screen = display.SMU{CH}'
        self.inst.write(msg.format(CH=self.ch.upper()))
        # Select current source
        msg = 'smu{ch}.source.func = smu{ch}.OUTPUT_DCAMPS'
        self.inst.write(msg.format(ch=self.chab))
        # Select current level
        msg = 'smu{ch}.source.leveli = {val}'
        self.inst.write(msg.format(ch=self.chab, val=value))
        logger.measure("{!r} current@{} := {}".format(self.instName, self.chab, float(value)))
        self.onoff = True
        if self.is_local:
            self.current

    @property
    def i_clamp(self):
        """Set the current clamping (A), will adjust current measurement range."""
        self.budget.set_slack(self)
        limit = self.inst.query("print(smu{ch}.source.limiti)".format(ch=self.chab))
        return float(limit)

    @i_clamp.setter
    def i_clamp(self, imax):            # imax in A
        self._i_clamp[self.chab] = imax
        self.budget.set_slack(self)
        self.inst.write('smu{ch}.source.limiti = {val}'.format(ch=self.chab, val=imax))

    @property
    def v_clamp(self):
        """Set the voltage clamping (V), will adjust voltage measurement range."""
        self.budget.set_slack(self)
        limit = self.inst.query("print(smu{ch}.source.limitv)".format(ch=self.chab))
        return float(limit)

    @v_clamp.setter
    def v_clamp(self, vmax):            # vmax in V
        self._v_clamp[self.chab] = vmax
        self.budget.set_slack(self)
        self.inst.write('smu{ch}.source.limitv = {val}'.format(ch=self.chab, val=vmax))

    @property
    def i_range(self):
        """Set the current measurement range (A)."""
        self.budget.set_slack(self)
        limit = self.inst.query("print(smu{ch}.measure.rangei)".format(ch=self.chab))
        return float(limit)

    @i_range.setter
    def i_range(self, imax):            # imax in A
        self._i_range[self.chab] = imax
        self.budget.set_slack(self)
        self.inst.write('smu{ch}.measure.rangei = {val}'.format(ch=self.chab, val=abs(imax)))

    @property
    def v_range(self):
        """Set the voltage measurement range (V)."""
        self.budget.set_slack(self)
        limit = self.inst.query("print(smu{ch}.measure.rangev)".format(ch=self.chab))
        return float(limit)

    @v_range.setter
    def v_range(self, vmax):            # vmax in V
        self._v_range[self.chab] = vmax
        self.budget.set_slack(self)
        self.inst.write('smu{ch}.measure.rangev = {val}'.format(ch=self.chab, val=abs(vmax)))

    @property
    def I_range(self):
        """Set the current driver range (A)."""
        self.budget.set_slack(self)
        limit = self.inst.query("print(smu{ch}.source.rangei)".format(ch=self.chab))
        return float(limit)

    @I_range.setter
    def I_range(self, imax):            # imax in A
        self._I_range[self.chab] = imax
        self.budget.set_slack(self)
        self.inst.write('smu{ch}.source.rangei = {val}'.format(ch=self.chab, val=abs(imax)))

    @property
    def V_range(self):
        """Set the voltage driver range (V)."""
        self.budget.set_slack(self)
        limit = self.inst.query("print(smu{ch}.source.rangev)".format(ch=self.chab))
        return float(limit)

    @V_range.setter
    def V_range(self, vmax):            # vmax in V
        self._V_range[self.chab] = vmax
        self.budget.set_slack(self)
        self.inst.write('smu{ch}.source.rangev = {val}'.format(ch=self.chab, val=abs(vmax)))

    def stair_sweep(self, start, stop, dstep, stime=0, typ='V', stair='Lin', wait=False):
        """Sweep V or I, measure v,i,r,p at time t with state s, wait for response.

        Args:
           typ:
              | 'Vvirpts-?', 'Ivirpts-?'  = Voltage / Current sourced, '-' changes direction,
              |  volts, amps, ohms, power, timestamp, status are sensed, ? animates display
           start:
              Start value in volts or amps
           stop:
              Stop value in volts or amps
           dstep:
              Delta amplitude for Lin, Points to interpolate for Log, stime is slope time for None (>0.2ms)
           stime:
              Delay between steps or slope time if dstep == None
           stair:
              ('Lin','Log) = linear or log source

        """
        args = [None, stop, dstep]
        kwargs = {'stime': stime, 'typ': typ, 'stair': stair, 'wait': wait}
        self.stair_step_set = [args, kwargs]
        self.budget.set_slack(self)
        if not self.has_scripts:
            self.scripts()
        if not self.has_scripts:
            logger.error("{!r} has no scripts loaded".format(self.instName))
            return
        styp = 'V'
        mtyp = 0
        measure = "V"
        measi = False
        measv = False
        measr = False
        measp = False
        lne = 0
        if 'I' in typ:
            measure = "I"
            styp = 'I'
        if "v" in typ:
            measure += "v"
            mtyp = mtyp | 2
            measv = True
            lne += 1
        if "i" in typ:
            measure += "i"
            mtyp = mtyp | 1
            measi = True
            lne += 1
        if "r" in typ:
            measure += "r"
            mtyp = mtyp | 4
            measr = True
            lne += 1
        if "p" in typ:
            measure += "p"
            mtyp = mtyp | 8
            measp = True
            lne += 1
        if "t" in typ:
            measure += "t"
            mtyp = mtyp | 16
            lne += 1
        if "s" in typ:
            measure += "s"
            mtyp = mtyp | 32
            lne += measv + measi + measr + measp
        if "?" in typ:
            mtyp = mtyp | 64
        lne += (measv | measi | measr | measp)
        if start is None or str(start) == '?':
            start = self.voltage
            if start is None:
                start = 0
                logger.warning("{!r} initial start assumed to be 0".format(self.instName))
            if dstep is not None:
                if start > stop and dstep > 0:
                    dstep = -1.0 * dstep
        if dstep is None:
            # stime is slope time
            # No measurement
            #   v_range =  <= 40
            # 1001 points for 40V == 240ms
            # 1001 points for 20V == 240ms
            # 1001 points for 10V == 240ms
            # 1001 points for 7V == 240ms
            #   v_range <= 6
            # 1001 points for 6V == 170ms
            # 1001 points for 5V == 170ms
            # 1001 points for 4V == 170ms
            # 1001 points for 3V == 170ms
            # 1001 points for 2V == 160ms
            #   v_range <= 1
            # 1001 points for 1V == 140ms
            # 101 points for 1V == 14.8ms
            # 11 points for 1V == ~1.5ms
            #   v_range <= 0.1
            # ?
            # V measurement, nplc = 0.001
            # 1001 points for 10V == 580ms
            # 1001 points for 7V == 580ms
            #   v_range <= 6
            # 1001 points for 6V == 510ms
            # 1001 points for 3V == 510ms
            # 1001 points for 2V == 510ms
            #   v_range <= 1
            # 1001 points for 1V == 480ms
            # 101 points for 1V == 49ms
            # 11 points for 1V == ~4.9ms
            # I measurement, nplc = 0.001
            # 1001 points for 10V == 580ms
            #   v_range <= 6
            # 1001 points for 6V == 510ms
            #   v_range <= 1
            # 1001 points for 1V == 470ms
            # 101 points for 1V == 49ms
            # 11 points for 1V == 5ms
            # VI (+R) measurement, nplc = 0.001
            # 1001 points for 10V == 680ms
            #   v_range <= 6
            # 1001 points for 6V == 620ms
            # 1001 points for 2V == 620ms
            #   v_range <= 1
            # 1001 points for 1V == 590ms
            # 101 points for 1V == 60ms
            # 11 points for 1V == 6ms
            # R measurement, nplc = 0.01
            # 101 points for 1V == 510ms
            nplc = 0.001
            fsd = max(abs(start), abs(stop))
            rang = abs(stop - start)
            max_pts = int(math.log(rang + 1.05) * 50)
            if measv and measi or measv and measr or measi and measr:
                if fsd > 6:
                    meas_cost = 0.66e-3
                if fsd > 1:
                    meas_cost = 0.62e-3
                else:
                    meas_cost = 0.6e-3
            elif measi or measr or measv:
                if fsd > 6:
                    meas_cost = 0.58e-3
                if fsd > 1:
                    meas_cost = 0.51e-3
                else:
                    meas_cost = 0.49e-3
            else:
                if fsd > 6:
                    meas_cost = 0.24e-3
                if fsd > 1:
                    meas_cost = 0.17e-3
                else:
                    meas_cost = 0.14e-3
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
            logger.debug("{!r} rang {}  max_pts {}   meas_pts {}   pts {}   dstep {}   step_time {}"
                         .format(self.instName, rang, max_pts, meas_pts, pts, dstep, step_time))
        elif dstep == 0:
            nplc = self._nplc
            step_time = stime
            pts = 0
        else:
            nplc = self._nplc
            step_time = stime
            pts = abs(int((stop - start) / dstep))+1
        if "-" in typ:
            dstep *= -1
            start, stop = stop, start
            typ = [c for c in typ if c != '-']
        self.inst.write('smu{ch}.measure.nplc = {nplc}'.format(ch=self.chab, nplc=nplc))
        self.stair_measure = measure
        if wait:
            msg = 'waitcomplete()\r print(SweepStaircase(smu{ch}, {start}, {stop}, {dstep}, {stime}, "{typ}", {mtyp}))'.format(
                ch=self.chab, start=start, stop=stop, dstep=dstep, stime=step_time, typ=styp, mtyp=mtyp)
            self.budget.set_slack(self, pts * (step_time * 1.0 + lne * 0.1))
            ret = self.inst.query(msg)
            ret = int(float(ret))
            if measv or measi:
                logger.info("{!r} stair_sweep returns {} * {}".format(self.instName, lne, ret))
            else:
                logger.info("{!r} stair_sweep drives {} stepoints".format(self.instName, ret))
        else:
            msg = 'waitcomplete()\r SweepStaircase(smu{ch}, {start}, {stop}, {dstep}, {stime}, "{typ}", {mtyp})'.format(
                ch=self.chab, start=start, stop=stop, dstep=dstep, stime=step_time, typ=styp, mtyp=mtyp)
            self.budget.set_slack(self, pts * (step_time * 1.0 + lne * 0.1))
            self.inst.write(msg)
            ret = None
            if measv or measi:
                logger.info("{!r} stair_sweep initiates {} * {} measurements".format(self.instName, lne, pts))
            else:
                logger.info("{!r} stair_sweep initiates drive of {} stepoints".format(self.instName, pts))
        self.inst.write('smu{ch}.measure.nplc = {nplc}'.format(ch=self.chab, nplc=self._nplc))
        if ret:
            if wait:
                ret = self.get_values(typ)
        self.budget.set_slack(self)
        return ret

    def get_values(self, typ=''):
        """Transfer last requested measurement sweep results.

        Get response of previous stair_sweep(), choosing result rows from previous request typ

        Parameters
        ----------
        typ : string, optional
            'virpts'. The default is ''.

        Returns
        -------
        TYPE
            values.

        """
        if not typ or typ == '':
            typ = self.stair_measure
        unknown_measure = [tm for tm in typ if not tm in "VI" + self.stair_measure]
        if unknown_measure:
            logger.error("{!r} get_values '{}' for stair_sweep of '{}' unknown".format(self.instName, unknown_measure, self.stair_measure))
            return np.array(None)
        self.budget.set_slack(self)
        lne = 0
        if not self.has_scripts:
            logger.error("{!r} has no scripts loaded".format(self.instName))
            return
        length = self.inst.query('waitcomplete()\r print(math.max(smu{ch}.nvbuffer1.n,smu{ch}.nvbuffer2.n))'.format(ch=self.chab))
        length = int(float(length))
        if length > 0:
            self.budget.set_slack(self, length*0.1)
            measurements = ''
            msep = ''
            if 'V' in typ or 'I' in typ:
                if 'i' in typ:
                    measurements += msep + 'smu{ch}.nvbuffer1.sourcevalues'.format(ch=self.chab)
                    msep = ','
                    lne += 1
                elif 'v' in typ:
                    measurements += msep + 'smu{ch}.nvbuffer2.sourcevalues'.format(ch=self.chab)
                    msep = ','
                    lne += 1
            if 'i' in typ:
                measurements += msep + 'smu{ch}.nvbuffer1.readings'.format(ch=self.chab)
                msep = ','
                lne += 1
            if 'v' in typ:
                measurements += msep + 'smu{ch}.nvbuffer2.readings'.format(ch=self.chab)
                msep = ','
                lne += 1
            if 'r' in typ:
                measurements += msep + 'nvbuffer3.readings'
                msep = ','
                lne += 1
            if 'p' in typ:
                measurements += msep + 'nvbuffer4.readings'
                msep = ','
                lne += 1
            if 't' in typ:
                if 'i' in typ:
                    measurements += msep + 'smu{ch}.nvbuffer1.timestamps'.format(ch=self.chab)
                    msep = ','
                    lne += 1
                elif 'v' in typ:
                    measurements += msep + 'smu{ch}.nvbuffer2.timestamps'.format(ch=self.chab)
                    msep = ','
                    lne += 1
            if 's' in typ:
                if 'i' in typ:
                    measurements += msep + 'smu{ch}.nvbuffer1.statuses'.format(ch=self.chab)
                    msep = ','
                    lne += 1
                if 'v' in typ:
                    measurements += msep + 'smu{ch}.nvbuffer2.statuses'.format(ch=self.chab)
                    msep = ','
                    lne += 1
                if 'r' in typ:
                    measurements += msep + 'nvbuffer3.statuses'
                    msep = ','
                    lne += 1
                if 'p' in typ:
                    measurements += msep + 'nvbuffer4.statuses'
                    msep = ','
                    lne += 1
            value = self.inst.query('waitcomplete()\r printbuffer(1,{l},{m})'.format(l=length, m=measurements))
            res = [float(i) for i in value.split(",")]
            self.budget.set_slack(self)
            na = np.array(res)
            nb = na.reshape((len(na))//lne, lne)
            nc = nb.transpose()
        else:
            self.budget.set_slack(self)
            nc = np.array(None)
        return (nc)

    @property
    def stair_step(self):
        """Set incremental ramp to target or (target,dstep) or (target,dstep,stime).

        Step_stair to target or target,dstep or target,dstep,stime, using previous stair_sweep() parameters.
        """
        return (self.stair_step_get)

    @stair_step.setter
    def stair_step(self, stair_set):
        if not type(stair_set) in [type(tuple()), type(list())]:
            stair_set_args, stair_set_kwargs = self.stair_step_set
            stair_set_args[0] = None
            stair_set_args[1] = stair_set
            stair_set_kwargs['wait'] = False
            self.stair_step_get = self.stair_sweep(*stair_set_args, **stair_set_kwargs)
        else:
            if len(stair_set) == 2:
                stair_set_args, stair_set_kwargs = self.stair_step_set
                stair_set_args[0] = None
                stair_set_args[1] = stair_set[0]
                stair_set_args[2] = stair_set[1]
                stair_set_kwargs['wait'] = False
                self.stair_step_get = self.stair_sweep(*stair_set_args, **stair_set_kwargs)
            if len(stair_set) == 3:
                stair_set_args, stair_set_kwargs = self.stair_step_set
                stair_set_args[0] = None
                stair_set_args[1] = stair_set[0]
                stair_set_args[2] = stair_set[1]
                stair_set_kwargs['wait'] = False
                stair_set_kwargs['stime'] = stair_set[2]
                self.stair_step_get = self.stair_sweep(*stair_set_args, **stair_set_kwargs)

    @property
    def stair_slope(self):
        """stair_slope to target or target, slope_time using previous stair_sweep() parameters."""
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

    def scriptin(self, msg):
        """A multiline LUA script needs to have -- comments correctly handled and newlines.

        converted to returns
        """
        self.inst.write('display.clear()')
        self.inst.write('display.settext("loading scripts: ")')
        newmsg = "loadandrunscript\n"
        if False:
            for line in msg.split("\n"):
                mo = re.match(r".*(--)(\[\[)*", line)
                if mo and mo.groups() == ("--", None):
                    newline = re.sub("--", "--[[", line, 1)
                    newmsg += newline + "]]" + "\n"
                else:
                    newmsg += line + "\n"
        else:
            newmsg += msg + "\n"
        newmsg += "endscript"
        return newmsg

    def scripts(self):
        """Upload specific functionality : sweep DUT."""
        print("loading scripts")
        msg = """
display.clear()
display.settext("loading scripts: ")
SweepStaircase = nil
AbortScript = nil
--nvbuffer3 = nil
--nvbuffer4 = nil
function SweepStaircase(smu, start, stop, dstep, stime, typ, mtyp)
    -- Save settings in temporary variables so they can be restored at the end.
    local l_d_screen = display.screen
    -- Temporary variables used by this function.
    local l_dstep = dstep
    local l_sweep = 0
    local l_typ = typ
    local l_limit = 0
    local l_j
    local points
    local l_measiv = bit.getfield(mtyp,1,2)
    local l_measi = bit.test(mtyp,1)
    local l_measv = bit.test(mtyp,2)
    local l_measr = bit.test(mtyp,3)
    local l_measp = bit.test(mtyp,4)
    local l_meast = bit.test(mtyp,5)
    local l_meass = bit.test(mtyp,6)
    local l_disptrack = bit.test(mtyp,7)
    display.settext("c")
    -- Default to smua if no smu is specified.
    if smu == nil then
        smu = smua
    end
    -- Default to V sweep
    if tostring(l_typ) ~= "I" then
        l_typ = "V"
        l_limit = smu.source.limitv
    else
        l_typ = "I"
        l_limit = smu.source.limiti
    end
    -- Default to no measurement
    if mtyp == nil then
        mtyp = 0
    end
    -- calculate points
    points = 0
    if l_dstep == 0 then
        smu.nvbuffer1.clear()
        smu.nvbuffer2.clear()
        AbortScript(": dstep==0", l_d_screen)
        return 0
    end
    if start < stop then
        if l_dstep < 0 then
            l_dstep = l_dstep * -1.0
        end
        points = math.floor((stop - start) / l_dstep)
        if points < 1 then
            points = 1
            l_dstep = stop - start
        end
    else
        if l_dstep > 0 then
            l_dstep = l_dstep * -1.0
        end
        points = math.floor((stop - start) / l_dstep)
        if points < 1 then
            points = 1
            l_dstep = start - stop
        end
    end
    l_sweep = start
    -- Setup a buffers to store the result(s) in and start testing.
    smu.nvbuffer1.clear()
    smu.nvbuffer1.appendmode = 1
    smu.nvbuffer1.collectsourcevalues = 1
    if l_meast then
        smu.nvbuffer1.collecttimestamps = 1
    else
        smu.nvbuffer1.collecttimestamps = 0
    end
    smu.nvbuffer2.clear()
    smu.nvbuffer2.appendmode = 1
    smu.nvbuffer2.collectsourcevalues = 1
    if l_meast then
        smu.nvbuffer2.collecttimestamps = 1
    else
       smu.nvbuffer2.collecttimestamps = 0
    end
    --nvbuffer3 = nil
    nvbuffer3 = smu.makebuffer(points+1)
    nvbuffer3.clear()
    nvbuffer3.appendmode = 1
    --nvbuffer4 = nil
    nvbuffer4 = smu.makebuffer(points+1)
    nvbuffer4.clear()
    nvbuffer4.appendmode = 1
    -- Check limits not exceeded in sweep
    if math.abs(start) > math.abs(l_limit) then
        AbortScript(": start>limit", l_d_screen)
        return 0
    end
    if math.abs(stop) > math.abs(l_limit) then
        AbortScript(": stop>limit", l_d_screen)
        return 0
    end
    -- update display
    display.clear()
    display.settext("SweepStairs " .. l_typ .. " " .. points)
    -- Configure source and measure settings.
    if l_typ == "V" then
        smu.source.func = smu.OUTPUT_DCVOLTS
        smu.source.levelv = l_sweep
        smu.source.rangev = math.max(math.abs(start), math.abs(stop))
    else
        smu.source.func = smu.OUTPUT_DCAMPS
        smu.source.leveli = l_sweep
        smu.source.rangei = math.max(math.abs(start), math.abs(stop))
    end
    smu.source.output = smu.OUTPUT_ON
    smu.measure.autozero = smu.AUTOZERO_OFF
    for l_j = 1,points do
        delay(stime)                  -- Wait desired settling time.
        if l_measiv == 1 then
            smu.measure.i(smu.nvbuffer1)  -- Measure current and store in reading buffer.
        elseif l_measiv == 2 then
            smu.measure.v(smu.nvbuffer2)  -- Measure voltage and store in reading buffer.
        elseif l_measiv == 3 then
            smu.measure.iv(smu.nvbuffer1,smu.nvbuffer2)  -- Measure current & voltage and store in reading buffers.
        end
        if l_measr then
            smu.measure.r(nvbuffer3)  -- Measure resistance and store in reading buffer.
        end
        if l_measp then
            smu.measure.p(nvbuffer4)  -- Measure power and store in reading buffer.
        end
        l_sweep = l_sweep + l_dstep
        if l_disptrack then
            display.clear()
            display.settext(l_j .. ": " .. l_sweep .. l_typ .. "  " .. l_dstep .. " - ")
        end
        if l_typ == "V" then
            smu.source.levelv = l_sweep
        else
            smu.source.leveli = l_sweep
        end
    end
    delay(stime)                  -- Wait desired settling time.
    if l_measiv == 1 then
        smu.measure.i(smu.nvbuffer1)  -- Measure current and store in reading buffer.
    elseif l_measiv == 2 then
        smu.measure.v(smu.nvbuffer2)  -- Measure voltage and store in reading buffer.
    elseif l_measiv == 3 then
        smu.measure.iv(smu.nvbuffer1,smu.nvbuffer2)  -- Measure current & voltage and store in reading buffers.
    end
    if l_measr then
        smu.measure.r(nvbuffer3)  -- Measure resistance and store in reading buffer.
    end
    if l_measp then
        smu.measure.p(nvbuffer4)  -- Measure power and store in reading buffer.
    end
    if l_typ == "V" then
        smu.source.levelv = stop
    else
        smu.source.leveli = stop
    end
    display.clear()
    display.screen = l_d_screen
    return points
end

function AbortScript(msg, screen)
    --Abort script on nil (typically exit keypress)
    display.clear() --clear display
    display.settext("Script Aborted " .. msg)
    delay(2)
    display.clear() --clear display
    display.screen = screen --show default screen
    exit() --abort script
end --function AbortScript()

display.clear()
display.settext("loaded scripts: ")
        """
        self.budget.set_slack(self, len(msg)*0.1)
        self.inst.write(self.scriptin(msg))
        self.has_scripts = True
        self.budget.set_slack(self)

    def com_recover(self, fix=False):
        """Detect & attempt to recover out of step communication (maybe after timeout).

        can lose coherency between read request and data, usually because of Timeout
        this routine can diagnose such loss of coherency and attempt to fix it, when fix=Tru
        """
        self.budget.set_slack(self)
        ires = None
        for i in range(1, 10):
            self.inst.write('print({})'.format(i))
            res = self.inst.read()
            try:
                ires = int(float(res))
                print("For {} got {}".format(i, ires))
                if i in [5, 6, 7] and fix:
                    diff = i - ires
                    if diff > 0:
                        print("See offset {}".format(diff))
                        for j in range(diff):
                            consume = self.inst.read()
                            print("Consumed '{}'".format(consume))
            except Exception:
                print("For {} got {}".format(i, res))
        return (ires == i)
