"""
Package: collate_instrument.

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

This collate_instrument package provides utilities to collate Instruments

It provides the following

Classes:

    Interface:
        Enumeration of instrument interface types

    InterfaceItem:
        Dataclass to classify interface item

    InstrumentItem
        Dataclass to classify instrument item

    DefInter:
        Singleton class to determine the default interface and optional backend

    CollateInstrument:
        Singleton class to collate all instrument instantiations

    NOTE::
        DefInter.check4nidriver() should find the national instrument driver if exist
        the used key depends from the pyvisa-version
        search for an independent solution !!
"""

import os

from enum import Enum
from dataclasses import dataclass
from typing import Any
from pylab_ml.common.singleton import Singleton

import logging

logger = logging.getLogger("pylab_ml.base_instrument")


class Interface(Enum):
    """Enumeration of instrument interface types"""
    gpib = 1
    usbserial = 2
    pxie = 3
    tcpip = 4
    singular = 5
    generic = 6


@dataclass
class InterfaceItem:
    """Dataclass to classify interface item"""
    interface: Interface
    backend: str
    hostname: str
    port: str
    addr: str


@dataclass
class InstrumentItem:
    """Dataclass to classify instrument item"""
    instName: str
    moduleName: str
    className: str
    interfaceItem: InterfaceItem
    identity: str
    initialized: bool
    instance: Any


class DefInter(object, metaclass=Singleton):
    """Singleton class to determine the default interface and optional backend"""

    import pyvisa

    visa_backends = ["@py", "@ivi", "@ni"]

    def __init__(self, style=None):
        self.style(style)

    def style(self, style=None):
        """
        Determine the default interface and optional backend
        
        Parameters
        ----------
            style : str
                "Linux" : Default interface is tcpip and usbserial, default backend is "@py"
                "usbserial" or "Serial" : Default interface is tcpip and usbserial, default backend is "@ni" if ni driver exist else "@py"
                other : Default interface is tcpip and gpib, default backend is "@ni" if ni driver exist else "@py"
        """
        if style == "Linux":
            self.default_interface = [Interface.tcpip, Interface.usbserial]
            self.default_backend = "@py"
        elif style == "usbserial" or style == "Serial":
            if os.sys.platform == "win32":
                self.default_interface = [Interface.tcpip, Interface.usbserial]
                default_backend = self.check4nidriver()
                if default_backend:
                    self.default_backend = default_backend
                else:
                    self.default_backend = "@py"
            else:
                self.default_interface = [Interface.tcpip, Interface.usbserial]
                self.default_backend = "@py"
        else:
            if os.sys.platform == "win32":
                self.default_interface = [Interface.tcpip, Interface.gpib]
                default_backend = self.check4nidriver()
                if default_backend:
                    self.default_backend = default_backend
                else:
                    self.default_backend = "@py"
            else:
                self.default_interface = [Interface.tcpip, Interface.usbserial]
                self.default_backend = "@py"

    def check4nidriver(self):
        """
        Search for the national instrument driver if exist.

        The used key depends from the pyvisa-version
        search for an independent solution !!
        returns @default_backend or False
        
        Returns
        -------
            default_backend : str
                "@ni" for NI-Library or "@ivi" for IVI-Library
            False : if no NI-Library is found
        """
        default_backend = False
        if "ni" in self.pyvisa.util.get_system_details()["backends"]:  # pyvisa 1.10.1
            vlib = self.pyvisa.util.get_system_details()["backends"]["ni"]
            default_backend = "@ni"
        elif "ivi" in self.pyvisa.util.get_system_details()["backends"]:  # pyvisa 1.11.3
            vlib = self.pyvisa.util.get_system_details()["backends"]["ivi"]
            default_backend = "@ivi"
        else:
            print("unknown key in pyvisa, please check your pyvisa-version")
            return False
        if "Binary library" in vlib and vlib["Binary library"] == "Not found":
            return False
        return default_backend


