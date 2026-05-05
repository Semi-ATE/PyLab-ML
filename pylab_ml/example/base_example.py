
from pylab_ml.base_instrument import logger
from pylab_ml.base_instrument import Instrument


class Example (Instrument):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
