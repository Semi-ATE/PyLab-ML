"""
This script defines the LecroyGenericScope class, which provides an interface to LeCroy Oscilloscopes.
The class allows users to control various settings of the oscilloscope and retrieve waveform data.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>

"""
import time
import numpy as np
import struct
import re
from pylab_ml.base_instrument import logger
from pylab_ml.scope.base_scope import Scope


class Lecroy (Scope):
    """ Base class for LeCroy Oscilloscopes. """

    def __init__(self, **kwargs):
        """ Initialize the Lecroy scope interface. """
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
        self.com._init(self)

    def reset(self):
        """ Reset the Lecroy scope. """
        self.inst.write('*RST')

    def message(self, message=None):
        """ Send a message to the Lecroy scope. """
        super().message()
        pass

    @property
    def id(self):
        """ Get the identification string of the Lecroy scope. """
        try:
            value = self.query('*IDN?')
        except Exception:
            value = ""
        return value


class LecroyGenericScope (Lecroy):
    """
    Interface to LeCroy Oscilloscopes.

    The Lecroy 'wavesurfer' & 'HBO with SENT option' Oscilloscopes can be driven over
    the network TCP/IP with this interface.

    Initialisation arguments:
        host : hostname, should by LeCroy serial number
        addr : IP_address, should hostname not be available
        port : scope TCP/IP port (1861 by default)

    Example: Initialization

        >>> scope = hwlib.lecroy.Scope("lcry4066n50407")

        >>> scope.trig_channel = 1
        >>> scope.trig_level = 1.5
        >>> scope.trig_slope = "POS"
        >>> scope.trig_mode = "norm"

        >>> scope.tdiv = 1e-3
        >>> scope.tdelay = -3e-3

        >>> scope.channel = 1
        >>> scope.trace = True
        >>> scope.vdiv = 1.0
        >>> scope.offs = 0

    Example: Coherent waveform grabbing

        >>> try:
        >>>    scope.trig_oneshot (0.5);
        >>> except scope.TriggerTimeout as err:
        >>>    print (err)
        >>> w1 = scope.get_waveform(2)
        >>> w2 = scope.get_waveform(2)
        >>> scope.trig_mode = scope.mode_before_oneshot

    Methods:
        reset()           reset
        identify()        instrument message, reflect address & interfade
        message("")       instrument message ("string") or ()
        close()           terminate interface
        get_waveform(n)   get waveform data from channel n
        trig_oneshot(t)   single measurement trigger to waveform or timeout after t s

    Properties:
        memsize
        id
        tdiv
        tdelay
        trig_slope
        trig_level
        trig_mode
        trig_channel
        channel
        trace
        vdiv
        offs
        waveform
    """

    def __init__(self, **kwargs):
        """ Initialize the LecroyGenericScope interface. """
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))

    def setup_inst(self):
        """ Set up the Lecroy scope with initial settings. """
        super().setup_inst()
        self.inst.write('COMM_HEADER OFF')
        self.channel_name = 'C1'
        self.mode_before_oneshot = None

    @property
    def id(self):
        """ Get the identification string of the Lecroy scope. """
        value = self.inst.query('*IDN?')
        return value

    def wait_until_idle(self, delay_ms=5):
        """
        Wait until the Lecroy scope is idle.

        Parameters
        ----------
            delay_ms : int
                The delay in milliseconds to wait between checks (default is 5 ms).

        Returns
        -------
            value : str
                The response from the scope indicating its idle status.
        """
        cmd = 'VBS? "return = app.WaitUntilIdle({})"'.format(delay_ms)
        value = self.inst.query(cmd)
        return value

    def fix_lecroy_trig(self):
        """
        Issue on LeCroy-wavesurfer, once active channel changed & used, trigger.

        Channel attribute (level & slope) changes are ignored!
        """
        tc = self.trig_channel
        ch = self.channel
        self.channel = tc
        self.trace = self.trace
        self.channel = ch

    @property
    def memsize(self):
        """ Get the memory size of the Lecroy scope. """
        value = self.inst.query('MSIZ?')
        return int(float(value))

    @memsize.setter
    def memsize(self, value):
        self.inst.write('MSIZ {}'.format(value))

    @property
    def tdiv(self):
        """ Get the time division of the Lecroy scope. """
        value = self.inst.query('TDIV?')
        return float(value)

    @tdiv.setter
    def tdiv(self, value):
        self.inst.write('TDIV {}'.format(float(value)))

    @property
    def tdelay(self):
        """ Get the trigger delay of the Lecroy scope. """
        value = self.inst.query('TRIG_DELAY?')
        return float(value)

    @tdelay.setter
    def tdelay(self, value):
        self.inst.write('TRIG_DELAY {}'.format(float(value)))

    @property
    def trig_slope(self):
        """ Get the trigger slope of the Lecroy scope. """
        value = self.inst.query('TRIG_SLOPE?')
        return value

    @trig_slope.setter
    def trig_slope(self, value):
        if isinstance(value, (int, float)):
            value = 'POS' if value > 0 else 'NEG'
        elif isinstance(value, bool):
            value = 'POS' if value else 'NEG'
        if 1:
            self.fix_lecroy_trig()
        self.inst.write('TRIG_SLOPE {}'.format(value))

    @property
    def trig_level(self):
        """ Get the trigger level of the Lecroy scope. """
        value = self.inst.query('TRIG_LEVEL?')
        return value

    @trig_level.setter
    def trig_level(self, value):
        if 1:
            self.fix_lecroy_trig()
        self.inst.write('TRIG_LEVEL {}'.format(float(value)))

    @property
    def trig_mode(self):
        """
        Get the trigger mode of the Lecroy scope. 
        Trigger mode is one of {'AUTO', 'NORM', 'SINGLE', 'STOP'}
        """
        value = self.inst.query('TRIG_MODE?')
        return value

    @trig_mode.setter
    def trig_mode(self, value):
        self.inst.write('TRIG_MODE {}'.format(value.upper()))

    @property
    def trig_channel(self):
        """ Get the trigger channel of the Lecroy scope. """
        value = self.inst.query('TRIG_SELECT?')
        channel_name = value.split(',')[2]
        if re.match("^C", channel_name):
            channel = value.split(',')[2][1]
            return int(channel)
        else:
            return channel_name

    @trig_channel.setter
    def trig_channel(self, value):
        if type(value) is int or re.match(r"\d", value):
            self.inst.write('TRIG_SELECT EDGE,SR,C{}'.format(int(value)))
        else:
            self.inst.write('TRIG_SELECT EDGE,SR,{}'.format(value))

    class TriggerTimeout(Exception):
        pass

    def trig_oneshot(self, timeout=1.0):
        """
        Trigger a single measurement and wait until it is complete or timeout.

        Parameters
        ----------
            timeout : float
                The maximum time to wait for the measurement to complete, in seconds.

        Raises
        ------
            TriggerTimeout
                If the measurement does not complete within the specified timeout.
        """
        start = time.monotonic()
        self.mode_before_oneshot = self.trig_mode
        self.inst.write('TRIG_MODE SINGLE')
        while self.inst.query('TRIG_MODE?') != "STOP":
            if (time.monotonic() - start > timeout):
                raise self.TriggerTimeout("Oneshot Trigger Timeout after {}s".format(timeout))

    @property
    def channel(self):
        """ Get the current channel of the Lecroy scope. """
        if re.match("^C", self.channel_name):
            channel = self.channel_name[1:]
            return int(channel)
        else:
            return self.channel_name

    @channel.setter
    def channel(self, value):
        if type(value) is int or re.match(r"\d", value):
            self.channel_name = "C{}".format(int(value))
        else:
            self.channel_name = value

    # per channel properties ###

    @property
    def trace(self):
        """ Get the trace state of the current channel. """
        value = self.inst.query('{}:TRACE?'.format(self.channel_name))
        return dict(ON=True, OFF=False)[value]

    @trace.setter
    def trace(self, value):
        value = 'ON' if value else 'OFF'
        self.inst.write('{}:TRACE {}'.format(self.channel_name, value))

    @property
    def vdiv(self):
        """ Get the voltage division of the current channel. """
        value = self.inst.query('{}:VDIV?'.format(self.channel_name))
        return float(value.split(':')[-1].strip('" '))

    @vdiv.setter
    def vdiv(self, value):
        self.inst.write('{}:VDIV {}'.format(self.channel_name, value))

    @property
    def offs(self):
        """ Get the offset of the current channel. """
        value = self.inst.query('{}:OFFSET?'.format(self.channel_name))
        return float(value.split(':')[-1].strip('" '))

    @offs.setter
    def offs(self, value):
        self.inst.write('{}:OFFSET {}'.format(self.channel_name, value))

    def _get_waveform(self, channel=None):
        """ 
        Get the waveform data from the specified channel.
        
        Parameters
        ----------
            channel : int or str, optional
                The channel to retrieve the waveform from. If None, uses the current channel (default is None).
                
        Returns
        -------
            voltage : np.ndarray
                The voltage values of the waveform.
            tdelta : float
                The time interval between samples.
            toffs : float
                The time offset of the waveform.
        """
        if channel is None:
            channel_name = self.channel_name
        elif type(channel) is int or re.match(r"\d", channel):
            channel_name = "C{}".format(int(channel))
        else:
            channel_name = channel
        meta = {}
        desc = self.inst.query("{}:INSPECT? WAVEDESC".format(channel_name))
        if not desc.startswith('"\r\nDESCRIPTOR_NAME    : WAVEDESC'):
            print('*** desc: {!r}'.format(desc))
            print('*** retry receiving description')
            desc = self.inst.read()
        for item in desc.split('\r\n'):
            name, sep, value = item.partition(':')
            if sep == ':':
                meta[name.strip()] = value.strip()
        gain = float(meta['VERTICAL_GAIN'])
        offs = float(meta['VERTICAL_OFFSET'])
        tdelta = float(meta['HORIZ_INTERVAL'])
        toffs = float(meta['HORIZ_OFFSET'])
        format = meta['COMM_TYPE']

        self.inst.write("{}:WF? DAT1".format(channel_name))
        chunks = []
        while 1:
            chunk = self.inst.read_chunk()
            if chunk.endswith(b'\n'):
                chunks.append(chunk.rstrip(b'\n'))
                break
            else:
                chunks.append(chunk)
        if self.debug:
            print('    get_waveform: c1 = {}'.format(chunks[0]))
            print('    get_waveform: c1 = {}'.format(chunks[1]))
        b = b''.join(chunks[2:])
        assert format.lower() == 'byte' or format.lower() == 'word'
        if format.lower() == 'byte':
            values = struct.unpack('{}b'.format(len(b)), b)
        if format.lower() == 'word':
            values = struct.unpack('{}h'.format(len(b)), b)
        voltage = gain * np.array(values) - offs
        return voltage, tdelta, toffs

    def get_waveform(self, channel=None):
        """
        Get the waveform data from the specified channel and return the time and voltage arrays.

        Parameters
        ----------
            channel : int or str, optional
                The channel to retrieve the waveform from. If None, uses the current channel (default is None).

        Returns
        -------
            t : np.ndarray
                The time values of the waveform.
            voltage : np.ndarray
                The voltage values of the waveform.
        """
        voltage, tdelta, toffs = self._get_waveform(channel)
        t = np.arange(len(voltage)) * tdelta + toffs
        return t, voltage

    @property
    def waveform(self):
        """ 
        Get the waveform data from the current channel and return the time and voltage arrays.
        
        Returns
        -------
            t : np.ndarray
                The time values of the waveform.
            voltage : np.ndarray
                The voltage values of the waveform.
        """
        voltage, tdelta, toffs = self._get_waveform()
        t = np.arange(len(voltage)) * tdelta + toffs
        return t, voltage

    @property
    def waveform_dt(self):
        """ 
        Get the waveform data from the current channel and return the voltage, time interval, and time offset.
        
        Returns
        -------
            voltage : np.ndarray
                The voltage values of the waveform.
            tdelta : float
                The time interval between samples.
            toffs : float
                The time offset of the waveform.
        """
        voltage, tdelta, toffs = self._get_waveform()
        return voltage, tdelta, toffs
