import os
from pylab_ml.collate_instrument import Interface
from pylab_ml.base_instrument import InvalidInstrumentConnection
from pylab_ml.baseclass.base_natinst import NatInst
from pylab_ml.base_instrument import logger
from matplotlib import pyplot as plt
import unittest
import hightime


class PXIe51xx(NatInst):
    """Interface to the Oscilloscopes NI PXIe-51xx (e.q. 5122)

    until now only initialisation on poor basic functions
     for more function see: https://nimi-python.readthedocs.io/en/master/niscope.html
         call with:   scope.inst.thefunctionname

    Initialization arguments:
       addr
           name from the PXI-Slot e.q. PXI1Slot4
       instName
           instance Name from top

    Example: Initialization
       >>> scope = PXIe4138('PXI1Slot4',instName='scope')   # connect and initialize instrument

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

    Methods:
        reset()           reset
        identify()        instrument message, reflect address & interfade
        message("")       instrument message ("string") or ()
        close()           terminate interface
      missing:  get_waveform(n)   get waveform data from channel n
      missing:  trig_oneshot(t)   single measurement trigger to waveform or timeout after t s

    Properties:
     missing:   memsize

     missing:   tdiv
     missing:   tdelay
     missing:   trig_mode
     missing:   trig_channel

     missing:   channel
     missing:   trace
     missing:   vdiv
     missing:   offs
     missing:   waveform

    for more properties or functios see:    https://nimi-python.readthedocs.io/en/master/niscope.html
        scope.inst.functionname

    """

    try:
        import niscope

        has_scope = True
    except ImportError:
        has_scope = False
        if os.sys.platform != "win32":
            logger.error("import niscope not found")
        else:
            logger.info("no import niscope can be found on non Windows platforms")

    # Create functions or property and wrap it to the inst.funcname:
    # If state != necessary state -> switch to the necessary state
    # Property/Function name -> (inst.funcname (get,set), Range, Call_Functions)
    #                           inst.funcname (get,set): Available in 'https://nimi-python.readthedocs.io/en/master/niscope.html'
    #                           Range: None, Enum or Range value
    #                           Call_Functions: see help in attributes

    _properties = {
        # 'aperture_time_units': ('aperture_time_units',     'backend.ApertureTimeUnits',      {'sac': 'checkstate(uncommitted)'}),
        "probeAttenuation": ("probe_attenuation", [1, 100], None),
        "couplings": ("vertical_coupling", "backend.VerticalCoupling", None),
        "onoff": ("channel_enabled", {"on": True, "off": False, 1: True, 0: False, True: True, False: False}, None),
        "sampleRate": ("min_sample_rate", [2_000, 2_000_000_000], None),
        "numberOfRecords": ("horz_num_records", [1, 1_000_000_000], None),
        "numberOfPoints": ("horz_min_num_pts", [1, 1_000_000_000], None),
        "numberOfSamples": ("horz_sample_rate", None, None),
        "referencePosition": ("horz_record_ref_position", [0, 100], None),
        "enforceRealtime": ("horz_enforce_realtime", {"on": True, "off": False}, None),
        "triggerType": ("trigger_type", "backend.TriggerType", None),
        "triggerModifier": ("trigger_modifier", "backend.TriggerModifier", None),
        "triggerSource": ("trigger_source", {0: "0", 1: "1", "TRIG": "TRIG"}, None),
        "triggerHysteresis": ("trigger_hysteresis", [0, 100], None),
        "triggerLevel": ("trigger_level", [-100, 100], None),
        "triggerDelay": ("trigger_delay_time", [0.0, 171.8], None),
        "triggerHoldoff": ("trigger_holdoff", [0.0, 171.8], None),
        "triggerSlope": ("trigger_slope", "backend.TriggerSlope", None),
        "triggerCoupling": ("trigger_coupling", "backend.TriggerCoupling", None),
        "terminals": ("channel_terminal_configuration", "backend.TerminalConfiguration", None),
        "impedance": ("trigger_impedance", [50, 1000000], None),
        "bandwidth": ("max_input_frequency", {"Full": -1.0, "Default": 0.0, "20MHz": 20_000_000.0, "125MHz": 125_000_000.0}, None),
        "range": ("vertical_range", {0.04: 0.04, 0.1: 0.1, 0.2: 0.2, 0.4: 0.4, 1.0: 1.0, 2.0: 2.0, 4.0: 4.0, 10.0: 10.0, 20.0: 20.0, 40.0: 40.0}, None),
        "offset": ("vertical_offset", [-30, 30], None),
    }

    interchoices = [Interface.pxie]

    def __init__(self, addr=None, identify=False, instName=None):
        if not self.has_scope:
            msg = "\nPXIe50xx not usable!! missing nidscope\n"
            msg = msg + "for installing niscope:\n"
            msg = msg + "    Start anaconda prompt and write: python –m pip install niscope\n"
            msg = msg + "For more infomation see:   http://nimi-python.readthedocs.io\n"
            raise InvalidInstrumentConnection(msg)
        kwargs = {"addr": addr, "backend": self.niscope, "identify": identify, "instName": instName}
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
        self.msg_row_col = (1, 20)
        self.setup_inst()

        inputTimeOut = 10
        # minTimeOut = (self.numberOfSamples * (self.numberOfRecords + 1)) / self.sampleRate
        # self.timeout = max(inputTimeOut, minTimeOut)

    def setup_inst(self):
        """Setup instrument settings"""
        super().setup_inst()
        self.mqtt_all = [""]

        channels = []

        if self.channels is None:
            self.channels = "0,1"
            temp = self.channels.split(",")
            for ch in temp:
                channels.append(int(ch))
            self.channels = channels
            self._create_channelinst(channels)
            self.channel = channels[0]

    def measure(self, channel=[0, 1], num_of_record=1, start_record=0, num_of_samples=None, offset=0):
        """Start to fetch data from the Scope.

        Parameters
        ----------
        channel : TYPE, (list or int)
            DESCRIPTION. The default is [0, 1] to measure from both the channels. Can also give '0' or '1' to measure from separate channel.
        num_of_record : TYPE, int
            DESCRIPTION. The default is 1. Number of records to fetch. Use -1 to fetch all configured records.
        start_record : TYPE, int
            DESCRIPTION. The default is 0. Zero-based index of the first record to fetch.
        num_of_samples : TYPE, int
            DESCRIPTION. The default is None. The maximum number of samples to fetch for each waveform.
            If the acquisition finishes with fewer points than requested, some devices return partial data if the acquisition finished, was aborted.
            If it fails to complete within the timeout period, the method raises.
        offset : TYPE, int
            DESCRIPTION. The default is 0. Offset in samples to start fetching data within each record. The offset can be positive or negative.

        Returns
        -------
        x : list
            Contains list of Time values.
        y : list
            Contains list of Voltage values.

        """
        if isinstance(channel, list):
            channel_map = map(str, channel)
            temp = "-".join(list(channel_map))
        else:
            temp = str(channel)

        waveforms = self.inst.channels[temp].fetch(
            num_samples=num_of_samples, record_number=start_record, offset=offset, num_records=num_of_record, timeout=hightime.timedelta(seconds=20)
        )

        if isinstance(channel, int):
            x = []
            for i in range(0, len(waveforms[0].samples)):
                temp = i * waveforms[0].x_increment
                x.append(temp)
            y = waveforms[0].samples.tolist()

        elif len(channel) == 2:
            x1 = []
            x2 = []
            x = []
            y = []

            for i in range(0, len(waveforms[0].samples)):
                temp1 = i * waveforms[0].x_increment
                x1.append(temp1)
            y1 = waveforms[0].samples.tolist()

            for i in range(0, len(waveforms[1].samples)):
                temp2 = i * waveforms[1].x_increment
                x2.append(temp2)
            y2 = waveforms[1].samples.tolist()

            x.extend([x1, x2])
            y.extend([y1, y2])

        return x, y

    def plot_scope_data(self, time, voltage):
        """Plot graph between Time and Voltage.

        Parameters
        ----------
        time : list
            Input a list of Time values for x-axis.
        voltage : list
            Input a list of Voltage values for y-axis.

        Returns
        -------
        None.

        """
        if any(isinstance(i, list) for i in voltage):
            plt.figure(figsize=(6.4, 4.8), dpi=300)
            plt.plot(time[0], voltage[0], "bo", markersize=0.1, alpha=0.1, label="Channel 0")
            plt.plot(time[1], voltage[1], "ro", markersize=0.1, alpha=0.1, label="Channel 1")
            plt.title("Scope Measurements")
            plt.xlabel("Time (s)")
            plt.ylabel("Voltage (V)")
            plt.legend()
            plt.grid(linestyle="--")
            plt.show()
        else:
            plt.figure(figsize=(6.4, 4.8), dpi=300)
            plt.plot(time, voltage, "bo", markersize=0.1, alpha=0.1)
            plt.title("Scope Measurements")
            plt.xlabel("Time (s)")
            plt.ylabel("Voltage (V)")
            plt.grid(linestyle="--")
            plt.show()

    def reset(self):
        super().reset()


