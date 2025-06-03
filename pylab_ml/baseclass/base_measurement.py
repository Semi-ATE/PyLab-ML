"""Basic SMU class."""
from pylab_ml.base_instrument import logger
from pylab_ml.base_instrument import Instrument
import numpy as np


class Measure(Instrument):
    """Basic Measurement class."""

    def __init__(self, **kwargs):
        """Initialize the smu class."""
        self._instName = ''
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))

    @property
    def instName(self):
        """Return with instname or instname[ch] if it has channels."""
        if hasattr(self, '_channel') and isinstance(self.channels, list) and (len(self.channels) > 1 or
                                                                              (len(self.channels) == 1 and self.channels[0] != 0)):
            # return '{}[{}]'.format(self._instName, self._channel)
            return self._instName
        else:
            return self._instName

    @instName.setter
    def instName(self, value):
        self._instName = value

    @property
    def measurecnt(self):
        """Set/get the number of measurement to be carried out in a loop.

        TODO: this function is not running yet, it is only a dummy

        if the result == None than this function not implemented.
        The return value for the measurement is calculated togetheer with the mfilter setting.
        """
        return self._measurecnt

    @measurecnt.setter
    def measurecnt(self, value):
        self._measurecnt = value

    # @property
    # def mfilter(self):
    #     """Set/get the type of digital-filter for the result of measurment if measurecnt>1.

    #     TODO: this function is not running yet, it is only a dummy

    #     Returns:
    #         delete_min_max_values_and_average: same function as the laboratory matlab function with the same name...
    #     """
    #     return self._mfilter

    # @mfilter.setter
    # def mfilter(self, value):
    #     self._mfilter = value

    def mfilter(self, input):
        if isinstance(input, list):
            if len(input) >= 4:
                min_temp = min(input)
                max_temp = max(input)
                input.remove(min_temp)
                input.remove(max_temp)
                avg = np.mean(input)
            else:
                avg = np.mean(input)
        return avg

    @property
    def channel(self):
        """
        Set/get channel number if the instrument have more than one channel.

         you can also use:
            >>> vdd[0].voltage = 5           # set voltage from channel 0
            >>> vdd[1].current = 0.1         # set current from channel 1
            >>> v = vdd[1].voltage           # measure voltage from channel 1
        """
        return self._channel

    @channel.setter
    def channel(self, value):
        if value not in self.channels:
            logger.error('{!r}.channel := {} not initialise in channels list == {}\n   use last channel := {} !'.format(self.instName, value, self.channels, self.channel))
            return
        self._channel = value

    def __getitem__(self, key):
        """Set channel to key."""
        if isinstance(key, int):
            self.channel = key
            return self
        elif isinstance(key, slice):
            chlist = []
            start, stop, step = key.indices(len(self.channels))
            for ch in range(start, stop+1, step):
                if ch in self.channels:
                    chlist.append(ch)
            print("Error, sorry this doesn't work yet :-(")
            print(key, '->', chlist)
            # self.channel=chlist[0]
            self._chiter = iter(chlist)
            # return map([self[i] for i in chlist])
            # return map(self[i], chlist)
            return self
        elif isinstance(key, tuple):
            chlist = key
            print("Error, sorry, this doesn't work yet :-(")
            print(key, '->', chlist)
            return self
        return self

    def __iter__(self):
        """For interations."""
        self._chiter = iter(self.channels)
        return self

    def __next__(self):
        """For interations."""
        self.channel = next(self._chiter)
        return self

    def __contains__(self, key):
        """For interations."""
        if key in self.channels:
            return True
        else:
            return False

    def __len__(self):
        """Return with count of channels."""
        if hasattr(self, '_channel'):
            return len(self.channels)
        else:
            return 0
