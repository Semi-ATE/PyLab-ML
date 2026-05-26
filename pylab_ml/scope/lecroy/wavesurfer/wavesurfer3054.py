
from pylab_ml.base_instrument import logger
from pylab_ml.collate_instrument import Interface
from pylab_ml.scope.lecroy.wavesurfer.base_wavesurfer import WavesurferLecroyGenericScope


class Wavesurfer3054 (WavesurferLecroyGenericScope):
    """" Interface to LeCroy Wavesurfer 3054 Oscilloscope. """

    interchoices = [Interface.tcpip]

    def __init__(self, addr=None, interface=None, hostname=None, port=None, instName=None):
        """ 
        Initialize the Wavesurfer3054 scope interface. 
        
        Parameters
        ----------
            addr : str
                IP address of the scope.
            interface : Interface
                Interface to use for communication (e.g., Interface.tcpip).
            hostname : str
                Hostname of the scope (should be LeCroy serial number).
            port : int
                Port number for communication.
            instName : str
                Instrument name.
        """
        kwargs = {"addr": addr, "interface": interface, "hostname": hostname, "port": port, "instName": instName}
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
