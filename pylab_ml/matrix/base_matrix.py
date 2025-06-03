#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Interface to a relay matrix.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>

[Categories]
Pos=struct                     ('Name', 'Pos',                      'Type', 'Exclusive', 'List', {'Position1', 'Position2'},                    'Protected', 0, 'Color', [1,0.6,0])
Supplies=struct				   ('Name', 'Supplies',                 'Type', 'Exclusive', 'List', {'C_Board_Vsup', 'ContactTestGND'},            'Protected', 0, 'Color', [0.2,0.6,1])
CommunicationBoardConfig=struct('Name', 'CommunicationBoardConfig', 'Type', 'Exclusive', 'List', {'C_BoardOut_BUS1', 'C_BoardOut_Only_BUS1'},   'Protected', 0, 'Color', [0.2,0.8,0])
Additonal=struct               ('Name', 'Additonal',                'Type', 'Stackable', 'List', {'Scope_BUS1', 'US1_VSUP'},                    'Protected', 0, 'Color', [0.74902,0,0.74902])
BUS1Config=struct              ('Name', 'BUS1Config',               'Type', 'Exclusive', 'List', {'BUS1_IO1_Position1'},                        'Protected', 0, 'Color', [0.93333,0.46667,0])
BUS2Config=struct              ('Name', 'BUS2Config',               'Type', 'Exclusive', 'List', {'BUS2_IO1_Position1'},                        'Protected', 0, 'Color', [0.8,0.33333,0])

