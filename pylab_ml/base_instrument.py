import sys
import os
try:
    import grp
except ImportError:
    pass

import time

from abc import ABC, abstractmethod
from serial.tools import list_ports
import logging
from pylab_ml.common.singleton import Singleton
from pylab_ml.dummy import Dummy
from pylab_ml.ident import Ident
from pylab_ml.collate_instrument import Interface, DefInter, CollateInstrument
from pylab_ml.scope.lecroy.vicp import VICP
from pylab_ml.common.mqtt_client import mqtt_deviceattributes, mqtt_init


def measure(self, message, *args, **kws):
    if self.isEnabledFor(MEASURE_LEVEL_NUM):
        # Yes, logger takes its '*args' as 'args'.
        self._log(MEASURE_LEVEL_NUM, message, args, **kws)


def choicelogger():
    for px in sys.argv:
        if px == '--labml':
            idx = sys.argv.index(px)
            logger = sys.argv[idx+1]
            return logger
    return logging.getLogger(__name__)


MEASURE_LEVEL_NUM = 15
logging.addLevelName(MEASURE_LEVEL_NUM, "MEASURE")
logging.MEASURE = MEASURE_LEVEL_NUM
logging.Logger.measure = measure
logger = choicelogger()
mqttc = mqtt_init(typ='instrument', logger=logger)   # TODO: wenn base_instrument importiert wird dann wird mqtt initialisiert!! das darf so nicht sein!!
                                                           # da dann der Typ dann nicht mehr geändert werden kann!!
_createDummyifInvalid = False


def createDummyifInvalid(val):
    """
    Global switch to create Dummy instance if error occured in instrument._init or instrument have no connection.

    Parameters
    ----------
    val : bool
        True/False(default)

    Returns
    -------
    None.
    """
    global _createDummyifInvalid
    _createDummyifInvalid = val


def mqttclose():
    mqttc.close()


def logsetup():
    logger.setLevel(logging.DEBUG)

    # remove existing handlers
    for handler in logger.handlers:
        print(handler)
        logger.removeHandler(handler)
    logger.handlers = []

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)

    # create file handler and set level to debug
    fh = logging.FileHandler('instrument.log', 'w')
    fh.setLevel(logging.MEASURE)

    # create formatter
    ch_formatter = logging.Formatter('%(levelname)s - %(message)s')
    fh_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # add formatter to ch & fh
    ch.setFormatter(ch_formatter)
    fh.setFormatter(fh_formatter)

    # add ch & fh to logger
    logger.addHandler(ch)
    logger.addHandler(fh)

    try:
        logger.ipython_shell = get_ipython().__class__.__name__
        # ZMQInteractiveShell -- Jupyter notebook or qtconcole
        # TerminalInteractiveShell -- Terminal running iPython
    except NameError:
        logger.ipython_shell = None


class InvalidInstrumentCreateSessionFunction(Exception):
    pass


class InvalidInstrumentConnection(Exception):
    pass


