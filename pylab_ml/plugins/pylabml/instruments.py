"""
Plugin for the Pylab-Ml environment.

load the configuration-file.

TODO:
      actual: send self.log_info('$LOGGINGFILENAME$ as mqtt command
                          better: the application give this message... need the path and the top applikation name

     change apikey to
{"project path": "$WORKAREA/units/lab/source/python; $WORKAREA/units/lab.Win64/source/python/",
 "add path": "harness/",  "Network prefix": "//samba"}

"""
import os
import sys
from pathlib import Path
import importlib
# import inspect
from ate_common.logger import LogLevel
from ate_semiateplugins.hookspec import hookimpl
from pylab_ml.common import environment
from pylab_ml.common import projectsetup
from pylab_ml.misc import registermaster

__author__ = "Zlin526F"
__credits__ = ["Zlin526F"]
__email__ = "Zlin526F@github"
__version__ = '0.4.0'


class Plugin:

    @hookimpl
    def get_plugin_identification():
        return {
            "Name": "Pylab-Ml Reference Plugin",
            "Version": __version__
        }

    @hookimpl
    def get_importer_names():
        return [
            {"display_name": "Dummy Importer",
             "version": "0.0",
             "name": "Pylab-Ml.DummyImporter"}]

    @hookimpl
    def get_exporter_names():
        return [
            {"display_name": "Dummy Exporter",
             "version": "0.0",
             "name": "Pylab-Ml.DummyExporter"}]

    @hookimpl
    def get_equipment_names():
        return [
            {"display_name": "Dummy Equipment",
             "version": "0.0",
             "name": "Pylab-Ml.DummyEquipment"}]

    @hookimpl
    def get_devicepin_importer_names():
        return [
            {"display_name": "Dummy Pinimport",
             "version": "0.0",
             "name": "Pylab-Ml.DummyPinimport"}]

    @hookimpl
    def get_instrument_names():
        return [
            {"display_name": "Labor Instruments V" + __version__,
             "version": __version__,
             "manufacturer": "Semi-ATE Labor",
             "name": "Pylab-Ml.Instruments"}]

#    @hookimpl
#    def get_tester_names():
#        return [
#            {"display_name": "NI PXIe",
#             "version": "0.0",
#            "manufacturer": "TCC Micronas Labor",
#             "name": "Pylab-Ml.NIPXIe"}]

    @hookimpl
    def get_general_purpose_function_names():
        return [
            {"display_name": "Project Setup",
             "version": projectsetup.__version__,
             "manufacturer": "Semi-ATE Labor",
             "name": "Pylab-Ml.Setup"},
            {"display_name": "Registermaster",
             "version": registermaster.__version__,
             "manufacturer": "Semi-ATE Labor",
             "name": "Pylab-Ml.Registermaster"}
            ]

    @hookimpl
    def get_importer(importer_name):
        if "Pylab-Ml." in importer_name:
            print('Pylab-Ml.get_importer')
            return Instruments()

    @hookimpl
    def get_exporter(exporter_name):
        if "Pylab-Ml." in exporter_name:
            print('Pylab-Ml.get_exporter')
            return Instruments()

    @hookimpl
    def get_equipment(equipment_name):
        if "Pylab-Ml." in equipment_name:
            print('Pylab-Ml.get_equipment')
            return Instruments()

    @hookimpl
    def get_devicepin_importer(importer_name):
        if "Pylab-Ml." in importer_name:
            print('Pylab-Ml.get_equipment')
            return Instruments()

    @hookimpl
    def get_instrument(instrument_name: str, logger):
        if instrument_name == "Pylab-Ml.Instruments":
            return Instruments(logger)

    @hookimpl
    def get_instrument_proxy(instrument_name):
        if "Pylab-Ml." in instrument_name:
            print('Pylab-Ml.get_instrument_proxy')
            return Instruments()