"""

import os
import pathlib
import configparser
from pylab_ml.collate_instrument import Interface
from pylab_ml.base_instrument import logger


class BaseMatrix():
    """Basic interface to a Relay Matrix.

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    """

    interchoices = [Interface.generic]

    def __init__(self, connectionTableName=None, identify=False, emulator=False):
        """Initialise the instrument.

        Parameters
        ---------_
        connectionTableName : str, optional
            filename from setup- or matlab-file with connection definition. The default is $WORKAREA/harness/matrix*.setup
        emulator : bool, optional
            if True than emulate only a Matrix. No real hardware. The default is False.


        Example: Initialization
           >>> tablename = 'matrix_messplatz.setup'
           >>> matrix = Pickering_40_5xx(addr='Switch', tablename, instName='matrix')
           >>> matrix.set('Position2','close')              # need connectionTable
           >>> matrix.set('Oszi','close')
           >>> matrix.set('APB_Vsup','close')
           >>> matrix.set('APB_Vsup','open')
           >>> matrix.set('SMU_Vsup','close')
           >>> matrix.set('SMU_Vsup')                       # default = open
           >>> matrix.set('APB_Vsup','close',SwitchOver=True)
           >>> matrix.connect('1,1,1;1,2,3;1,3,5','close')  # if connectionTable not loaded

        detailed example of usage:
           * :download:`examples/pickeringmatrix/matrix_40_541_201.py <../../../examples/pickeringmatrix/matrix_40_541_201.py>`

        """
        self.connectionTableName = connectionTableName
        self.connectionTable = None
        self.emulator = emulator
        self.gui = "ate_spyder_lab_control.labml_adjutancy.gui.instruments.matrix.matrix"  # semi-ctrl use this lib for the matrix gui
        logger.debug("Class {}".format(self.__class__.__name__))

    def setup_inst(self):
        """Set instrument settings for setup, called von class Instrument."""
        super().setup_inst()
        breakpoint()
        errorlist = self.error_list()
        if errorlist[0] != 0:
            logger.error("{} found Diagnose error {}".format(self.instName, errorlist))
        self.cardnr = 1  # only one card Sub-Unit accept, changes necessary for more sub-units,   if more than self.inst.GetSubCounts()
        self.dic_connectionTable = None  # will be set if connectionTable = *.setup
        self.dic_constantsTable = None  # "
        path = os.environ.get("harness")
        if self.connectionTableName is not None:
            self.load_connectionTable(self.connectionTableName)
        elif path is not None and path != "":  # load default $workarea/harness/matrix*.setup
            load = False
            with os.scandir(path) as entries:
                for entry in entries:
                    if entry.is_file() and pathlib.Path(entry.name).suffix == ".setup" and entry.name.find("matrix") == 0:
                        if load:
                            logger.error(f"{self.instName} found more than one setup file, use {entry.path}")
                        self.load_connectionTable(entry.path)
                        load = True
        self.type = ""
        self.mqtt_all = ["set()", "clear()", "id", "load_connectionTable()", "close()", "display()"]

    def _error_message(self, err):
        """Get the error_message from instance."""
        msg = "{}.Error: {}".format(self.instName, self.inst.ErrorMessage(err))
        return msg

    def display(self, mode=None):
        """
        Display state, nodes or connection in ASCII-String.

           | mode==None or 'state'  display actual state
           | mode=='nodes'  display connected nodes
           | mode=='connection' display available codes for connections
           | mode==someone else  display help
        """
        if mode is None or mode == "state":
            if self.connectionTable is None:
                logger.error("   display({}) not possible, connectionTable not loaded".format(mode))
            else:
                msg = "\n"
                for key in self.connectionTable.keys():
                    if key.find("ModeSets.") < 0:
                        msg = msg + ("    {:<20} :         {}\n".format(key, self.ActualState[key]))
                msg += f"{self.instName}.display('?') for other modes\n"
                logger.info(msg)
                print(msg)
                self.publish_get("display", ("state", msg))
            return
        elif mode == "nodes":
            self._GetCrosspointState(self.cardnr)
        elif mode == "connection":
            if self.connectionTable is None:
                logger.error("   display({}) not possible, connectionTable not loaded".format(mode))
                return
            msg = "\n"
            for key in self.connectionTable.keys():
                if key.find("ModeSets.") < 0:
                    state = ":         {}".format(self.ActualState[key])
                else:
                    state = ""
                msg = msg + ("    {:<20}{}\n".format(key, state))
                for mode in self.connectionTable[key]:
                    msg = msg + "            {}\n".format(mode)
            logger.info(msg)
            print(msg)
        else:
            print("    usage: display(mode)")
            print("       with mode= 'state' ")
            print("                = 'nodes' ")
            print("                = 'connection' ")

    def clear(self):
        """Clear all connections (open).

        add the correct command for the instance to this function.
        """
        if self.connectionTable is None:
            self.ActualState = "open"
        else:  # set all Categories to open
            self.ActualState = {}
            for key in self.connectionTable.keys():
                self.ActualState.update({key: "open"})
        self.publish_set("clear", 0)

    def set(self, connection, state="open", SwitchOver=False):
        """Set categories or scenarios to state 'open' or 'close'.

        Args:
            connection (str):  categories or scenarios.
            state (str, optional):  'open' or 'close'. Defaults to 'open'.
            SwitchOver (TYPE, optional):
               | True : connection will be open AFTER the new one was set,
               | False : default -> first: open last connection, than: close new connection

        Returns:
            None

        """
        if self.connectionTable is None:
            logger.warning("set({},{}) not possible: connectionTable not loaded".format(connection, state))
            return
        key = connection  # for setup-File
        if self.dic_connectionTable is None:
            key = "Category_" + connection  # for Matlab-File
        if key in self.connectionTable:  # what is the key, is it in Categories ?
            if self.ActualState[key] == state:
                logger.info("set({},{}) already set".format(connection, state))
                return
            vtype = self.dic_connectionTable[key]["Type"]
            if vtype == "Exclusive":  # if Exclusive than open the last setting
                if self.connect(self.connectionTable[key][self.ActualState[key]], "open"):
                    self.ActualState[key] = "open"
                self.publish_set("set", (connection, state))
            elif vtype == "Stackable":
                print("found Stackable", connection, state)
                for connection in self.connectionTable[key]:
                    self.set(connection, "open")
            else:
                logger.error("{}.set type {} unknown, please check your setup-file".format(self.instName, vtype))
            return
        if self.dic_connectionTable is None:
            key = "ModeSets." + connection  # for Matlab-File
        if key in self.connectionTable:  # search for ScenariosSets
            for connection in self.connectionTable[key]:  # it is a ScenariosSets
                self.set(connection, state)
            self.publish_set("set", (connection, state))
            return
        # it is not a categorie or ScenariosSets, so it is a scenario:
        found = 0
        for key in self.connectionTable.keys():  # scan all keys for the connection
            if connection in self.connectionTable[key]:
                found = 1
                last_connection = self.ActualState[key]
                if SwitchOver:
                    break
                if (
                    key.find("Category_Supply") == 0 or (self.dic_connectionTable is not None and self.dic_connectionTable[key]["Type"] == "Exclusive")
                ) and self.ActualState[key].find(
                    "open"
                ) < 0:  # if supply than always open last state
                    if self.connect(self.connectionTable[key][self.ActualState[key]], "open"):
                        self.ActualState[key] = "open"
                    else:
                        return
                for gkey in self.connectionTable[key].keys():  # search for key 'open*' and if found, than 'open' last connection
                    if gkey.find("open") == 0 and self.ActualState[key].find("open") < 0:  # key open indicate open before close
                        if self.connect(self.connectionTable[key][self.ActualState[key]], "open"):
                            self.ActualState[key] = "open"
                        else:
                            return  # connection goes wrong...
                        if connection.find(gkey) == 0:
                            found = 2  # do nothing more
                break
        if found == 1:
            if self.ActualState[key] != "mode":
                if self.connect(self.connectionTable[key][connection], state):
                    if state == "close":
                        self.ActualState[key] = connection
                    else:
                        self.ActualState[key] = state
                if SwitchOver:
                    self.connect(self.connectionTable[key][last_connection], "open")  # open last connection
                self.publish_set("set", (connection, state))
                logger.measure(f"{self.instName}.set('{connection}', '{state}')")
        elif found == 0:
            logger.error("{}.set('{}') not found !".format(self.instName, connection))
            logger.info("     for available connections, write   {}.display('connection')".format(self.instName))
        return

    def load_connectionTable(self, connectionTableName=None):
        """Load matlab(.m) or setup-file(.setup) with definition from connections.

        create constantsTable and connectionTable
        """
        self.id
        if connectionTableName is None:
            if self.connectionTableName is not None:
                connectionTableName = self.connectionTableName
            else:
                logger.error(f"{self.instName}.load_connectionTable: connectionTableName isn't defined")
                return
        file_extension = os.path.splitext(connectionTableName)[-1]
        if file_extension == ".m":
            constants, contab = self._load_matlabTable(connectionTableName)
        else:
            constants, contab = self._load_setupTable(connectionTableName)
        logger.info(f"{self.instName}.load_connectionTable('{connectionTableName}')")
        self.connectionTableName = connectionTableName
        self.publish_set("dic_constantsTable", self.dic_constantsTable)
        self.publish_set("dic_connectionTable", self.dic_connectionTable)
        if self.connectionTable != contab:
            self.connectionTable = contab
            self.clear()
        self.constantsTable = constants
        self.connectionTable = contab
        self.constantsTable = constants

    def _load_setupTable(self, filename):
        """
        Load filename  and create dictionary constants and contab.

        Args:
            filename (TYPE):  filename *.setup

        Raises:
            Exception: IOError.

        Returns:
            constants (dic)  contab.

        """
        if not os.path.isfile(filename):
            raise Exception(" couldn't find {}".format(filename))
        dic_connectionTable = {}
        dic_constantsTable = {}
        # constants = {}
        contab = {}
        config = configparser.ConfigParser()
        config.optionxform = str  # allow upper character in key
        config.read(filename)
        if config.sections() == []:
            raise IOError(" {} couldn't found necessary information in the file".format(filename))
        for key in config["Device"]:
            dic_constantsTable = self._struc2dic(config["Device"][key])  # have to change for more than one devices
            # if 'XLables' in dic_constantsTable:
            #     constants = dic_constantsTable['XLables']
            # if 'YLables' in dic_constantsTable:
            #     constants.update(dic_constantsTable['YLables'])
        for categories in config["Categories"]:
            dic = self._struc2dic(config["Categories"][categories])
            for scenario in config["Scenarios"]:
                if scenario in dic["List"]:
                    dic["List"][scenario] = config["Scenarios"][scenario][1:-1].replace(",'", ";")
            dic_connectionTable.update({dic["Name"]: dic})
        for key in dic_connectionTable:
            contab.update({dic_connectionTable[key]["Name"]: dic_connectionTable[key]["List"]})
        self.dic_connectionTable = dic_connectionTable
        self.dic_constantsTable = dic_constantsTable
        self.clear()
        # return(constants, contab)
        return (dic_constantsTable, contab)

    def connect(self, crosspointtable, state):
        """Set state from crosspoint.

        Args:
            crosspointtable (str): stringlist with nodes ('1,3,4;1,5,6;1,2,14')  card, row, col.
            state (str): 'open' or 'close'.

        Raises:
            Exception: when more than one card use.

        Returns:
            bool:
               | True : etablish state
               | False : error

        """
        if state == "close":
            state = 1
        elif state == "open":
            state = 0
        else:
            logger.error("{}.connect: could not connect to state {}".format(self.instName, state))
            return False
        crosspoints = crosspointtable.split(";")
        for point in crosspoints:
            net = point.split(",")
            if len(net) == 2:
                cardnr = 1
                row = int(net[0])
                col = int(net[1])
            else:
                cardnr = int(net[0])
                row = int(net[1])
                col = int(net[2])
                if cardnr != 1:
                    raise IOError("{!r} supports only 1 Card, but Card={}, if you need this, please extend the software....".format(self.instName, cardnr))
            err = self.inst.SetCrosspointState(cardnr, row, col, state)
            if err != 0:
                logger.error("{}.connect: row={}, col={}, state={}  -> {}".format(self.instName, row, col, state, self._error_message(err)))
                return False
            else:
                self.publish_set("SetCrosspointState", (cardnr, row, col, state))
        return True

    def _GetCrosspointState(self, cardnr):
        msg = "\n    {} = {}  {}x{}\n      ".format(self.instName, self.type, self.cols, self.rows)
        for cols in range(1, int(self.cols / 10) + 1):
            msg = msg + ("         {}".format(cols))
        msg = msg + ("\n      ")
        for cols in range(1, self.cols + 1):
            msg = msg + "{}".format(cols % 10)
        for rows in range(1, self.rows + 1):
            msg = msg + "\n    {} ".format(rows)
            for cols in range(1, self.cols + 1):
                err, value = self.inst.GetCrosspointState(cardnr, rows, cols)
                if value == 0:
                    value = " "
                elif value == 1:
                    value = "*"
                msg = msg + "{}".format(value)
            if self.dic_constantsTable is not None:
                for key in self.dic_constantsTable["YLables"]:
                    if key.find(".") < 0 and self.dic_constantsTable["YLables"][key] == str(rows):
                        msg = msg + "{}".format(key)
        logger.info(msg)
        print(msg)


class Matrix_Emulator(object):
    """Emulator from a relay Matrix.

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    Usable if you have no real Matrix as instance

    """

    import numpy as np

    def __init__(self, addr=None, x=66, y=8):
        """Initialise."""
        self.addr = addr
        self.y_max = y
        self.x_max = x

    def Reset(self):
        """Reset."""
        self.clear()

    def clear(self):
        """Clear all connections (opem)."""
        self.ClearCard()

    def Close(self):
        """Close connection to Pickering Emulator."""
        self.matrix_array = None
        self = None
        return 0

    def ClearCard(self):
        """Open all connections."""
        self.matrix_array = self.np.zeros((self.y_max, self.x_max))

    def SetCrosspointState(self, cardnr, row, col, state):
        self.matrix_array[row - 1][col - 1] = state
        return 0

    def GetCrosspointState(self, cardnr, rows, cols):
        return 0, self.matrix_array[rows - 1][cols - 1]

    def ErrorMessage(self, err):
        msg = "Emulator.matrix:  something goes wrong, error = {}".format(err)
        raise Exception(msg)

    def message(self, message=None):
        """Device has no display, message display to logger."""
        if message is not None:
            logger.debug(message)

    def GetCardId(self):
        return 0, "Pickering Emulator Matrix"

    def Diagnostic(self):
        value = 0
        return [value]

    def SubInfo(self, cardnr, unknown):
        return 0, 100, self.y_max, self.x_max