class LocalInstrument(object, metaclass=Singleton):
    has_visa = False
    try:
        import pyvisa
        has_visa = True
    except ImportError:
        logger.error("import pyvisa not found")

    def __init__(self):
        logger.debug("Class {}".format(self.__class__.__name__))
        if os.sys.platform != 'win32':
            self.check_group_dialout()

    def _init(self, instrument, identify=True):
        instrument.addr = self.search4vidpid(instrument.addr, instrument.backend)
        if instrument.init_implict or identify:
            instrument = instrument.collation.add(instrument)
        else:
            instrumentItem = instrument.collation.get_instrument(instrument.interface, instrument.addr)
            if instrumentItem is None:
                logger.warning("No such {!r} instrument at {!r} to init".format(instrument.interface.name, instrument.addr))
                instrument.inst = None
                return
            if instrumentItem.instance != instrument and instrument.addr is not None:
                logger.warning("Cannot initialise {!r} {!r} instrument at {!r} already occupied by {!r} - {!r}"
                               .format(instrument.__class__.__name__, instrument.interface.name, instrument.addr,
                                       instrumentItem.instance.__class__.__name__, instrumentItem.instance.instName))
                instrument.inst = None
                return
        if instrument.addr is None:
            logger.warning('Local instrument:  no address specified, empty instrument')
            instrument.inst = None
            return
        if not self.has_visa:
            logger.error('local instrument:  import pyvisa failed')
            logger.error('please install pyvisa first')
        logger.debug("Local instrument backend {}".format(instrument.backend))
        rm = self.pyvisa.ResourceManager(instrument.backend)
        logger.debug("Local instrument resource manager {}".format(rm))
        instrument.resource_manager = rm
        try:
            self.rid = self.resource_id(instrument.interface, instrument.addr)
            logger.debug("Local instrument resource Id {}".format(self.rid))
            instrument.inst = rm.open_resource(self.rid)
        except Exception as e:
            logger.error(f'Exception in {instrument.instName}, could not open addr {instrument.addr}')
            logger.error('local_instrument resource_manager.open_resource exception {}'.format(repr(e)))
            if self.pyvisa.__version__ < '1.11.3':
                logger.error('local instrument:  wrong pyvisa version, need Version >= 1.11.3')
                raise Exception
            instrument.inst = None
            logger.error('could not open resource {}'.format(instrument.addr))
            logger.error('perhaps disabled or in use?')
            if instrument.interface == Interface.usbserial:
                print('found following devices:')
                self.serial_list(instrument.backend)
            if os.sys.platform == 'win32' and hasattr(logger, 'ipython_shell') and logger.ipython_shell is None:
                input('press any key to continue ...')
            instrument.mqtt_add(mqttc, instrument)
        if instrument.inst:
            if instrument.debugInst:
                return
            instrument.setup_inst()
            iid = instrument.reset()
            instrument.identify()
            if instrument.init_implict:
                logger.debug("{} has implicit instrument init()".format(instrument.__class__.__name__))
            elif identify:
                logger.info("{} need to call instrument init()".format(instrument.__class__.__name__))
            if iid is None or iid != -1:
                try:
                    iid = instrument.id
                except Exception:
                    iid = None
            if iid is not None and iid != "" and iid != -1:
                instrument.is_inited = instrument.init_implict or not identify
                instrument.collation.identification(
                    instrument.interface, instrument.addr,
                    identity=iid, instance=instrument, initialized=instrument.is_inited
                )
                if not instrument.init_implict and identify:
                    logger.info("Validate identity {ident} display on '{iid}', then init()".format(ident=instrument, iid=iid))
                    instrument.close()
                else:
                    logger.info("Device {!r} via {!r}".format(instrument, instrument.inst))
                    instrument.message()
            if iid is None or iid == "" or iid == -1 or iid == '-1':
                msg = "Invalid instrument connection {ident}, no identification id".format(ident=instrument)
                if instrument.interface == Interface.usbserial:
                    msg = msg+'\nplease check the serial parameter on the device: Baudrate, Data bits, Parity, Terminator'
                if instrument.debug:
                    logger.error(msg)
                elif not _createDummyifInvalid:
                    raise InvalidInstrumentConnection(msg)
                elif _createDummyifInvalid:
                    instrument.inst = Dummy(instrument, logger)
            if instrument.init_implict:
                instrument.mqtt_add(mqttc, instrument)

    def resource_id(self, interface, address):
        id_name = "UNDEFINED_INTERFACE"
        if os.sys.platform == 'win32':
            if interface == Interface.gpib and str(address).find('.') < -1:
                id_name = 'GPIB0::{}::INSTR'.format(address)
            elif interface == Interface.gpib and str(address).find('.') > -1:
                id_name = 'TCPIP::{}::INSTR'.format(address)
            elif interface == Interface.usbserial:
                if isinstance(address, (str)) and address.find('COM') > -1:    # pyvisa.__version__> 1.11 needs no 'COM' in the adress
                    address = address[3:]
                id_name = 'ASRL{}::INSTR'.format(address)
        else:
            if interface == Interface.gpib:
                id_name = 'GPIB0::{}::INSTR'.format(address)
                logger.error("No GPIB support on UNIX")
            elif interface == Interface.usbserial:
                if isinstance(address, (str)) and address.find("/") == 0:      # address is already an unix device
                    id_name = 'ASRL{}::INSTR'.format(address)
                else:
                    id_name = 'ASRL/dev/ttyUSB{!r}::INSTR'.format(address)
        return id_name

    def check_group_dialout(self):
        if os.sys.platform == 'win32':
            return True
        if "dialout" not in [grp.getgrgid(g).gr_name for g in os.getgroups()]:
            logger.error("User not in group dialout")
            return False
        else:
            return True

