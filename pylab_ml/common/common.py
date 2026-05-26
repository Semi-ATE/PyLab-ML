# -*- coding: utf-8 -*-
"""
Created on Tue May 4 14:18:05 2021

This script is part of the pylab_ml package and contains common utility functions that can be used across the package. 
These functions include logging, process management, string command execution, array creation from string input, argument checking, value comparison, and terminal string coloring. 
The functions are designed to facilitate various tasks such as executing commands dynamically, checking values against targets with optional tolerance, and managing subprocesses.
"""

import numpy as np
import ast
import copy
import psutil
from pylab_ml.common.data import str2num

mylogger = None


def set_logger(logger):
    """
    Set the logger for the package.
    
    Parameters
    ----------
        logger: A logger object that will be used for logging messages in the package.

    Returns
    -------
        None.
    """
    
    global mylogger
    mylogger = logger


def kill_proc_tree(pid=None, instance=None, including_parent=False):
    """
    Kill a process and all its children.
    
    Parameters
    ----------
        pid: The process ID of the parent process to kill. If None, it will be determined from the instance.
        instance: An optional instance that has a pid attribute. If provided, its pid will be used if pid is None.
        including_parent: A boolean indicating whether to also kill the parent process. Default is False.

    Returns
    -------
        None.
    """
    
    if pid is None and instance is None:
        return
    if pid is None and instance is not None:
        pid = instance.pid
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    for child in children:
        child.kill()
    gone, still_alive = psutil.wait_procs(children, timeout=5)
    if including_parent:
        parent.kill()
        parent.wait(5)
    if instance is not None:
        instance.terminate()
        del (instance)


def multistrcall(self, commandlist):
    """
    Execute multiple commands given in a dictionary format, where keys are command strings and values are the corresponding values to use in the command.
    
    Parameters
    ----------
        commandlist: A dictionary where keys are command strings to execute and values are the corresponding values to use in the command.
        eg: {'smu.voltage': 5.3, 'smu.current': 0.001}
        
    Returns
        None.
    """
    
    #    if type(command) == str:
    #        command = command.split(',')
    #        result = []
    for cmd in commandlist:
        strcall(self, cmd, commandlist[cmd][0])


def strcall(self, command, value=None, typ=None, mqttcheck=False):
    """
    Make a call from the command:
        result = common.strcall(tcc, 'regs.HW_ID.read()')
        result = common.strcall(self, 'smu.voltage=5.3' , mqttcheck=True)'
        result = common.strcall(self, 'smu.blabla()', 4.7, mqttcheck=True)'
    needs the the logger from self

    Parameters
    ----------
        command: Command string to execute, e.g. 'regs.HW_ID.read()', 'smu.voltage'
        value: The value to set or to use as parameter for the command, e.g. 5.3 for 'smu.voltage=5.3' or 30 for 'regs.ACL_OSC.write(30)'
        typ: If the command an mqtt-command, than you have coice if it is settable or gettable
        mqttcheck: Check if the command is in the mqtt_list. If not, the command will not be executed

    Returns
    -------
        The result of the command execution, or "ERROR" if there was an error during execution.
    """
    if self is None:
        print("strcall: initialise missing, self is None -> do nothing")
        return
    parent = self
    instname = self.instName + "." if hasattr(self, "instName") else ""
    mqttcmd = command
    if mqttcmd.find("(") > 0:
        mqttcmd = mqttcmd[: mqttcmd.find("(") + 1] + ")"
        typ = "func"
    elif typ is None and mqttcmd.find(':') < 0:
        typ = "get"
    if mqttcheck and mqttcmd not in ["mqtt_status"] + parent.mqtt_list:
        instname = parent.instName if hasattr(self, "instName") else parent
        print(f"   Warning strcall: {instname} get {mqttcmd}, but it is not in the mqtt_list")
        return "ERROR"
    if typ == "set":
        value = tuple(value) if type(value) is list else str2num(value)
        evalue = f'"{value}"' if isinstance(value, str) else value
        try:
            exec(f"self.{command} = {evalue}")
            print(f"   self.{instname}{command} := {value}")
            return None
        except Exception as ex:
            print(f"   strcall error: 'self.{instname}{command} := {value}' get an exception: {ex}")
            return "ERROR"
    elif typ == "get":
        try:
            value = eval(f"self.{command}")
            print(f"   self.{instname}{command} == {value}")
            return value
        except Exception as ex:
            print(f"   strcall get error: 'self.{instname}{command}' get an exception: {ex}")
            return "ERROR"
    elif typ == "func":
        command = command[: command.find("(")]
        para = ""
        if type(value) is list:
            for val in value:
                para += f"'{val}',"
            para = para[:-1]
        elif type(value) is str and value != "":
            para = f"'{value}'"
        elif value is not None:
            para = value
        try:
            result = eval(f"self.{command}({para})")
            print(f"   self.{instname}{command}({para})")
            return result
        except Exception as ex:
            print(f"   strcall error func: self.{instname}{command}({para}), get an exception: {ex}")
            return 'ERROR'


