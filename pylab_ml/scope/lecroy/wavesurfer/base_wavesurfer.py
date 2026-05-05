
from pylab_ml.base_instrument import logger
from pylab_ml.scope.lecroy.base_lecroy import Lecroy, LecroyGenericScope


class Wavesurfer (Lecroy):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))


class WavesurferLecroyGenericScope (LecroyGenericScope):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