class PXIe5114(PXIe51xx):

    _properties = {
        "sampleRate": ("min_sample_rate", [200_000_000, 200_000_000], None),
        "bandwidth": ("max_input_frequency", {"Full": -1.0, "Default": 0.0, "20MHz": 20_000_000.0, "125MHz": 125_000_000.0}, None),
        "range": ("vertical_range", {0.04: 0.04, 0.1: 0.1, 0.2: 0.2, 0.4: 0.4, 1.0: 1.0, 2.0: 2.0, 4.0: 4.0, 10.0: 10.0, 20.0: 20.0, 40.0: 40.0}, None),
        "offset": ("vertical_offset", [-30, 30], None),
        # Max Offset values for Range values : {0.04: 0.8, 0.1: 0.8, 0.2: 0.8, 0.4: 0.8, 1.0: 8.0, 2.0: 8.0, 4.0: 8.0, 10.0: 30.0, 20.0: 25.0, 40.0: 15.0}
        "probeAttenuation": ("probe_attenuation", [1, 100], None),
        "couplings": ("vertical_coupling", "backend.VerticalCoupling", None),
        "output": ("channel_enabled", {"on": True, "off": False}, None),
        "numberOfRecords": ("horz_num_records", [1, 100_000], None),
        "numberOfPoints": ("horz_min_num_pts", [1, 100_000], None),
        "numberOfSamples": ("horz_sample_rate", None, None),
        "referencePosition": ("horz_record_ref_position", [0, 100], None),
        "enforceRealtime": ("horz_enforce_realtime", {"on": True, "off": False}, None),
        "triggerType": ("trigger_type", "backend.TriggerType", None),
        "triggerSource": ("trigger_source", {"CH1": "0", "CH2": "1", "CH3": "2", "CH4": "3"}, None),
        "triggerHysteresis": ("trigger_hysteresis", [0, 100], None),
        "triggerLevel": ("trigger_level", [-100, 100], None),
        "triggerDelay": ("trigger_delay_time", [0.0, 171.8], None),
        "triggerHoldoff": ("trigger_holdoff", [0.0, 171.8], None),
        "triggerSlope": ("trigger_slope", "backend.TriggerSlope", None),
        "triggerCoupling": ("trigger_coupling", "backend.TriggerCoupling", None),
        "terminals": ("channel_terminal_configuration", "backend.TerminalConfiguration", None),
        "impedance": ("trigger_impedance", [50, 1000000], None),
    }

    def __init__(self, addr=None, identify=False, instName=None):
        if not self.has_scope:
            msg = "\nPXIe51xx not usable!! missing nidscope\n"
            msg = msg + "for installing niscope:\n"
            msg = msg + "    Start anaconda prompt and write: python –m pip install niscope\n"
            msg = msg + "For more infomation see:   http://nimi-python.readthedocs.io\n"
            raise InvalidInstrumentConnection(msg)

        super().__init__(addr=addr, identify=identify, instName=instName)
        logger.debug("Class {}".format(self.__class__.__name__))
        self.msg_row_col = (1, 20)
        self.sampleRate = 200_000_000
        self.bandwidth = "125MHz"