#    def backend_windows_usbserial(self, libpath="Z:/pytestsharing/ms_win/libusb/MS64/dll/libusb-1.0.dll"):
#        import usb.backend.libusb1
#        print("Backend %s" % libpath)
#        backend = usb.backend.libusb1.get_backend(find_library=lambda x: libpath)
#        dev = usb.core.find(backend=backend)

    def list_com(self):
        ports = list(list_ports.comports())
        for p, d, a in ports:
            print("{} {!r} {!r}".format(p, d, a))

    def list_usb_serial_ports(self):
        ports = list_ports.comports()
        for port in ports:
            print(port)

    def search4vidpid(self, addr, backend=None):
        """
        Search for VID:PID in the addr.

                addr = 'VID:PID'  e.q  addr = '16C0:0483'
             return:  device name
        """
        if isinstance(addr, int) and os.sys.platform == 'win32':
            # return 'COM' + str(addr)
            return addr
        elif addr is None or isinstance(addr, int) or addr.find(':') != 4:
            return addr                       # addr is not vid:pid
        try:
            vid = int(addr.split(':')[0], 16)
            pid = int(addr.split(':')[1], 16)
        except Exception:
            return addr
        result = None
        ports = []
        for port in list_ports.comports():
            if port.vid is not None and port.vid == vid and port.pid == pid:
                if result is not None:
                    ports.append(result)
                result = port.device
        if backend is not None:
            list_resources_info = self.pyvisa.ResourceManager(backend).list_resources_info()
            for port in list_resources_info:
                if list_resources_info[port].alias == result:
                    result = list_resources_info[port].interface_board_number
        elif result is not None and DefInter().check4nidriver():
            result = result[3:]
        if result is None:
            logger.error("couldn't find device with vid:pid = {}".format(addr))
            print('found following devices:')
            self.serial_list(backend)
        if len(ports) > 0:
            logger.error('found more than 1 device with vid:pid = {}'.format(addr))
            for port in ports:
                logger.error('    Port: {}'.format(port))
            logger.error('    Port: {}'.format(result))
            result = None
        return result

    def serial_list(self, backend=None):
        """
        List all devices from serial-port (USB-Ports).

           backend = None
                     or '@py'/'@ni', than also print ASRL::INSTR

        """
        ports = list(list_ports.comports())
        dl = len("Port")
        ml = len("Manufacturer")
        il = len("USB info")
        for i in range(0, len(ports)):
            dl = max(dl, len(ports[i].device))
            if ports[i].manufacturer is not None:
                ml = max(ml, len(ports[i].manufacturer))
            if ports[i].usb_info() is not None:
                il = max(il, len(ports[i].usb_info()))
        if backend is not None and os.sys.platform == 'win32':
            vports = self.pyvisa.ResourceManager(backend).list_resources_info()
            vl = len("Visa")
            for port in vports:
                vl = max(vl, len(port))
            print('{:{dl}}   {:{vl}}   {:{ml}}   {:{il}}'.format("Port", "Visa", "Manufacturer", "USB info", dl=dl, vl=vl, ml=ml, il=il))
            print('-----------------------------------------------------------------')
            for i in range(0, len(ports)):
                asrl = "?????::?????"
                addr = "??"
                for port in vports:
                    device = ports[i].device
                    if device.find('COM') > -1:
                        device = int(device[3:])
                    if (vports[port].alias is not None and vports[port].alias == ports[i].device) or vports[port].interface_board_number == device:
                        asrl = port
                        addr = asrl[4:asrl.find(':')]
                print('{!s:{dl}}   {:{vl}}   {!r:{ml}}   {!r:{il}}'.format(addr, asrl, ports[i].manufacturer, ports[i].usb_info(), dl=dl, vl=vl, ml=ml, il=il))
        else:
            print('{:{dl}}   {:{ml}}   {:{il}}'.format("Port", "Manufacturer", "USB info", dl=dl, ml=ml, il=il))
            print('-----------------------------------------------------')
            for i in range(0, len(ports)):
                print('{!s:{dl}}   {!r:{ml}}   {!r:{il}}'.format(ports[i].device, ports[i].manufacturer, ports[i].usb_info(), dl=dl, ml=ml, il=il))

    def idtry(self, instrument):
        """Attempt to fix VISA termination characters to Query IDN."""
        import pyvisa.errors
        # budget.set_slack(self)
        try:
            value = instrument.query('*IDN?')
        except pyvisa.errors.VisaIOError as x:
            logger.warning("Issue with first {} id request, adjusting termination characters, was {!r},{!r}"
                           .format(instrument.__class__.__name__, str(instrument.write_termination), str(instrument.read_termination)))
            if instrument.read_termination == '\n':
                instrument.read_termination = '\r'
            else:
                instrument.read_termination = '\n'
            if instrument.write_termination == '\n':
                instrument.write_termination = '\r'
            else:
                instrument.write_termination = '\n'
            try:
                value = instrument.query('*IDN?')
                logger.info("Termination adjustment required for {} id request, is {!r},{!r}"
                            .format(self.__class__.__name__, str(instrument.write_termination), str(instrument.read_termination)))
            except Exception:
                value = ""
        except Exception:
            value = ""
        return value.replace('\r', '').replace('\n', '')

    def __del__(self):
        self.close()