def convertExpr2Expression(Expr):    
    Expr.lineno = 0
    Expr.col_offset = 0
    result = ast.Expression(Expr.value, lineno=0, col_offset=0)
    return result


def exec_with_return(code, parent=None):
    """
    This function executes the given code and returns the result of the last expression in the code.
    Implemented from https://stackoverflow.com/questions/33409207/how-to-return-value-from-exec-in-function

    Parameters
    ----------
        code: TYPE
            DESCRIPTION.
            
        parent: TYPE, optional
            DESCRIPTION. The default is None.
    
    Returns
    -------
        None
    """
    code_ast = ast.parse(code)

    init_ast = copy.deepcopy(code_ast)
    init_ast.body = code_ast.body[:-1]

    last_ast = copy.deepcopy(code_ast)
    last_ast.body = code_ast.body[-1:]

    exec(compile(init_ast, "<ast>", "exec"), globals())
    if type(last_ast.body[0]) is ast.Expr:
        return eval(compile(convertExpr2Expression(last_ast.body[0]), "<ast>", "eval"), globals(), {"self": parent})
    else:
        exec(compile(last_ast, "<ast>", "exec"), globals(), {"self": parent})


def arange(myitems):
    """
    Create an array from a string in a format similar to Matlab,

    e.q. "18:-1:6:"
    "18:-1:6, 5.9:-0.1:4.1"
    "18:-1:6, 5.9:-0.1:4.1, 7, 9"

    also possible: "18:6:-1"
    
    Parameters
    ----------
        myitems: A string containing the items to create the array from, in a format similar to Matlab.
        eg. "18:-1:6, 5.9:-0.1:4.1, 7, 9"
    
    Returns
    -------
        result: An array created from the input string.
    """
    result = None
    if myitems.find(",") > 0:
        delimiter = ","
    elif myitems.find(";") > 0:
        delimiter = ";"
    else:
        delimiter = " "
    for item in myitems.split(delimiter):
        if item.find(":"):
            split = item.split(":")
            start = str2num(split[0])
            if len(split) == 1:
                myresult = start
            else:
                if len(split) == 2:
                    inc = 1
                    stop = str2num(split[1])
                else:
                    stop = str2num(split[2])
                    inc = 1 if len(split) < 3 else str2num(split[1])
                if inc > stop:
                    temp = inc
                    inc = stop
                    stop = temp
                if len(split) == 2 and start > stop:
                    inc = -1
                try:
                    correctur = inc  # to calculate like matlab 3:6:1 -> 3,4,5,6  normaly in python 3,4,5
                    myresult = np.arange(start, stop + correctur, inc)
                except Exception:
                    myresult = f"Syntax error in {item}"
        else:
            myresult = item
        result = myresult if result is None else np.append(result, myresult)
    return result


def choice(arg, myargs):
    """
    Check if the argument is in the list of valid arguments.

    Parameters
    ----------
        arg: The argument to check. (string)
        myargs: The list of valid arguments. (string or list of strings)

    Returns
    -------
        bool
            True if the argument is in the list of valid arguments, False otherwise.
    """
    if arg not in myargs:
        print(f"checkargs: attribute {arg} not valid")
        return False
    return True


def checkargs(myargs, **kwargs):
    """
    Check if the given arguments are valid.
    
    Parameters
    ----------
        myargs: The list of valid arguments. (string or list of strings)
        **kwargs: The arguments to check.

    Returns
    -------
        None.
    """
    for arg in kwargs:
        if arg not in myargs:
            print(f"checkargs: attribute {arg} not valid")


