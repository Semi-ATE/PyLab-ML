"""Interface to the Matrix Pickering 40-541-021.

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
import regex
import pathlib
import configparser
from pylab_ml.collate_instrument import Interface

# from pylab_ml.base_instrument import InvalidInstrumentConnection
from pylab_ml.matrix import Pipx40
from pylab_ml.matrix.base_pickering import Pickering
from pylab_ml.matrix.base_pickering import findcard
from pylab_ml.base_instrument import logger


class Pickering_40_5xx(Pickering):
    """Interface to the Matrix Pickering 40-541-021 (66x8 Matrix, 69x16).

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    .. image:: ../_static/pickeringmatrix.jpg

    .. warning::
        | only tested with one table and Matrix Pickering 40-541-021 (66 x 8 Matrix)
        | please use it carefully with other tables and matrixs
        | matlab.m files as table will not supported any more

    todo:
       | SwitchOver not tested!!
       | only one device allowed
       | ScenariosSet not implemented
       | Auswertung protected=0/1 für Category fehlt
       | stackable testen
       | wie ist switchover in neuem setup-file von Matlab implementiert

    """

    #    available functions from self.inst:
    #    ['AttenGetAttenuation', 'AttenGetInfo', 'AttenGetPadValue', 'AttenGetType', 'AttenSetAttenuation',
    #     'BattGetCurrent', 'BattGetEnable', 'BattGetVoltage', 'BattReadInterlockState', 'BattSetCurrent', 'BattSetEnable', 'BattSetVoltage',
    #     'ClearCard', 'ClearSub', 'Close', 'CountFreeCards', 'Diagnostic', 'ErrorMessage',
    #     'FindFreeCards', 'GetCardId', 'GetCardStatus', 'GetChannelPattern', 'GetChannelState',
    #     'GetClosureLimit', 'GetCrosspointMask', 'GetCrosspointState', 'GetMaskPattern', 'GetMaskState',
    #     'GetSettlingTime', 'GetSubCounts', 'OperateSwitch',
    #     'ReadCalibration', 'ReadCalibrationDate', 'ReadCalibrationFP',
    #     'ReadInputPattern', 'ReadInputState', 'ResGetInfo', 'ResGetResistance', 'ResSetResistance',
    #     'Reset', 'RevisionQuery', 'SelfTest', 'SetCalibrationPoint',
    #     'SetChannelPattern', 'SetChannelState', 'SetCrosspointMask', 'SetCrosspointState',
    #     'SetDriverMode', 'SetMaskPattern', 'SetMaskState', 'SubAttribute', 'SubInfo', 'SubSize',
    #     'SubStatus', 'SubType', 'WriteCalibration', 'WriteCalibrationDate', 'WriteCalibrationFP',
    #     'data', 'handle', 'rm', 'string', 'vi']
    #
    #    not for 40-541-021:
    #     PsuGetInfo
    #     PsuGetType
    #     PsuGetVoltage
    #     PsuSetVoltage
    #     PsuEnable

    interchoices = [Interface.generic]

    def __init__(self, addr=None, connectionTableName=None, identify=False, instName=None, emulator=False):
        """Initialise the instrument.

        Parameters
        ----------
        addr : str, optional
           address Name from NIMax,
           or None, but than it is time-killing (only works ith one Pickering Matrix at PCIe ). The default is None.
        connectionTableName : str, optional
            filename from setup- or matlab-file with connection definition. The default is $WORKAREA/harness/matrix*.setup
        instName : str, optional
            instance Name from top
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
           >>> matrix.display('nodes')
           >>> matrix.display('state')
           >>> matrix.connect('1,1,1;1,2,3;1,3,5','close')  # if connectionTable not loaded

        detailed example of usage:
           * :download:`examples/pickeringmatrix/matrix_40_541_201.py <../../../examples/pickeringmatrix/matrix_40_541_201.py>`

        """
        # self.mqtt_debug = True
        self.connectionTableName = connectionTableName
        self.connectionTable = None
        self.emulator = emulator
        self.gui = "pylab_ml.gui.instruments.matrix.matrix"  # semi-ctrl use this lib for the matrix gui
        kwargs = {"addr": addr, "backend": Pipx40, "identify": identify, "instName": instName}
        super().__init__(**kwargs)
        logger.debug("Class {}".format(self.__class__.__name__))

    #        self.msg_row_col = (1,20)

    def create_session(self):
        """Create Session, called von class Instrument."""
        if self.addr == -1:
            self.addr = findcard()
        #        inst = Pipx40.pipx40_card(('{}'.format(self.addr)).encode(),0,0);
        if not self.emulator:
            inst = Pipx40.pipx40_card(("{}".format(self.addr)), 0, 0)
        else:
            inst = Pickering_Emulator(self.addr)
        return inst

    def setup_inst(self):
        """Set instrument settings for setup, called von class Instrument."""
        super().setup_inst()
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
        # else:
        # self.constantsTable = None
        self.type = ""
        self.mqtt_all = ["set()", "clear()", "id", "load_connectionTable()", "close()", "display()"]

    def _error_message(self, err):
        """Get the error_message from instance."""
        msg = "{}.Error: {}".format(self.instName, self.inst.ErrorMessage(err))
        return msg

    def identify(self):
        """Identify message."""
        msg = self.id
        self.message(msg)
        #       Getting Sub-Unit Information
        err, subType, rows, cols = self.inst.SubInfo(self.cardnr, 1)
        if subType == 0:
            subType, comment = "unknown", "pipx40 with adr='{}' not found".format(self.addr)
        elif subType == 1:
            subType, comment = "pipx40_TYPE_SW", "Uncommitted switches or Input sub-units "
        elif subType == 2:
            subType, comment = "pipx40_TYPE_MUX", "Relay multiplexer (single-channel only)"
        elif subType == 3:
            subType, comment = "pipx40_TYPE_MUXM", "Relay multiplexer (multi-channel capable)"
        elif subType == 4:
            subType, comment = "pipx40_TYPE_MAT", "Standard matrix"
        elif subType == 5:
            subType, comment = "pipx40_TYPE_MATR", "RF matrix"
        elif subType == 6:
            subType, comment = "pipx40_TYPE_DIG", "Digital outputs"
        elif subType == 7:
            subType, comment = "pipx40_TYPE_RE", "Programmable Resistor"
        elif subType == 8:
            subType, comment = "pipx40_TYPE_ATTEN", "Programmable Attenuator"
        elif subType == 9:
            subType, comment = "pipx40_TYPE_PSUDC", "Power Supply, DC"
        elif subType == 100:
            subType, comment = "Python Relay Emulator ", "Relay multiplexer"
        else:
            comment = "pipx40_TYPE unknown"
        if err != 0:
            self.message("{}, typ = {}".format(comment, subType))
            self.message(self._error_message(err))
        else:
            self.message("Type={} (->{}): {}x{}".format(subType, comment, rows, cols))
        self.type = comment
        self.rows = rows
        self.cols = cols
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
        """Clear all connections (open)."""
        self.inst.ClearCard()
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

    def _struc2dic(self, key):
        """Convert string struct from matlab to dictonary.

        Args:
            key (str): string struct in matlab syntax

        Returns:
            dic (dic): python dictonary from the key.

        """
        dic = {}
        if key.find("struc") == 0:
            key = key.replace("'", "")[key.find("(") + 1: -1].replace(" ", "")
            key = regex.split(r"\[.*\](*SKIP)(*FAIL)|,", key)  # split without e.q. [1,0.6,0]
        variable = ""
        for string in key:
            if variable == "":
                variable = string
                index = -1
            elif index == -1:
                value = string
                if value.find("{") > -1:  # find dict in dict
                    index = 1
                    string = value[value.find("{") + 1:]
                    dic.update({variable: {}})
                else:
                    dic.update({variable: value})
                    variable = ""
            if index > -1:
                end = string.find("}")
                if end > -1:
                    string = string[:end]
                if string != "":
                    dic[variable].update({string: str(index)})
                index += 1
                if end > -1:
                    variable = ""
        return dic

    def _load_matlabTable(self, table_filename):
        """
        Load connection Table from matlab sources.

        Args:
            table_filename (str): filename von matlab Table file.

        Returns:
            None.

        """
        contab = {}
        constants = {}
        state = 0
        with open(table_filename, "r") as file:
            for line in file:
                comment = line.find("%")
                if comment == 0 or len(line) == 1:
                    continue
                elif comment > 0:
                    line = line[: comment - 1]
                if state == 0:  # search for start
                    start = regex.compile(r"function *\[ *").search(line)
                    if start is not None:
                        last = regex.compile(r" *\] *=").search(line)
                        name_contab = line[start.end(): last.start()]
                        state = 1
                elif state > 0 and line.find(name_contab) >= 0:
                    loop = True
                    while line.find("=") > 0 and loop:
                        line = line.replace(" ", "")  # filter all empty spaces
                        start = regex.compile(name_contab + r"\.").search(line)  # start found, now analyse line
                        if start is not None:
                            line = line[start.end():]  # remove from line first variablename
                            last = regex.compile(" *=").search(line)
                            variable = line[: last.start()]
                            values = {}
                            if line.find("{") > 0:  # insert new keys
                                while len(line) > 0 and line[0] != "}":
                                    line = line[line.find("'") + 1:]
                                    newkey = line[: line.find("'")]
                                    values.update({newkey: None})
                                    line = line[line.find("'") + 1:]
                                contab.update({variable: values})
                            elif line.find("[") > 0:  # now, replace constants with values
                                line = line[line.find("[") + 1:]  # now, only the constants name in the line
                                start = variable.find(".")
                                if start > 0:
                                    variable = variable[start + 1:]
                                if variable in contab:
                                    msg = "{}.load_connectionTable: Error in function Please check Software or Matlab-file ??".format(self.instName)
                                    raise (msg)
                                else:
                                    for key in contab.keys():
                                        if variable in contab[key]:
                                            replace_line = ""  # replaced constants with integers
                                            while len(line) > 3:
                                                last = regex.compile(r"[,;\]]").search(line)
                                                replace_constant = line[: last.start()]
                                                if replace_constant.find(name_contab) >= 0:
                                                    replace_constant = replace_constant[len(name_contab) + 1:]
                                                replace_line = replace_line + constants[replace_constant] + line[last.end() - 1]
                                                line = line[last.start() + 1:]
                                            contab[key][variable] = replace_line[:-1]
                            else:  # rest should be absolute terms -> save it to constants
                                value = line[line.find("=") + 1: line.find(";")]
                                constants.update({variable: value})
                        else:
                            loop = False
        return (constants, contab)

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

    # -----------------------------------------------------------------------------------------------------------------
    # only for testing and debugging, could be removed or improve...:
    def GetChannelPattern(self, cardnr):
        """Only for testing and debugging, could be removed or improve..."""
        err, dwords, array = self.inst.GetChannelPattern(cardnr)  # dwords=17
        for i in array:
            print("{} ".format(array[i]), end="")
        print("")

    def GetChannelState(self, cardnr):
        """Only for testing and debugging, could be removed or improve..."""
        for ch in range(1, self.rows * self.cols):
            err, state = self.inst.GetChannelState(cardnr, ch)
            print("{} ".format(state), end="")
        print("")

    def GetMaskPattern(self, cardnr):
        """Only for testing and debugging, could be removed or improve..."""
        err, dwords, array = self.inst.GetMaskPattern(cardnr)  # warum nur 40 words???!!!
        for i in array:
            print("{} ".format(array[i]), end="")

    def GetMaskState(self, cardnr):
        """Only for testing and debugging, could be removed or improve..."""
        for i in range(1, self.rows * self.cols):
            print("{} ".format(self.inst.GetMaskState(cardnr, i)), end="")

    def GetCrosspointMask(self, cardnr):
        """Only for testing and debugging, could be removed or improve..."""
        for rows in range(1, self.rows):
            for cols in range(1, self.cols):
                err, value = self.inst.GetCrosspointMask(cardnr, rows, cols)
                print("{} ".format(value), end="")
            print("")


class Pickering_Emulator(object):
    """Emulator from a  Matrix Pickering.

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


if __name__ == "__main__":
    from pylab_ml.base_instrument import logsetup
    # from pylab_ml.matrix.base_pickering import findcard           # only if unknown card address

    logsetup()

    # addr = findcard()     # this is time-killing, if you know the addr use the addr directly
    addr = "PXI1Slot6"
    tablename = r"\harness\matrix_qdbmessplatz.setup"
    matrix = Pickering_40_5xx(addr, connectionTable=os.path.normcase(tablename), instName="matrix", emulator=True)
    matrix.mqtt_debug = True

    matrix.connect("1,1,1;1,2,3;1,3,5", "close")  # set crosspoints direct y1,x1;y2,x2;y3,x3

    matrix.display("nodes")
    matrix.clear()

    matrix.set("Position1", "close")
    matrix.set("Pos", "open")
    matrix.set("Pos", "open")

    matrix.display("state")
    matrix.display("nodes")
    matrix.set("Position2", "close")
    matrix.display("state")
    matrix.display("nodes")
    matrix.set("APB_Vsup", "close")
    matrix.set("APB", "close")  # key von ModeSets
    matrix.display("state")
    matrix.display("nodes")
    matrix.set("SMU_Vsup", "close")
    matrix.display("state")
    matrix.display("nodes")

    matrix.close()