class PxieInstrument(object, metaclass=Singleton):

    def __init__(self):
        logger.debug("Class {}".format(self.__class__.__name__))

    def _init(self, instrument, identify=True):
        if instrument.init_implict or identify:
            instrument = instrument.collation.add(instrument)
        else:
            instrumentItem = instrument.collation.get_instrument(instrument.interface, instrument.addr)
            if instrumentItem is None:
                logger.warning("No such {!r} instrument at {!r} to init".format(instrument.interface.name, instrument.addr))
                instrument.inst = None
                return
            if instrumentItem.instance != instrument and instrument.addr is not None:
                logger.warning("Cannot initialise {!r} {!r} instrument at {!r} already occupied by {!r} - {!r}".
                               format(instrument.__class__.__name__, instrument.interface.name, instrument.addr,
                                      instrumentItem.instance.__class__.__name__, instrumentItem.instance.instName))
                instrument.inst = None
                return
        if instrument.addr is None:
            logger.warning('PXIe instrument:  no address slot specified, empty instrument')
            instrument.inst = None
            return
        try:
            if instrument.channels is None:
                instrument.inst = instrument.backend.Session(resource_name=instrument.addr)
            else:
                instrument.inst = instrument.backend.Session(resource_name=instrument.addr, channels=str(instrument.channels))
        except Exception:
            instrument.inst = None
            logger.error('could not open resource {} for {}'.format(instrument.addr, instrument))
            logger.error(sys.exc_info())
            if os.sys.platform == 'win32' and hasattr(logger, 'ipython_shell') and logger.ipython_shell is None:
                input('press any key to continue ...')
            raise InvalidInstrumentConnection("Invalid instrument connection {ident}".format(ident=instrument))
        if instrument.inst:
            instrument.setup_inst()
            instrument.reset()
            instrument.identify()
            if instrument.init_implict:
                logger.debug("{} has implicit instrument init()".format(instrument.__class__.__name__))
                instrument.is_inited = True
            elif identify:
                logger.info("{} need to call instrument init()".format(instrument.__class__.__name__))
            if hasattr(instrument, "id"):
                instrument.is_inited = instrument.init_implict or not identify
                iid = instrument.id
                instrument.collation.identification(
                    instrument.interface, instrument.addr,
                    identity=iid, instance=instrument, initialized=instrument.is_inited
                )
                if iid == "":
                    raise InvalidInstrumentConnection("Invalid instrument connection {ident}, no identification id".format(ident=instrument))
                if not instrument.init_implict and identify:
                    logger.info("Validate identity {ident} display on '{iid}', then init()".format(ident=instrument, iid=iid))
                    instrument.close()
                else:
                    logger.info("Device {!r} via {!r}".format(instrument, instrument.inst))
                    instrument.message()
            if instrument.init_implict:
                instrument.mqtt_add(mqttc, instrument)


