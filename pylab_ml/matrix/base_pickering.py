"""Base Class, Interface to the Pickering Matrix Card.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>

"""

from pylab_ml.base_instrument import logger
from pylab_ml.collate_instrument import Interface
from pylab_ml.base_instrument import Instrument
from pylab_ml.matrix import Pipx40


def findcard():
    """Find address for Pickering Card.

    Returns:
       int:
          | -1 if no card found
          | addr if card found
          | -1 and display addr if more than 1 card found.

    """
    base = Pipx40.pipx40_base()                   # Initialising Base Class
    CountFreeCards = base.CountFreeCards()        # search for available cards
    if CountFreeCards == 0:
        logger.info('{}: no card found')
        addr = -1
    elif CountFreeCards == 1:
        RsrcString = base.FindFreeCards()[0]
        # addr=int(RsrcString.split('::')[1])
        logger.info('found card addr:{}'.format(RsrcString))
        addr = RsrcString
    else:
        RsrcString = base.FindFreeCards()
        logger.info('found more than one card ')
        for i in range(0, base.CountFreeCards()):
            print(b', '.join(RsrcString[i]))
        addr = -1
    return addr


class Pickering (Instrument):
    """Base Class, Interface to the Pickering Matrix Card.

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    The Pickering baseclass can connect to Pickering Matrix Card

    """

    def __init__(self, **kwargs):
        """Initialise.

        Initialization arguments:
           addr (int):
              interface PXIslot address
        interface (dev_interface.Instrument):
           pxie


        Example: Initialization
           >>> instrument = NatInst(addr=3)     # PXIe slot address
           >>> instrument.init()                # connect and initialize instrument

        """
        if not hasattr(self, 'interchoices'):
            self.interchoices = [Interface.pxie]
        self.is_local = False
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
        self.com._init(self)

    def findcard(self):
        """Find address for Pickering Card.

        Returns:
           int:
              | -1 if no card found
              | addr if card found
              | -1 and display addr if more than 1 card found.
        """
        self.base = Pipx40.pipx40_base()                  # Initialising Base Class
        CountFreeCards = self.base.CountFreeCards()       # search for available cards
        if CountFreeCards == 0:
            logger.info('{}: no card found'.format(self.__class__.__name__))
            addr = -1
        elif CountFreeCards == 1:
            RsrcString = self.base.FindFreeCards()[0]
            # addr=int(RsrcString.split('::')[1])
            logger.info('{}: found card addr:{}'.format(self.__class__.__name__, RsrcString))
            addr = RsrcString
        else:
            RsrcString = self.base.FindFreeCards()
            logger.info('{}: found more than one card '.format(self.__class__.__name__))
            for i in range(0, self.base.CountFreeCards()):
                print(b', '.join(RsrcString[i]))
            addr = -1
        return addr

    def reset(self):
        """Reset."""
        self.budget.set_slack(self)
        self.inst.Reset()

    def clear(self):
        """Clear error status."""
        self.inst.clear()

    def close(self):
        """Close connection to Pickering device."""
        err = 0
        if self.inst is not None:
            err = self.inst.Close()
        if err != 0:
            self.message(self._error_message(err))
        super().close()
        return

    def error_list(self):
        """List of outstanding errors."""
        errorlist = self.inst.Diagnostic()
#        errors = errormsgs[0]
#        codes =errormsgs[1]
#        errorlist = []
#        for c,m in zip(codes, errors):
#            print("{} : {}".format(c,m))
#            errorlist.append((c,m))
        return errorlist

    def message(self, message=None):
        """Device has no display, message display to logger."""
        if message is not None:
            logger.debug(message)

    @property
    def id(self):
        """Get the id from the device."""
        err, msg = self.inst.GetCardId()
        if err != 0:
            self.message(self._error_message(err))
            msg = ''
        return msg

    def local(self):
        """Not possible, always remote control."""
        logger.info("set local not possible, always remote control")
        self.is_local = False
