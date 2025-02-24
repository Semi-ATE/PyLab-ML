

import gc
import inspect


"""ident package, provides Ident() class for multiple inheritance 'identity' functionality
and stand-alone get_names() function to get list of assignemt identifiers"""


def find_names(obj):
    """find_names(obj) returns list of identifiers strings, lhs of = assignments to obj"""
    frame = inspect.currentframe()
    for frame in iter(lambda: frame.f_back, None):
        frame.f_locals
    obj_names = []
    for referrer in gc.get_referrers(obj):
        if isinstance(referrer, dict):
            for k, v in referrer.items():
                if v is obj:
                    obj_names.append(k)
    return obj_names


class Ident():

    """Ident class to determine identity of identifiers to which class instances assigned"""

    def find_names(self):
        """find_names() returns list of identifiers strings, lhs of = assignments"""
        frame = inspect.currentframe()
        for frame in iter(lambda: frame.f_back, None):
            frame.f_locals
        obj_names = []
        for referrer in gc.get_referrers(self):
            if isinstance(referrer, dict):
                for k, v in referrer.items():
                    if v is self:
                        obj_names.append(k)
        return obj_names