class NetworkInstrument(object, metaclass=Singleton):
    def __init__(self):
        logger.debug("Class {}".format(self.__class__.__name__))

    def _init(self, instrument, identify=True):
        if instrument.init_implict or identify:
            if instrument.addr and not instrument.hostname:
                instrument.hostname = instrument.addr
            elif not instrument.addr and instrument.hostname:
                instrument.addr = instrument.hostname
            if instrument.port is None:
                instrument.port = 1861
            instrument = instrument.collation.add(instrument)
        else:
            instrumentItem = instrument.collation.get_instrument(instrument.interface, instrument.addr)
            if instrumentItem is None:
                logger.error("No such {!r} instrument at {!r} to init".format(instrument.interface, instrument.addr))
                instrument.inst = None
                return
            if instrumentItem.instance != instrument and instrument.addr is not None:
                logger.error("Cannot initialise {!r} {!r} instrument at {!r} already occupied by {!r} - {!r}".
                             format(instrument.__class__.__name__, instrument.interface.name, instrument.addr,
                                    instrumentItem.instance.__class__.__name__, instrumentItem.instance.instName))
                instrument.inst = None
                return
        if instrument.addr is None:
            logger.warning('local instrument:  no address specified, empty instrument')
            instrument.inst = None
            return
        try:
            if not hasattr(instrument, "create_session"):
                instrument.inst = VICP(addr=instrument.addr, port=instrument.port, debug=instrument.debug)
            else:
                instrument.inst = instrument.create_session()
        except Exception:
            instrument.inst = None
            logger.error('could not open resource {} for {}'.format(instrument.addr, instrument))
            logger.error(sys.exc_info())
            if os.sys.platform == 'win32' and logger.ipython_shell is None:
                input('press any key to continue ...')
            raise InvalidInstrumentConnection("Invalid instrument connection {ident}".format(ident=instrument))
        if instrument.inst:
            instrument.setup_inst()
            instrument.reset()
            instrument.identify()
            if instrument.init_implict:
                logger.debug("{} has implicit instrument init()".format(instrument.__class__.__name__))
                instrument.is_inited = True
            elif identify:
                logger.info("{} need to call instrument init()".format(instrument.__class__.__name__))
            if hasattr(instrument, "id"):
                instrument.is_inited = instrument.init_implict or not identify
                iid = instrument.id
                instrument.collation.identification(
                    instrument.interface, instrument.addr,
                    identity=iid, instance=instrument, initialized=instrument.is_inited
                )
                if iid == "":
                    raise InvalidInstrumentConnection("Invalid instrument connection {ident}, no identification id".format(ident=instrument))
                if not instrument.init_implict and identify:
                    logger.info("Validate identity {ident} display on '{iid}', then init()".format(ident=instrument, iid=iid))
                    instrument.close()
                else:
                    logger.info("Device {!r} via {!r}".format(instrument, instrument.inst))
                    instrument.message()
            if instrument.init_implict:
                instrument.mqtt_add(mqttc, instrument)


class GenericInstrument(object, metaclass=Singleton):
    def __init__(self):
        logger.debug("Class {}".format(self.__class__.__name__))

    def _init(self, instrument, identify=True):
        if not hasattr(instrument, "create_session"):
            logger.error("No 'create_session(instrument)' function defined in instrument {!r} instrument at {!r} to create interface inst of instrument".
                         format(instrument.__class__.__name__, instrument.addr))
            raise InvalidInstrumentCreateSessionFunction("Invalid instrument create_session(instrument) function for {ident}".format(ident=instrument))
        if instrument.init_implict or identify:
            instrument = instrument.collation.add(instrument)
        else:
            instrumentItem = instrument.collation.get_instrument(instrument.interface, instrument.addr)
            if instrumentItem is None:
                logger.warning("No such {!r} instrument at {!r} to init".format(instrument.interface.name, instrument.addr))
                instrument.inst = None
                return
            if instrumentItem.instance != instrument and instrument.addr is not None:
                logger.warning("Cannot initialise {!r} {!r} instrument at {!r} already occupied by {!r} - {!r}".
                               format(instrument.__class__.__name__, instrument.interface.name, instrument.addr,
                                      instrumentItem.instance.__class__.__name__, instrumentItem.instance.instName))
                instrument.inst = None
                return
        if instrument.addr is None:
            logger.warning('Generic instrument:  no address specified, empty instrument')
            instrument.inst = None
            return
        try:
            instrument.inst = instrument.create_session()
        except Exception:
            instrument.inst = None
            logger.error('could not open resource {} for {}'.format(instrument.addr, instrument))
            logger.error(sys.exc_info())
            if os.sys.platform == 'win32' and hasattr(logger, 'ipython_shell') and logger.ipython_shell is None:
                input('press any key to continue ...')
            raise InvalidInstrumentConnection("Invalid instrument connection {ident}".format(ident=instrument))
        if instrument.inst:
            instrument.setup_inst()
            instrument.reset()
            instrument.identify()
            if instrument.init_implict:
                logger.debug("{} has implicit instrument init()".format(instrument.__class__.__name__))
                instrument.is_inited = True
            elif identify:
                logger.info("{} need to call instrument init()".format(instrument.__class__.__name__))
            if hasattr(instrument, "id"):
                instrument.is_inited = instrument.init_implict or not identify
                iid = instrument.id
                instrument.collation.identification(
                    instrument.interface, instrument.addr,
                    identity=iid, instance=instrument, initialized=instrument.is_inited
                )
                if iid == "":
                    raise InvalidInstrumentConnection("Invalid instrument connection {ident}, no identification id".format(ident=instrument))
                if not instrument.init_implict and identify:
                    logger.info("Validate identity {ident} display on '{iid}', then init()".format(ident=instrument, iid=iid))
                    instrument.close()
                else:
                    logger.info("Device {!r} via {!r}".format(instrument, instrument.inst))
                    instrument.message()
            if instrument.init_implict:
                instrument.mqtt_add(mqttc, instrument)