def check(msg, target, actual, tolerance=0, mask=None):
    """
    Compare target with the acutal value with optional tolerance and mask. 
    The target can be a string with mask information, e.g. "0x1X3" or "0b1x0", where 'X' or 'x' indicates a masked bit that will not be compared.

    Parameters
    ----------
        msg: A message to display with the comparison result.
        target: The target value:
                    if str and start with 0x than each X is a 4bit mask.
                    if str and start with 0b than each x is a 1bit mask.
        actual: The actual value to compare with the target.
        tolerance: The tolerance for comparing the target and actual values. Default is 0, which means an exact match is required.
        mask: An optional mask to apply to the target and actual values before comparing. If provided, the comparison will only consider the bits where the mask has a value of 1.

    Returns
    -------
        error: bool
            True: target = actual value.
            False: target != actual value.
    """
    error = 0
    if type(target) is str and len(target) > 3:
        if target[1] == "x":  # it is a hex number with mask information
            target = target.replace("_", "", len(target))
            mask = 0
            for index in range(2, len(target)):
                mask = (mask << 4) + (15 if target[index] != "X" else 0)
            target = str2num(target.replace("X", "0", len(target)))
        elif target[1] == "b":  # it is a bin number with mask information
            target = target.replace("_", "", len(target))
            mask = 0
            for index in range(2, len(target)):
                mask = (mask << 1) + (1 if target[index] != "x" else 0)
            target = str2num(target.replace("x", "0", len(target)))
    if type(actual) is not type(target):
        error = 1
        msg = f"{msg}  different type: target= {target}({type(target)}) <-> actual= {actual}({type(actual)}) -> couldn't check')"
    elif type(actual) is list:
        if len(target) != len(actual):
            logprint("WARNING", f": check len() from target list (={len(target)}) <-> actual list ({len(actual)}), are different!!!!")
        for index in range(0, len(actual)):
            if actual[index] != target[index]:
                logprint("ERROR", f"Wrong value at adr 0x{index:2x}, read 0x{actual[index]:x}, expected 0x{target[index]:x}")
                error += 1
        msg = f"{msg}: {len(actual)} Word checked ->"
        if error == 0:
            msg = f"{msg} OK"
        else:
            msg = f"{msg} {error} Errors"
    elif type(actual) is int:
        if mask is not None and (actual & mask) != (target & mask):
            error = 1
            msg = f"{msg}  target: 0x{target&mask:x} != actual: 0x{actual&mask:x}"
        elif mask is None and not (target - tolerance <= actual <= target + tolerance):    # actual != target:
            error = 1
            msg = f"{msg}  target: 0x{target:x} != actual: 0x{actual:x}" if tolerance == 0 \
                else f"{msg}: 0x{target:x} +- 0x{tolerance:x} <> 0x{actual:x}"
        else:
            msg = f"{msg} == 0x{actual:2x}"
    elif (type(actual) is str) or (type(actual) is bool):
        if target != actual:
            error = 1
            msg = f"{msg}  target: {target} != actual: {actual}"
        else:
            msg = "{msg} = {actual}"
    elif type(actual) is float:  # float checked with tolerance
        if (target < (actual - tolerance)) or (target > (actual + tolerance)):
            error = 1
            msg = f"{msg}:  expected {target} +- {tolerance} <>{actual}"
        else:
            msg = f"{msg}:  expected {target} +- {tolerance} == {actual}"
    else:
        logprint("ERROR", "pylab_ml.common.check: type {type(actual)} not yet implant !")
        error = 1
    if error > 0:
        logprint("ERROR", msg)
    else:
        logprint("MEASURE", msg)
    return error


def color(n, s):
    """
    Color a string for terminal output.
    
    Parameters
    ----------
        n: The name of the color or style to apply to the string.
        s: The string to color.
        
        eg. n = "red", s = "This is a red string"
        
    Returns
    -------
        value: The input string s wrapped in terminal color codes corresponding to the color or style n. 
        If n is not a valid color or style, the original string s is returned without modification.
    """
    code = {
        "bold": 1,
        "faint": 2,
        "italic": 3,
        "underline": 4,
        "blink_slow": 5,
        "blink_fast": 6,
        "negative": 7,
        "conceal": 8,
        "strike_th": 9,
        "ack": 30,
        "red": 31,
        "green": 32,
        "yellow": 33,
        "blue": 34,
        "magenda": 35,
        "cyan": 36,
        "white": 37,
        "black": 40,
        "b_red": 41,
        "b_green": 42,
        "b_yellow": 43,
        "b_blue": 44,
        "b_magenda": 45,
        "b_cyan": 46,
        "b_white": 47,
    }
    try:
        num = str(code[n])
        value = "\033[" + num + "m" + s + "\033[0m"
        return value
    except Exception:
        pass


def logprint(level, msg):
    """
    Print a message with a given log level, using the logger if set.
    
    Parameters
    ----------
        level: The log level of the message, e.g. "DEBUG", "INFO", "WARNING", "ERROR", "MEASURE".
        msg: The message to print.
        
    Returns
    -------
        None.
    """
    
    if mylogger is None:
        print(f"{level}: {msg}")
    else:
        if level == "DEBUG":
            mylogger.debug(msg)
        elif level == "MEASURE":
            mylogger.measure(msg)
        elif level == "INFO":
            mylogger.info(msg)
        elif level == "WARNING":
            mylogger.warning(msg)
        elif level == "ERROR":
            mylogger.error(msg)


if __name__ == "__main__":

    class test:

        mqtt_list = [
            "CH0.connect()",
            "CH0.drv.vdl",
            "CH0.drv.vdh",
            "CH0.disconnect()",
            "CH1.connect()",
            "CH1.drv.vdl",
            "CH1.drv.vdh",
            "CH1.disconnect()",
            "CH2.connect()",
        ]

        def strcall_test(self):
            strcall(
                self,
                'CH0.disconnect("PBUS_F")',
                value=None,
                typ=None,
                mqttcheck=True,
            )

    print(arange("18:5:-1"))
    print(arange("6:4:-1"))
    print(arange("6:4:-0.1"))
    print(arange("-6:-4:0.1"))
    print(arange("18:5:-1, 5.9:4.1:-0.1, 4:-18:-1, -18:5:1, 4.1:5.9:0.1, 6:19:1"))
    print(arange("18:5:-1, 5.9:4.1:-0.1, 5, 8"))
    print(arange("18:5:-1,  4, 8"))
    print(arange("18:5:-1   6, 9"))
    print(arange("18:5"))
    print(arange("5:5"))