class PXIe5122(PXIe51xx):

    _properties = {
        "sampleRate": ("min_sample_rate", [100_000_000, 100_000_000], None),
        "bandwidth": ("max_input_frequency", {"Full": -1.0, "Default": 0.0, "20MHz": 20_000_000.0, "100MHz": 100_000_000.0}, None),
        "range": ("vertical_range", {0.2: 0.2, 0.4: 0.4, 1.0: 1.0, 2.0: 2.0, 4.0: 4.0, 10.0: 10.0, 20.0: 20.0}, None),
        "offset": ("vertical_offset", [-5, 5], None),
        # Max Offset values for Range values : {0.2: 0.1, 0.4: 0.2, 1.0: 0.5, 2.0: 1.0, 4.0: 2.0, 10.0: 5.0, 20.0: 0}
        "probeAttenuation": ("probe_attenuation", [1, 100], None),
        "couplings": ("vertical_coupling", "backend.VerticalCoupling", None),
        "output": ("channel_enabled", {"on": True, "off": False}, None),
        "numberOfRecords": ("horz_num_records", [1, 100_000], None),
        "numberOfPoints": ("horz_min_num_pts", [1, 100_000], None),
        "numberOfSamples": ("horz_sample_rate", None, None),
        "referencePosition": ("horz_record_ref_position", [0, 100], None),
        "enforceRealtime": ("horz_enforce_realtime", {"on": True, "off": False}, None),
        "triggerType": ("trigger_type", "backend.TriggerType", None),
        "triggerSource": ("trigger_source", {"CH1": "0", "CH2": "1", "CH3": "2", "CH4": "3"}, None),
        "triggerHysteresis": ("trigger_hysteresis", [0, 100], None),
        "triggerLevel": ("trigger_level", [-100, 100], None),
        "triggerDelay": ("trigger_delay_time", [0.0, 171.8], None),
        "triggerHoldoff": ("trigger_holdoff", [0.0, 171.8], None),
        "triggerSlope": ("trigger_slope", "backend.TriggerSlope", None),
        "triggerCoupling": ("trigger_coupling", "backend.TriggerCoupling", None),
        "terminals": ("channel_terminal_configuration", "backend.TerminalConfiguration", None),
        "impedance": ("trigger_impedance", [50, 1000000], None),
    }

    def __init__(self, addr=None, identify=False, instName=None):
        if not self.has_scope:
            msg = "\nPXIe51xx not usable!! missing nidscope\n"
            msg = msg + "for installing niscope:\n"
            msg = msg + "    Start anaconda prompt and write: python –m pip install niscope\n"
            msg = msg + "For more infomation see:   http://nimi-python.readthedocs.io\n"
            raise InvalidInstrumentConnection(msg)

        super().__init__(addr=addr, identify=identify, instName=instName)
        logger.debug("Class {}".format(self.__class__.__name__))
        self.msg_row_col = (1, 20)
        self.sampleRate = 100_000_000
        self.bandwidth = "20MHz"