#    @hookimpl
#    def get_tester(tester_name: str):
#        if tester_name == "Pylab-Ml.NIPXIe":
#            return NIPXIe.NIPXIe()

    @hookimpl
    def get_general_purpose_function(func_name: str, logger):
        if func_name == "Pylab-Ml.Setup":
            return projectsetup.ProjectSetup(logger)
        elif func_name == "Pylab-Ml.Registermaster":
            return registermaster.RegisterMaster(logger)

    @hookimpl
    def get_configuration_options(object_name):
        if object_name == "Pylab-Ml.Instruments":
            return ["Network prefix", "working directory", "add path"]
        elif object_name == "Pylab-Ml.Setup":
            return ["Network prefix", "working directory", "add path", 'instance name', 'filename']
        elif object_name == "Pylab-Ml.Registermaster":
            return ['instance name', 'filename', 'read mod write', 'reset value']


class Instruments:
    """
    get keyword from the api_key for configuration:
        PROJECT_PATH ->search for config/init-File for the instrument-configuration, delimiter=; -> use last valid path
        ADD_PATH  additional path, together with PROJECT_PATH e.q. harness/)
        NETWORK : „//samba“ will be use if running windows
        LOG_LEVEL  10,20,30 (default= 20)

        $name in paths-> replace with os.environ.get(name)

    Import configuration from Instrument configuration-files.

       1. search for file:
          1.1. my_config.py in your path                                                            = defines for individual instrument configuration (instantiation)
          1.2. when not found: search for project/version/harness/tb_project_config.py              = defines for project dependent instrument configuration (instantiation)
          1.3. when not found: search for computername.py in pytestsharing/instruments/init         = defines for Messplatz dependent instrument settings (this is normal case)
       2. if not my_config.py, search for:
          2.1 my_init.py in your path                                                               = individual init settings
          1.2. when not found: search in project/version/harness/tb_project_init.py                 = project specific initialisation, e.q. kind of communication: halapb, sti, msp
    use this files together as $$$HW_config.py

    - add $WORKAREA/units/lab/source/python/harness to path
    """

    FILE_PREFIX = 'tb_'
    INSTRUMENT_CONFIG = '_config.py'
    INSTRUMENT_INIT = '_init.py'
    ERROMSG = {'ok': 'no errors'}

    def __init__(self, logger):
        """Initialise."""
        self.logger = logger
        self.main_path = str(Path(sys.modules['__main__'].__file__).parent) + os.sep
        os.environ['PROJECT_PATH'] = str(Path(self.main_path).parent.parent.parent) + os.sep
        self.logger.debug = self.log_debug
        self.logger.measure = self.log_measure
        self.logger.info = self.log_info
        self.logger.warning = self.log_warning
        self.logger.error = self.log_error

    def log_debug(self, message: str):
        """Send the message with loglevel=debug to the logger."""
        self.logger.log_message(LogLevel.Debug(), message)

    def log_measure(self, message: str):
        """Send the message with loglevel=measure to the logger."""
        self.logger.log_message(LogLevel.Measure(), message)

    def log_info(self, message: str):
        """Send the message with loglevel=info to the logger."""
        self.logger.log_message(LogLevel.Info(), message)

    def log_warning(self, message: str):
        """Send the message with loglevel=warning to the logger."""
        self.logger.log_message(LogLevel.Warning(), message)

    def log_error(self, message: str):
        """Send the message with loglevel=error to the logger."""
        self.logger.log_message(LogLevel.Error(), message)

    def get(self):
        """Get the instrument handler."""
        return self.instruments

    def do_import(self):
        """Only empty dummy function."""
        self.log_warning('Pylab-Ml.Instruments: do_import only dummy function')
        return False

    def do_export(self):
        """Only empty dummy function."""
        self.log_warning('Pylab-Ml.Instruments: do_export only dummy function')
        return False

    def get_abort_reason(self):
        """Only empty dummy function."""
        self.log_warning('Pylab-Ml.Instruments: get_abort_reason only dummy function')
        return self.errormsg

    def set_mqtt_client(self, mqtt):
        """Only empty dummy function."""
        self.log_warning('Pylab-Ml.Instruments: set_mqtt_client only dummy function')
        pass

    def set_configuration_values(self, data):
        """Only empty dummy function."""
        self.log_warning('Pylab-Ml.Instruments: set_configuration_values only dummy function')
        pass

    def apply_configuration(self, data):
        # {"working directory": "$WORKAREA/units/lab/source/python; $WORKAREA/units/lab.Win64/source/python/",  the last exist path win
        #  "add path": "harness/",
        # "Network prefix": "//samba"}

        config = environment.replaceEnvs(data)
        project_path = self.main_path
        harness = ''
        path_prefix = ''
        working_dir = ''
        if 'Network prefix' in config and config['Network prefix'] != '' and os.name == "nt":
            path_prefix = config['Network prefix']
        if 'working directory' in config and config['working directory'] != '':
            for path in config['working directory'].split(';'):
                if os.path.exists(path):
                    working_dir = path
            os.environ['WORKING_DIR'] = working_dir
            if working_dir != '':
                self.log_info(f'Pylab-Ml.Instruments: get WORKING_DIR from the Plugin parameter-file = {working_dir}')
        if 'add path' in config and config['add path'] != '':
            harness = config['add path']
        self.log_info('$LOGGINGFILENAME$ {};{}'.format(project_path, self.logger.get_log_file_information()['filename']))

        os.environ['NETWORK'] = path_prefix
        computername = os.environ.get('COMPUTERNAME')
        environment.environ_getpath(self, 'registermaster')      # replace environment for registermaster if os='nt'
        instruments = None
        project_path = os.environ['PROJECT_PATH']
        harness = working_dir + harness if working_dir != "" else str(Path(project_path).parent) + os.sep + harness
        sys.path.append(working_dir if working_dir != "" else str(Path(project_path).parent))
        os.environ['harness'] = harness
        # search for instrument definition file and after import, search for init-file:
        myfile = '$$$HW' + self.INSTRUMENT_CONFIG
        mypath = self.main_path
        with open(mypath + myfile, 'w') as f:
            f.write('# -*- coding: utf-8 -*-\n"""\n\n')
            f.write("Don't edit this file. It will be overwriten at runtime. Any manual edits will be lost\n")
            f.write('"""\n')
            f.write("import sys\n")
            f.write("logger = sys.argv[2]\n")
        self.log_info('Pylab-Ml.Instruments use:')
        found = []
        for filename in (self.INSTRUMENT_INIT, self.INSTRUMENT_CONFIG):
            if Path(mypath + 'my' + self.INSTRUMENT_CONFIG).is_file():                        # first search in your directory
                source = mypath + 'my' + self.INSTRUMENT_CONFIG
            elif Path(harness + self.FILE_PREFIX + 'project' + filename).is_file():     # search in project harness directory
                source = Path(harness + self.FILE_PREFIX + 'project' + filename)
            elif filename == self.INSTRUMENT_CONFIG:
                source = computername + '.py'
                if not Path(source).is_file() and found == []:
                    self.log_warning('                - no instrument definition found!')
                    self.log_warning(f'                  create your own my{self.INSTRUMENT_CONFIG} !')
                    continue
                elif found != []:
                    continue
            else:
                self.log_warning('Pylab-Ml.Instruments:  - no first initialisation found !')
                continue
            self.log_info('                - {}'.format(str(Path(source))))
            with open(mypath+myfile, 'a') as dest:
                with open(Path(source), 'r') as src:
                    lines = src.readlines()
                dest.writelines(lines)
            found.append(source)
            if str(source).split(os.sep)[-1].find('my') == 0:
                break
        if len(found) > 0:
            sys.argv.append('--labml')
            sys.argv.append(self.logger)
            pythonPath = '.'.join(mypath.upper().split(os.sep)[-3:])
            instruments = importlib.import_module(pythonPath + os.path.splitext(myfile)[0])
        self.path_prefix = path_prefix
        self.instruments = instruments
        self.log_info("Pylab-Ml.Instruments: apply_configuration()")
