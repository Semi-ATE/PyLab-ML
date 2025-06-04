"""Interface to the Digital Multimeter (DMM) NI PXIe-40xx (e.q. 4081).

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>

"""
import os
from pylab_ml.collate_instrument import Interface
from pylab_ml.base_instrument import InvalidInstrumentConnection
from pylab_ml.baseclass.base_natinst import NatInst
from pylab_ml.base_instrument import logger
import matplotlib.pyplot as plt
import hightime


class PXIe40xx(NatInst):
    """Interface to the Digital Multimeter (DMM) NI PXIe-40xx (e.q. 4081).

    .. image:: ../static/pxie_4081.jpg

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    todo::

    | in work
    | only base functions implemented
    | for more properties or functios see:    https://nimi-python.readthedocs.io/en/master/nidmm.html
    | call the misssing function with dmm.inst.functionname

    The PXI-4081 can measure voltage and current precisely

    """

    try:
        import nidmm

        has_nidmm = True
    except ImportError:
        has_nidmm = False
        if os.sys.platform != "win32":
            logger.error("import nidmm not found")
        else:
            logger.info("no import nidmm can be found on non Windows platforms")

    # create functions or proberty and wrap it to the inst.funcname:
    # if state != necessary state -> switch to the necessary state
    #  proberty/function name -> inst.funcname (get,set)    , range,    call functions
    #                                                         range : None, Enum or range value
    #                                                         call functions: see help in attributes

    _properties = {
        "auto_zero": ("auto_zero", "backend.AutoZero", {"sac": "checkstate(uncommitted)"}),
        "range": ("range", None, {"sac": "checkstate(uncommitted)"}),
        "aperture_time_units": ("aperture_time_units", "backend.ApertureTimeUnits", {"sac": "checkstate(uncommitted)"}),
        "aperture_time": ("aperture_time", None, {"sac": "checkstate(uncommitted)"}),
        "adc_calibration": ("adc_calibration", "backend.ADCCalibration", {"sac": "checkstate(uncommitted)"}),
        "dc_noise_rejection": ("dc_noise_rejection", "backend.DCNoiseRejection", {"sac": "checkstate(uncommitted)"}),
        "function": ("function", "backend.Function", {"sac": "checkstate(uncommitted)"}),
        "operation_mode": ("operation_mode", "backend.OperationMode", {"sac": "checkstate(uncommitted)"}),
        "trigger_source": ("trigger_source", "backend.TriggerSource", {"sac": "checkstate(uncommitted)"}),
        "sample_interval": ("sample_interval", [0, 149], {"sac": "checkstate(uncommitted)"}),
        "sample_trigger": ("sample_trigger", "backend.SampleTrigger", {"sac": "checkstate(uncommitted)"}),
        "sample_count": ("sample_count", None, {"sac": "checkstate(uncommitted)"}),
        "waveform_rate": ("waveform_rate", [10, 1_800_000], {"sac": "checkstate(uncommitted)"}),
        "waveform_points": ("waveform_points", [1, 18_000_000], {"sac": "checkstate(uncommitted)"}),
    }

    interchoices = [Interface.pxie]

    # def __init__(self, addr=None, channels='0', identify=False, instName=None):
    def __init__(self, addr=None, identify=False, instName=None):
        """Initialise.

        Args:
           addr (string):
              name from the PXI-Slot e.q. 'PXI1Slot3' or 'SMU'.
           identify (bool, optional):
              Defaults to False.
           instName (string, optional):
              Instance Name from top.

        Example: Initialization
           >>> dmm = PXIe41xx('PXI1Slot5',instName='dmm')   # connect and initialize instrument

        Example: Current measurement
           >>> i = dmm.current              # measure (supply) current

        Example: Voltage measurement
           >>> v = dmm.voltage              # measure voltage

        """
        if not self.has_nidmm:
            msg = "\nPXIe4081 not usable!! missing nidcpower\n"
            msg = msg + "for installing nidcpower:\n"
            msg = msg + "    Start anaconda prompt and write: python –m pip install nidmm\n"
            msg = msg + "For more infomation see:   http://nimi-python.readthedocs.io\n"
            raise InvalidInstrumentConnection(msg)
        # kwargs = {"addr": addr, "channels": channels, "backend": self.nidmm, "identify": identify, "instName": instName}
        kwargs = {"addr": addr, "backend": self.nidmm, "identify": identify, "instName": instName}
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
        self.msg_row_col = (1, 20)

    def setup_inst(self):
        """Set setup instrument settings."""
        super().setup_inst()
        self.mqtt_all = ["voltage", "current"]
        channels = []
        try:
            for ch in range(0, self.inst.channel_count):
                channels.append(int(ch))
        except Exception:
            channels = [0]  # only one channel exist
        self.channels = channels
        self._create_channelinst(channels)
        self.channel = channels[0]

    def reset(self):
        """Reset, and set folowing attributes.

        * power_line_frequency = 50.0
        * aperture_time_units = POWER_LINE_CYCLES
        * aperture_time = 2
        * inst.auto_zero = OFF
        * dc_noise_rejection = SECOND_ORDER
        """
        super().reset()
        for inst in self.ch:
            if inst is not None:
                inst.powerline_freq = 50.0  # set power line frequency to 50Hz
                inst.aperture_time_units = self.nidmm.ApertureTimeUnits.POWER_LINE_CYCLES
                inst.aperture_time = 2  # set aperture time to 2 PLC
                inst.auto_zero = self.nidmm.AutoZero.OFF  # disable auto zero
                inst.adc_calibration = self.nidmm.ADCCalibration.AUTO
                inst.resolution_digits = 5.5
                try:  # not possible for PXI-4138
                    inst.dc_noise_rejection = self.nidmm.DCNoiseRejection.SECOND_ORDER  # set dc noise rejection to "second order"
                except Exception:
                    pass

    # ----------------------------------------------------------
    # doc strings for _properties, propertie themselve will create form dictionary _properties
    @property
    def aperture_time(self):
        """Specifiy the measurement aperture time for the channel configuration.

        Aperture time is specified in the units set by the aperture_time_units property
        see: http://nimi-python.readthedocs.io/en/master/nidmm/class.html#aperture-time
        """

    @property
    def aperture_time_units(self):
        """Specifiy the units of the aperture_time property for the channel configuration.

        | SECONDS or POWER_LINE_CYCLES.
        | see: http://nimi-python.readthedocs.io/en/master/nidmm/class.html#aperture-time-units
        """

    @property
    def auto_zero(self):
        """Get or set auto_zero.

        | AUTO = The drivers chooses the AutoZero setting based on the configured method  and resolution.
        | OFF  = Disables AutoZero.
        | ON   = The DMM internally disconnects the input signal following each measurement  and takes a zero reading. It then subtracts the zero reading from the  preceding reading.
        | ONCE = The DMM internally disconnects the input signal for the first measurement  and takes a zero reading. It then subtracts the zero reading from the first  reading and the following readings.
        """

    @property
    def adc_calibration(self):
        """Get or set adc_calibration.

        AUTO = The DMM enables or disables ADC calibration for you.
        OFF  = The DMM does not compensate for changes to the gain.
        ON   = The DMM measures an internal reference to calculate the correct gain for the  measurement.
        """

    @property
    def function(self):
        """Get or set measurement method.

        | DC_VOLTS =    DC Voltage
        | AC_VOLTS =    AC Voltage
        | DC_CURRENT =  DC Current
        | AC_CURRENT =  AC Current
        | TWO_WIRE_RES  = 2-Wire Resistance
        | FOUR_WIRE_RES = 4-Wire Resistance
        | FREQ = Frequency
        | PERIOD = Period
        | TEMPERATURE = tempearture,  NI 4065, NI 4070/4071/4072, and NI 4080/4081/4182 supported.
        | AC_VOLTS_DC_COUPLED = AC Voltage with DC Coupling
        | DIODE = Diode
        | WAVEFORM_VOLTAGE = Waveform voltage
        | WAVEFORM_CURRENT = Waveform current
        | CAPACITANCE = Capacitance
        | INDUCTANCE =    Inductance

        see https://nimi-python.readthedocs.io/en/master/nidmm/class.html#function

        """

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

    @property
    def voltage(self):
        """Get voltage."""
        self.inst.function = self.nidmm.Function.DC_VOLTS
        return float(self.read)

    @property
    def current(self):
        """Get current."""
        self.inst.function = self.nidmm.Function.DC_CURRENT
        return float(self.read)

    @property
    def read(self):
        """Get measurement from measurement method."""
        value = self.inst.read(1)
        return float(value)

    def measure(self, nsamples):
        """Start to fetch data from the DMM.

        Parameters
        ----------
        nsamples : int
            Number of Data-points to fetch.

        Returns
        -------
        time : list
            Contains list of Time values..
        voltage : list
            Contains list of Voltage values..

        """
        self.inst.send_software_trigger()
        voltage = self.inst.fetch_waveform(nsamples, maximum_time=hightime.timedelta(milliseconds=3000))

        sample_rate = self.inst.waveform_rate
        time = []
        for i in range(0, nsamples):
            temp = i / sample_rate
            time.append(temp)

        return time, voltage

    def plot_dmm_data(self, time, voltage):
        """Plot graph between Time and Voltage.

        Parameters
        ----------
        time : list
            Input a list of Time values for x-axis..
        voltage : list
            Input a list of Voltage values for y-axis..

        Returns
        -------
        None.

        """
        plt.figure(figsize=(6.4, 4.8), dpi=300)
        plt.plot(time, voltage, "ro", markersize=0.1, alpha=0.1)
        plt.title("DMM Measurements")
        plt.xlabel("Time (s)")
        plt.ylabel("Voltage (V)")
        plt.grid(linestyle="--")
        plt.show()
        pass


if __name__ == "__main__":
    from pylab_ml.base_instrument import logsetup

    logsetup()

    dmm = PXIe40xx("PXI1Slot5", instName="dmm")

    dmm.abort()

    # Change the Operation mode and operation function
    dmm.operation_mode = "WAVEFORM"
    dmm.function = "WAVEFORM_VOLTAGE"
    dmm.dc_noise_rejection = "AUTO"

    # Edit the Trigger properties
    dmm.inst.range = 10
    dmm.trigger_source = "SOFTWARE_TRIG"
    dmm.sample_trigger = "SOFTWARE_TRIG"

    # Set the Waveform Acquisition properties
    dmm.waveform_rate = 1_800_000
    dmm.waveform_points = 1_000_000  # Time of Fetch = (waveform_points / waveform_rate)
    # dmm.sample_interval = 0.2
    # dmm.inst.sample_count = 5
    # dmm.inst.trigger_count = 3

    dmm.initiate()
    time, voltage = dmm.measure(dmm.waveform_points)
    dmm.abort()

    dmm.plot_dmm_data(time, voltage)

    dmm.close()

    # print("voltage= {} V".format(dmm.voltage))
    # print("current= {} mA".format(dmm.current * 1000))