class PXIe5172(PXIe51xx):

    _properties = {
        "sampleRate": ("min_sample_rate", [250_000_000, 250_000_000], None),
        "bandwidth": ("max_input_frequency", {"Full": -1.0, "Default": 0.0, "20MHz": 20_000_000.0, "100MHz": 100_000_000.0}, None),
        "range": ("vertical_range", {0.2: 0.2, 0.4: 0.4, 1.0: 1.0, 2.0: 2.0, 4.0: 4.0, 10.0: 10.0, 20.0: 20.0, 40.0: 40.0}, None),
        "offset": ("vertical_offset", [-20, 20], None),
        # Max Offset values for Range values : {0.2: 0.5, 0.4: 0.5, 1.0: 0.5, 4.0: 4.5, 10.0: 4.5, 40.0: 20.0}
        "probeAttenuation": ("probe_attenuation", [1, 100], None),
        "couplings": ("vertical_coupling", "backend.VerticalCoupling", None),
        "output": ("channel_enabled", {"on": True, "off": False}, None),
        "numberOfRecords": ("horz_num_records", [1, 100_000], None),
        "numberOfPoints": ("horz_min_num_pts", [1, 100_000], None),
        "numberOfSamples": ("horz_sample_rate", None, None),
        "referencePosition": ("horz_record_ref_position", [0, 100], None),
        "enforceRealtime": ("horz_enforce_realtime", {"on": True, "off": False}, None),
        "triggerType": ("trigger_type", "backend.TriggerType", None),
        "triggerSource": ("trigger_source", {"CH1": "0", "CH2": "1", "CH3": "2", "CH4": "3"}, None),
        "triggerHysteresis": ("trigger_hysteresis", [0, 100], None),
        "triggerLevel": ("trigger_level", [-100, 100], None),
        "triggerDelay": ("trigger_delay_time", [0.0, 171.8], None),
        "triggerHoldoff": ("trigger_holdoff", [0.0, 171.8], None),
        "triggerSlope": ("trigger_slope", "backend.TriggerSlope", None),
        "triggerCoupling": ("trigger_coupling", "backend.TriggerCoupling", None),
        "terminals": ("channel_terminal_configuration", "backend.TerminalConfiguration", None),
        "impedance": ("trigger_impedance", [50, 1000000], None),
    }

    def __init__(self, addr=None, identify=False, instName=None):
        if not self.has_scope:
            msg = "\nPXIe51xx not usable!! missing nidscope\n"
            msg = msg + "for installing niscope:\n"
            msg = msg + "    Start anaconda prompt and write: python –m pip install niscope\n"
            msg = msg + "For more infomation see:   http://nimi-python.readthedocs.io\n"
            raise InvalidInstrumentConnection(msg)

        super().__init__(addr=addr, identify=identify, instName=instName)
        logger.debug("Class {}".format(self.__class__.__name__))
        self.msg_row_col = (1, 20)
        self.sampleRate = 250_000_000
        self.bandwidth = "20MHz"