class TimeoutBudget(object, metaclass=Singleton):
    """This TimeoutBudget class is a singleton to provide a shared budget object within each Instrument object.

    Allowing each instrument transaction to accumulate timeout for their needs, which gradually bleeds away as time
    elapses

    Example:
        >>> instrument.budget = TimeoutBudget()
        >>> instrument.budget.cut_slack(instrument, 3)
            add 3sec delay to whats left of the accumulated timeout to instrument.inst.timeout
        >>> instrument.budget.cut_slack(instrument)
            add minimal delay to whats left of the accumulated timeout to instrument.inst.timeout
    """

    def __init__(self):
        self.slack_time = 0
        self.scale = 1.0
        self.relax = 0.1
        self.minim = 1.0
        self.debug = False

    def slack(self):
        """Seconds remaining of accumulated timeout, lower limit at minim"""
        now = time.time()
        todo = self.slack_time - now
        if todo < self.minim:
            todo = self.minim
        return (todo)

    def cut_slack(self, need):
        """add needed delay to whats left of the accumulated timeout"""
        todo = self.slack()
        todo += need * self.scale + self.relax
        now = time.time()
        self.slack_time = todo + now
        return (todo)

    def set_slack(self, instrument, need=None):
        """add needed delay to whats left of the accumulated timeout to given instrument.inst.timeout"""
        if need is None:
            # default time for mundane operations (could depend on instrument interface)
            need = 0.2
        todo = self.cut_slack(need)
        if self.debug:
            if instrument:
                if hasattr(instrument, "inst"):
                    if instrument.inst and hasattr(instrument.inst, "timeout"):
                        instrument.inst.timeout = todo * 1000
                        logger.debug("{!r} timeout now {}".format(instrument.instName, instrument.inst.timeout/1000))
        elif instrument.inst:
            instrument.inst.timeout = todo * 1000


