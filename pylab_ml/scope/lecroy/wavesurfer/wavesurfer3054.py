
from pylab_ml.base_instrument import logger
from pylab_ml.collate_instrument import Interface
from pylab_ml.scope.lecroy.wavesurfer.base_wavesurfer import WavesurferLecroyGenericScope


class Wavesurfer3054 (WavesurferLecroyGenericScope):

    interchoices = [Interface.tcpip]

    def __init__(self, addr=None, interface=None, hostname=None, port=None, instName=None):
        kwargs = {"addr": addr, "interface": interface, "hostname": hostname, "port": port, "instName": instName}
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