class TestClass(unittest.TestCase):
    def test_probeAttenuation(self):
        scope.probeAttenuation = 10.0
        self.assertEqual(scope.probeAttenuation, 10.0)
        scope.probeAttenuation = 101.0
        self.assertNotEqual(scope.probeAttenuation, 101.0)

    def test_couplings(self):
        scope.couplings = "DC"
        self.assertEqual(scope.couplings, scope.niscope.VerticalCoupling.DC)

    def test_onoff(self):
        scope.onoff = "on"
        self.assertTrue(scope.inst.channel_enabled)
        scope[2].onoff = False
        self.assertFalse(scope.inst.channels[1].channel_enabled)

    def test_sampleRate(self):
        scope.sampleRate = 1_000_000
        self.assertEqual(scope.sampleRate, 1000000)

    def test_numberOfRecords(self):
        scope.numberOfRecords = 10
        self.assertEqual(scope.numberOfRecords, 10)
        scope.numberOfRecords = 100000
        self.assertEqual(scope.numberOfRecords, 100000)

    def test_numberOfPoints(self):
        scope.numberOfPoints = 100_000
        self.assertEqual(scope.numberOfPoints, 100000)
        scope.numberOfPoints = 100_000_000
        self.assertNotEqual(scope.numberOfPoints, 100000000)

    def test_referencePosition(self):
        scope.referencePosition = 10
        self.assertEqual(scope.referencePosition, 10)
        scope.referencePosition = 101
        self.assertNotEqual(scope.referencePosition, 101)

    def test_enforceRealtime(self):
        scope.enforceRealtime = "off"
        self.assertFalse(scope.inst.horz_enforce_realtime)

    def test_triggerType(self):
        scope.triggerType = "DIGITAL"
        self.assertEqual(scope.triggerType, scope.niscope.TriggerType.DIGITAL)

    def test_triggerSource(self):
        scope.triggerSource = "CH3"
        self.assertEqual(scope.triggerSource, str("CH3"))

    def test_triggerHysteresis(self):
        scope.triggerHysteresis = 10
        self.assertEqual(scope.triggerHysteresis, 10)
        scope.triggerHysteresis = 101
        self.assertNotEqual(scope.triggerHysteresis, 101)

    def test_triggerLevel(self):
        scope.triggerLevel = 10
        self.assertEqual(scope.triggerLevel, 10)
        scope.triggerLevel = 101
        self.assertNotEqual(scope.triggerLevel, 101)

    def test_triggerDelay(self):
        scope.triggerDelay = 50
        self.assertEqual(scope.triggerDelay, 50)
        scope.triggerDelay = 172
        self.assertNotEqual(scope.triggerDelay, 172)

    def test_triggerHoldoff(self):
        scope.triggerHoldoff = 75
        self.assertEqual(scope.triggerHoldoff, 75)
        scope.triggerHoldoff = 172
        self.assertNotEqual(scope.triggerHoldoff, 172)

    def test_triggerSlope(self):
        scope.triggerSlope = "FALLING"
        self.assertEqual(scope.triggerSlope, scope.niscope.TriggerSlope.FALLING)

    def test_triggerCoupling(self):
        scope.triggerCoupling = "HF_REJECT"
        self.assertEqual(scope.triggerCoupling, scope.niscope.TriggerCoupling.HF_REJECT)

    def test_terminals(self):
        scope.terminals = "SINGLE_ENDED"
        self.assertEqual(scope.terminals, scope.niscope.TerminalConfiguration.SINGLE_ENDED)

    def test_bandwidth(self):
        scope.bandwidth = "20MHz"
        self.assertEqual(scope.bandwidth, str("20MHz"))

    def test_range(self):
        scope.range = 20
        self.assertEqual(scope.range, 20)
        scope.range = 25
        self.assertNotEqual(scope.range, 25)
        scope.range = 50
        self.assertNotEqual(scope.range, 50)

    def test_offset(self):
        scope.offset = 15
        self.assertEqual(scope.offset, 15)
        scope.offset = 50
        self.assertNotEqual(scope.offset, 50)


if __name__ == "__main__":
    from pylab_ml.base_instrument import logsetup

    # import scope

    logsetup()

    scope = PXIe51xx("PXI1Slot4", instName="scope")
    scope.abort()

    # scope_5114 = PXIe5114('PXI1Slot4', instName='scope_5114')
    # scope_5122 = PXIe5122('PXI1Slot4', instName='scope_5122')
    # scope_5172 = PXIe5172('PXI1Slot4', instName='scope_5172')

    scope.onoff = "on"

    scope[1].range = 4.0
    scope[2].range = 20.0

    # scope.triggerSource = 0
    scope.bandwidth = "125MHz"
    scope.triggerType = "IMMEDIATE"
    scope.triggerSlope = "RISING"
    scope.triggerLevel = 0.5
    scope.triggerCoupling = "DC"

    scope.sampleRate = 100_000
    scope.numberOfPoints = 300_000
    scope.numberOfRecords = 1

    scope.initiate()
    # time, voltage = scope.measure(1, 5000, num_of_samples=4, filter='mfilter')
    time, voltage = scope.measure(0)
    scope.abort()
    scope.plot_scope_data(time, voltage)
    # unittest.main()

    scope.close()

    # scope_5114.close()
    # scope_5122.close()
    # scope_5172.close()