class Instrument(ABC, Ident, mqtt_deviceattributes):
    """This is the abstract Instrument class.

    It cannot be used directly but
    provides a basic set of methods & properties to override with actual instruments

    Initialization arguments of a derived class:
        addr (int | str):
                        interface address, hostname, ip-address, pxi-slot or other address required by interface

        interface (Interface):
                        gpib, usbserial, tcpip, pxie, generic.

        backend (str):
                        backend could be path to a DLL, custom interface item or for
                        pyvisa backend is either '@ivi' (or '@ni') for NI-Library or
                        '@py' for pure python pyvisa-py backend.
                        On default it uses '@ivi' (or '@ni') on win32 and '@py' on
                        other platforms.

        hostname (str):
                        optional interface hostname or ip-address required by interface, when not addr, for tcpip network instruments

        port (int):
                        optional interface port number, for tcpip network instruments

        instName (str):
                        Instrument object name passed as string for later reference in messages to user

        debug (bool):
                        debug information

    Example: Initialization of a derived class
        >>> vdd = DerivedInstrument (addr=24)  # GPIB or USB address
        >>> vdd.init()                         # connect and initialize instrument if this method provided, otherwise implicitly

    Methods:
        init()
            connect and initialize instrument if this method overidden, otherwise implicitly initialize instrument when this method not locally implemented
        setup_inst()
            post init method to override with specific instrument interface initialisation
        reset()
            abstract reset
        identify()
            instrument message, reflect address & interface - if message() implemented
        message("")
            abstract instrument message ("string") or ()
        close()
            terminate interface
        inst.write('*RST')
            write directly to instrument, using underlying instruments command language
        ask=inst.query(':READ?')
            write and read the answer, using underlying instruments command language

    Properties:
        id
            abstract get IDN string

    Objects:
        collation
            a collate_instrument.CollateInstrument singleton cataloging instruments connected
        budget
            a TimeoutBudget singleton to accumulate timeout across all instrument transactions
        com
            an instrument resource to generate interface instances, a singleton of LocalInstrument, PXIeInstrument, NetworkInstrument or GenericInstrument
        inst
            an instance of instrument interface once a connection session to instrument is successful, i.e. a visa object with write(),read(),query() API
    """

    @property
    @abstractmethod
    def interchoices(self):
        """Abstract for static class variable interchoices, to list interfaces statically."""
        return []

    def __init__(self, **kwargs):
        super().__init__()
        logger.debug("Class {}".format(self.__class__.__name__))
        logger.debug("Instrument {} ({})".format(self.__class__.__name__, kwargs))
        self.init_implict = self.init.__func__ == Instrument.init
        logger.debug("Implicit {}".format(self.init_implict))
        self.msg_row_col = (40, 80)
        self.budget = TimeoutBudget()
        self.interface = None
        if "interface" in kwargs and kwargs["interface"] is not None:
            self.interface = kwargs["interface"]
        else:
            if hasattr(self, "interchoices"):
                logger.debug("Interchoices {}".format(self.interchoices))
                for inter in DefInter().default_interface:
                    if inter in self.interchoices:
                        self.interface = inter
                        break
                if not self.interface:
                    self.interface = self.interchoices[0]
                    logger.debug("Defaulting to instruments preferred interface of {} from {}".format(self.interface.name, self.interchoices))
                else:
                    logger.debug("Instrument interface of {}".format(self.interface.name))
            else:
                logger.debug("No interface choices predefined in interchoices")
            if not self.interface:
                self.interface = DefInter().default_interface[0]
            logger.debug("Interface {}".format(self.interface.name))
        if self.interface == Interface.tcpip:
            self.com = NetworkInstrument()
            if "hostname" in kwargs:
                self.hostname = kwargs["hostname"]
            else:
                self.hostname = None
            if "port" in kwargs:
                self.port = kwargs["port"]
            else:
                self.port = None
            self.backend = None
        elif self.interface == Interface.pxie:
            self.com = PxieInstrument()
            self.hostname = None
            self.port = None
            if "backend" in kwargs:
                self.backend = kwargs["backend"]
            else:
                self.backend = None
            if "channels" in kwargs:
                self.channels = kwargs["channels"]
            else:
                self.channels = None
        elif self.interface == Interface.usbserial or self.interface == Interface.gpib:
            self.com = LocalInstrument()
            if "backend" in kwargs and kwargs["backend"] is not None:
                self.backend = kwargs["backend"]
            else:
                self.backend = DefInter().default_backend
            self.hostname = None
            self.port = None
        elif self.interface == Interface.generic:
            self.com = GenericInstrument()
            if "hostname" in kwargs:
                self.hostname = kwargs["hostname"]
            else:
                self.hostname = None
            if "port" in kwargs:
                self.port = kwargs["port"]
            else:
                self.port = None
            if "backend" in kwargs:
                self.backend = kwargs["backend"]
            else:
                self.backend = None
        else:
            logger.error("No interface type {interface} for {instrument}".format(instrument=self.__class__.__name__, interface=self.interface.name))
        if "addr" in kwargs:
            self.addr = kwargs["addr"]
            if type(self.addr) is str and self.addr.find('COM') > -1:
                self.addr = self.addr[3:]
        else:
            self.addr = None
        if "instName" in kwargs:
            self.instName = kwargs["instName"]
        else:
            self.instName = None
        if "debug" in kwargs:
            self.debug = kwargs["debug"]
        else:
            self.debug = False
        if "debugInst" in kwargs:
            self.debugInst = True
        else:
            self.debugInst = False
        self.collation = CollateInstrument()
        self.mqtt_all = ['']
        self.is_inited = False

    def __repr__(self):
        args = ['addr={!r}'.format(self.addr)]
        if self.backend is not None:
            args.append('backend={!r}'.format(self.backend))
        if self.interface is not None:
            args.append('interface={!r}'.format(self.interface.name))
        if self.is_inited:
            return "{classname}({args})->{id}".format(
               classname=self.__class__.__name__,
               args=', '.join(args),
               id=self.id)
        else:
            return "{classname}({args})".format(
               classname=self.__class__.__name__,
               args=', '.join(args))

    def help(self):
        print(self.__doc__)

    @abstractmethod
    def reset(self):
        """Reset and switch beep off."""
        logger.warning("Attention: reset() method unimplemented")

    @abstractmethod
    def message(self, message=None):
        """Message display."""
        logger.warning("Attention: message() method unimplemented")

    @property
    @abstractmethod
    def id(self):
        """Query IDN."""
        logger.warning("Attention: id property unimplemented")

    def identify(self, showInstName=False):
        """Identify message."""
        if showInstName and self.instName and self.instName != "":
            msg = self.instName
        else:
            msg = '{address} :{interface}'.format(interface=self.interface.name, address=self.addr)
        self.message(msg)
        return msg

    def setup_inst(self):
        """Setup the instrument settings."""
        self.budget.set_slack(self, 5.5)      # initial timeout longer for communication startup delay
        if self.inst is not None:
            self.inst.read_termination = '\n'
            self.inst.write_termination = '\n'

    def init(self, identify=False):
        """Optional init for interlock startup after identification."""
        if self.init_implict and not identify:
            logger.warning("Attention: init() method unimplemented, reinitialising")
        if self.is_inited:
            self.close()
        self.com._init(self, identify)
        self.mqtt_add(mqttc, self)

    def close(self, force=False):
        """Close connection to instrument."""
        self.collation.drop(self.interface, self.addr, force)
        self.mqtt_disconnect()
        if hasattr(self, 'inst') and self.inst is not None:
            try:
                self.inst.close()
            except Exception:
                pass
        self.is_inited = False
        self.inst = None
        logger.info('{} closed'.format(self.instName))

    def __del__(self):
        self.close()


