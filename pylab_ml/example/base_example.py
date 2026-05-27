
from pylab_ml.base_instrument import logger
from pylab_ml.base_instrument import Instrument


class Example (Instrument):
    """ An example class that inherits from Instrument. It demonstrates how to use the common functions and logging features provided by the base class. """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