class CollateInstrument(object, metaclass=Singleton):
    """Singleton class to collate all instrument instantiations"""
    
    def __init__(self):
        self.interface_addresses = {}

    def list_int(self, interface=[]):
        """
        List all instruments of the given interface(s) or all instruments if no interface is given.
        
        Parameters
        ----------
            interface : list of Interface
                List of interfaces to list, if empty list is given, all interfaces are listed
        """
        if interface is None:
            interface = DefInter().default_interface
        if interface == []:
            interface = Interface
        for inter in interface:
            print("{} :".format(inter))
            if inter in self.interface_addresses:
                for k in self.interface_addresses[inter]:
                    instr = self.interface_addresses[inter][k]
                    intrf = instr.interfaceItem
                    if instr.instance is not None:
                        inam = instr.instance.find_names()
                    else:
                        inam = None
                    print(" {} : {}".format(k, instr.instName))
                    print("    : {}".format(inam))
                    print("    : {} : {}".format(instr.moduleName, instr.className))
                    print("       : {} : {}".format(intrf.interface, intrf.backend))
                    print("       : {} : {}".format(intrf.hostname, intrf.port))
                    print("       : {}".format(intrf.addr))
                    print("    : {} : {}".format(instr.identity, instr.initialized))
                    print("    : {}".format(instr.instance))

    def add(self, instrument):
        """
        Add an instrument to the collate instrument.
        
        Parameters
        ----------
             instrument : BaseInstrument
                Instrument to add
                
        Returns
        -------
            instrument : BaseInstrument
                Instrument that was added
        """
        if instrument.interface not in self.interface_addresses:
            self.interface_addresses[instrument.interface] = {}
        if instrument.instName is None:
            instrument.instName = "{!r}".format(instrument)
        if instrument.addr == "?":
            addr = 0
            while addr in self.interface_addresses[instrument.interface].keys():
                addr += 1
            instrument.addr = addr
            logger.info("Allocating first free {!r} address {!r} to {!r}".format(instrument.interface.name, instrument.addr, instrument.__class__.__name__))
        interfaceItem = InterfaceItem(instrument.interface, instrument.backend, instrument.hostname, instrument.port, instrument.addr)
        instrumentItem = InstrumentItem(instrument.instName, instrument.__module__, instrument.__class__.__name__, interfaceItem, "", False, instrument)
        otherInstrumentItem = self.get_instrument(instrument.interface, instrument.addr)
        if otherInstrumentItem:
            logger.info("Replacing already occupied {!r} {!r} by {}".format(instrument.interface.name, instrument.addr, otherInstrumentItem.__class__.__name__))
            if otherInstrumentItem.instance:
                try:
                    otherInstrumentItem.instance.close()
                except Exception:
                    logger.error("could not close other instrument {}".format(otherInstrumentItem.className))
        self.interface_addresses[instrument.interface][instrument.addr] = instrumentItem
        return instrument

    def identification(self, interface, address, identity=None, module=None, initialized=None, instance=None, instName=None):
        """
        Add identification information to an instrument.
        
        Parameters
        ----------
            interface : Interface
                Interface of the instrument
            address : int
                Address of the instrument
            identity : str, optional
                Identity of the instrument
            module : str, optional
                Module name of the instrument
            initialized : bool, optional
                Initialization status of the instrument
            instance : object, optional
                Instance of the instrument
            instName : str, optional
                Name of the instrument
        """
        if interface in self.interface_addresses:
            if address in self.interface_addresses[interface]:
                if self.interface_addresses[interface][address] is None:
                    self.interface_addresses[interface][address] = InstrumentItem("", "", "", None, "", False, None)
                if module is not None:
                    self.interface_addresses[interface][address].moduleName = module
                if identity is not None:
                    self.interface_addresses[interface][address].identity = identity
                if initialized is not None:
                    self.interface_addresses[interface][address].initialized = initialized
                if instance is not None:
                    self.interface_addresses[interface][address].instance = instance
                if instName is not None:
                    self.interface_addresses[interface][address].instName = instName

    def get_instrument(self, interface, address):
        """
        Get an instrument from the collate instrument.
        
        Parameters
        ----------
            interface : Interface
                Interface of the instrument
            address : int
                Address of the instrument
        
        Returns
        -------
            InstrumentItem or None
                The instrument item if found, otherwise None
        """
        if interface in self.interface_addresses:
            if address in self.interface_addresses[interface]:
                return self.interface_addresses[interface][address]
            else:
                return None

    def find_instrument(self, instName):
        """
        Find an instrument by its name.
        
        Parameters
        ----------
            instName : str
                Name of the instrument
        
        Returns
        -------
            InstrumentItem or None
                The instrument item if found, otherwise None
        """
        for interface in self.interface_addresses:
            for address in self.interface_addresses[interface]:
                instrument = self.get_instrument(interface, address)
                if instrument.instName == instName:
                    return instrument
        return None

    def drop(self, interface, address, force=False):
        """
        Drop an instrument from the collate instrument.
        
        Parameters
        ----------
            interface : Interface
                Interface of the instrument
            address : int
                Address of the instrument
            force : bool, optional
                Force drop the instrument even if not initialized
        """
        if interface in self.interface_addresses:
            if address in self.interface_addresses[interface]:
                if force or self.interface_addresses[interface][address].initialized:
                    del self.interface_addresses[interface][address]


@dataclass
class InstrumentDefinition:
    """Dataclass to classify instrument definition"""
    nickName: str
    moduleName: str
    className: str


class InstrumentLibrary(metaclass=Singleton):
    """Singleton class to collate all instrument definitions"""
    
    def __init__(self):
        logger.debug("Class {}".format(self.__class__.__name__))
        self.tcc_pythonpath = os.environ["TCC_PYTHONPATH"]
        self.collation = CollateInstrument()
        self.library = {}
        self.library["smu.Keithley2000"] = InstrumentDefinition("smu.Keithley2000", "pylab_ml.smu.keithley.keithley2000", "Keithley2000")
        self.library["smu.Keithley2400"] = InstrumentDefinition("smu.Keithley2400", "pylab_ml.smu.keithley.keithley2400", "Keithley2400")
        self.library["smu.Keithley2602"] = InstrumentDefinition("smu.Keithley2602", "pylab_ml.smu.keithley.keithley2602", "Keithley2602")
        self.library["scope.Lecroy.Wavesurfer3054"] = InstrumentDefinition(
            "scope.Lecroy.Wavesurfer3054", "pylab_ml.scope.lecroy.wavesurfer.wavesurfer3054", "Wavesurfer3054"
        )
