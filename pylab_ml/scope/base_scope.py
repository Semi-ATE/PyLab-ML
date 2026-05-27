from pylab_ml.base_instrument import logger
from pylab_ml.base_instrument import Instrument


class Scope(Instrument):
    """ Base class for oscilloscopes."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
