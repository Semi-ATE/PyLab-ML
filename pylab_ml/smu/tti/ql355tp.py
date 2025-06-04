"""Interface to the Power supply unit TTi QL355TP.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>

"""

from pylab_ml.collate_instrument import Interface
from pylab_ml.smu.tti.base_tti import TTI
from pylab_ml.base_instrument import logger


class QL355TP(TTI):
    """Interface to the Power supply unit TTi QL355TP.

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    .. image:: ../static/ql355tp.jpg

    The QL355TP can
        supply two voltage sources and limit its current

        :download:`Manual  <../../manuals/QL355_QL355P_QL564+QL564P_Instruction_Manual-Iss9.pdf>`

    *Examples:*
       * common for QL355TP: :download:`examples/smu/ql355tp.py <../../../examples/smu/ql355tp.py>`

    """

    interchoices = [Interface.usbserial, Interface.gpib]

    def __init__(self, addr=None, interface=None, backend=None, identify=True, instName=None):
        """
        Connect and initialize.

        Args:
           addr (int):
              interface address
           interface (Interface):
              | To select the bus type, the same bus must also be selected on the instrument.
                For selection : Control 2, SHIFt 6 and then make the right selection with the rotary wheel.
              * gpib
              * usbserial:
                 | for serial or usb
                 | The serial bus only works with a special cable (rts must be connect to cts)
                 | USB works only with windows. Please install the driver 'instruments/smu/tti/TTI_USB_FTDI-v2_12_16'
           backend (str):
              visa backend is either '@ni' for NI-Library or
              '@py' for pure python pyvisa-py backend.
              On default it uses '@ni' on win32 and '@py' on
              other platforms.
           instName (string):
              Instance Name from top.

        Example: Initialization
           >>> vdd = QL355TP(11, 'vdd')     # GPIB address=11
           >>> vdd.init()                   # connect and initialize instrument with 2 channels

        Example: Config power supply 1+2 and enable the output
           >>> vdd[0].voltage = 5.0           # voltage (@channel=0) = 5V
           >>> vdd[0].current_lim = 0.01      # current limit = 10mA
           >>> vdd[0].onoff = 1               # enable output 0
           >>> vdd[1].voltage = 6.3           # voltage (@channel=1) = 6.3V
           >>> vdd[1].current_lim = 0.58      # current limit = 580mA
           >>> vdd[1].onoff = 1               # enable output 0

        """
        kwargs = {"addr": addr, "interface": interface, "backend": backend, "identify": identify, "instName": instName}
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))

    def setup_inst(self):
        """
        Start setup instrument settings, called from class instruments.

        Create 2 channels
        """
        super().setup_inst()
        self.channels = [0, 1]

    @property
    def v_range(self):
        """
        Get/Set the operating Output-Value-Range for actual Channel.

        |  0 = 15V/5A' : Voltage 0 to 15 V / Current 0 to 5 A
        |  1 = 35V/3A' : Voltage 0 to 35 V / Current 0 to 3 A
        |  2 = 35V/500mA : Voltage 0 to 35 V / Current 0 to 500 mA
        """


if __name__ == '__main__':
    from pylab_ml.base_instrument import logsetup

    logsetup()

    smu = QL355TP(8, Interface.usbserial, instName='smu')
    # smu = QL355TP(5, Interface.usbserial, instName='smu')
    # smu = QL355TP(11, instName='smu')           # Interface.gpib is default
    smu.init()

    # smu[0,2].voltage = 1.1      # not running yet
    # smu[0:1].voltage = 1.1      # "
    smu[0].voltage = 1.1
    smu[1].voltage = 2.2
    smu[0].voltage
    smu[1].voltage
    smu[0].current
    smu[1].current
    smu[0].i_clamp
    smu[0].i_clamp = 0.456
    smu[0].i_clamp
    smu[1].v_range
    smu[1].v_range = 2
    smu[1].v_range
    smu[0].ovp
    smu[0].ovp = 20.8
    smu[0].ovp
    smu[1].ocp
    smu[1].ocp = 1.3
    smu[1].ocp
    smu[0].onoff