class GeneralVisa (Instrument):
    """Interface to any Visa Instrument.

    The GeneralVisa baseclass can connect to Visa usbserial & gpib instruments
    Very limited capabilities, but general purpose for low level access to inst
    Use this class to debug an instrument.inst, note  there is no init()

    Initialization arguments:
        addr (int):
                        interface address

        interface (Interface):
                        gpib, usbserial

        backend (str):
                        visa backend is either '@ivi' (or '@ni') for NI-Library or
                        '@py' for pure python pyvisa-py backend.
                        On default it uses '@ivi' (or '@ni') on win32 and '@py' on
                        other platforms.

    Example: Initialization
        >>> instrument = GeneralVisa(addr=24)       # GPIB or USB address

    Methods:
        close()
            terminate interface
        inst.write('*RST')
            write direct to instrument
        ask=inst.query(':READ?')
            write and read the answer

    Properties:
        id          get IDN string
    """

    interchoices = [Interface.usbserial, Interface.gpib]

    def __init__(self, **kwargs):
        self.is_local = False
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))
        self.com._init(self)

    @property
    def id(self):
        """Query IDN."""
        self.budget.set_slack(self)
        try:
            value = self.inst.query('*IDN?')
        except Exception:
            value = ""
        return value.replace('\r', '').replace('\n', '')

    @property
    def idtry(self):
        """Query IDN."""
        import pyvisa.errors
        self.budget.set_slack(self)
        try:
            value = self.inst.query('*IDN?')
        except pyvisa.errors.VisaIOError as x:
            logger.warning("Issue with first {} id request, adjusting termination characters, was {!r},{!r}"
                           .format(self.__class__.__name__, str(self.inst.write_termination), str(self.inst.read_termination)))
            if self.inst.read_termination == '\n':
                self.inst.read_termination = '\r'
            else:
                self.inst.read_termination = '\n'
            if self.inst.write_termination == '\n':
                self.inst.write_termination = '\r'
            else:
                self.inst.write_termination = '\n'
            try:
                value = self.inst.query('*IDN?')
                logger.info("Termination adjustment required for {} id request, is {!r},{!r}"
                            .format(self.__class__.__name__, str(self.inst.write_termination), str(self.inst.read_termination)))
            except Exception:
                value = ""
        except Exception:
            value = ""
        return value.replace('\r', '').replace('\n', '')

    def message(self, msg=None):
        """There is no message implemented."""
        super().message(msg)

    def reset(self):
        """There is no reset implemented."""
        super().reset()
