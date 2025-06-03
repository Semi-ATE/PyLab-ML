import os
from pathlib import Path
import importlib

__author__ = "Christian Jung"
__copyright__ = "Copyright 2021, TDK Micronas"
__credits__ = ["Christan Jung"]
__email__ = "christian.jung@micronas.com"


class Functions():
    """

    """
    INSTRUMENT_INIT_ALL = 'init_all'
    INSTRUMENT_INIT = 'init'
    USER_PATH = 'units/tcc/source/python/'
    ERROMSG = {'ok': 'no errors'}

    def __init__(self):
        print('Functions.__init__ ')


    def init(self):
        print('Functions.init ')

    def do_import(self):
        print('Functions: do_import, test={}'.format(self.test))
        return False

    def do_export(self):
        print('Functions: do_export')
        return False

    def get_abort_reason(self):
        print('Functions: get_abort_reason')
        return self.errormsg

    def set_mqtt_client(self, mqtt):
        print('Functions: set_mqtt_client')
        pass

    def set_configuration_values(data):
        print('Functions: set_configuration_values')
        pass

    def apply_configuration(self, data):
        print("Functions: Configuration applied.")
