"""
Created on Thu Jan  7 17:18:03 2021

This script is for handling json dictionaries, especially for the projectsetup.json file. 
It includes a custom JSON decoder, a dictionary list class (diclist) for handling lists of dictionaries, a setup string class (setupstr) for handling arange-like strings, and a dot dictionary class (dotdict) for allowing dot notation access to dictionary attributes.
The main class, JsonDict, is used to load a json file and convert it into a dot-dictionary format, allowing for easy access and manipulation of the data.
It also includes a method to replace environment variables in the json data with their actual values, and a method to write the modified data back to a json file.

TODO: started from projectsetup, so, some functions have to delete or to clear....

@author: jung
"""
import os
import json

# from pylab_ml.base_instrument import logger
from pylab_ml.misc import common
from pylab_ml.misc import file_io


__author__ = "Zlin526F"
__credits__ = ["Zlin526F"]
__email__ = "Zlin526F@github"


class JsonDecoder(json.JSONDecoder):
    def decode(self, obj):
        # TODO: implementend parser for hexnumbers and other special formats....
        return json.JSONDecoder.decode(self, obj)


class diclist(list):
    """A custom list class for handling lists of dictionaries, allowing for dot notation access and additional methods for retrieving keys and values."""

    def __init__(*args, **kwargs):
        global myparent
        if len(args) > 1:
            myparent = args[1]
            args = list(args)
            del args[1]
        list.__init__(*args, **kwargs)

    def __getattr__(mylist, key):
        """
        Get the value(s) from the key found in mylist. If the key is not found, return None.
        
        Parameters
        ----------
            mylist : list
                The list of dictionaries to search through.
            key : str
                The key to search for in the dictionaries.
                
        Returns
        -------
            The value(s) associated with the key if found, or None if the key is not found in any of the dictionaries.
        """
        
        if key in mylist:
            list.__getattribute__(mylist, key)
        else:
            return diclist.values(mylist, key)

    def keys(mylist):
        """
        Get the unique keys from a list of dictionaries.
        
        eg. keys([{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'city': 'New York'}]) will return ['name', 'age', 'city'].
        
        Parameters
        ----------
            mylist : list
                The list of dictionaries to search through.
                
        Returns
        -------
            result : list
                A list of unique keys found in the dictionaries within mylist.
        """
        result = []
        for item in mylist:
            for key in item.keys():
                if key not in result:
                    result.append(key)
        return result

    def index(mylist, index, value=None):
        """
        Get the dictionary/dictionaries from the list where the key 'index' has the value 'value'. 
        If value is None, return all dictionaries that contain the key 'index'.
        
        eg. index([{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'city': 'New York'}], 'name', 'Alice') will return {'name': 'Alice', 'age': 30}.
            index([{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'city': 'New York'}], 'name') will return [{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'city': 'New York'}].
        
        Parameters
        ----------
            mylist : list
                The list of dictionaries to search through.
            index : str or int
                The key to search for in the dictionaries or the index if an integer is provided.
            value : any, optional
                The value to match for the given key. If None, all dictionaries containing the key are returned.
                
        Returns
        -------
            result : dict or list
                If 'index' is an integer, the dictionary at that index in mylist is returned.
                If 'index' is a string, a list of dictionaries matching the criteria is returned. 
                If only one dictionary matches, that dictionary is returned directly.
        """
        
        if type(index) is int:
            return mylist[index]
        else:
            result = []
            for count in mylist:
                if index in count:
                    if value is None or (value is not None and count[index] == value):
                        result.append(count)
            if len(result) == 1:
                return result[0]
            return result

    def values(mylist, key=None):
        """
        Get the value(s) from the key found in mylist. If the key is not found, return None.
        
        eg. values([{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'city': 'New York'}], 'name') will return ['Alice', 'Bob'].
            values([{'name': 'Alice', 'age': 30}, {'name': 'Bob', 'city': 'New York'}], 'age') will return [30, None].
            
        Parameters
        ----------
            mylist : list
                The list of dictionaries to search through.
            key : str, optional
                The key to search for in the dictionaries. If None, all values from all dictionaries are returned.
                
        Returns
        -------
            result : list
                A list of values associated with the key if found, or None if the key is not found in any of the dictionaries. If key is None, a list of all values from all dictionaries is returned.
        """
        result = None
        # if key is not None and key in diclist.keys(mylist):
        if key is not None:
            if len(diclist.keys(mylist)) == 1:
                result = list(mylist[diclist.keys(mylist).index(key)].values())
            else:
                result = []
                for index in mylist:
                    if key in index:
                        result.append(index[key])
        elif len(mylist) > 0:
            result = []
            for item in mylist:
                if key is None:
                    value = list(item.values())[0]
                elif key in list(item.values())[0].keys():
                    value = list(item.values())[0][key]
                else:
                    value = None
                if type(value) is str:
                    value = common.str2num(value)
                result.append(value)
        return result

    def run(mylist, **kwargs):
        """
        Run the macro defined in mylist. The macro is determined by the last accessed dot-dictionary (myparent.mylastdotdic) and the commands are given in mylist.
        The result of the macro execution can be optionally written to the setup.result json file if 'output' in kwargs is set to 'wr2setup'.
        
        Parameters
        ----------
            mylist : list
                The list of commands to execute as part of the macro.
            **kwargs : dict
                Optional keyword arguments for macro execution. 
                If 'output' is set to 'wr2setup', the result of the macro execution will be written to the setup.result json file.
                
        Returns
        -------
            result : any
                The result of the macro execution, which can be of any type depending on the macro's functionality. If the macro is not defined, a warning message is printed and None is returned.
        """
        result = None
        if myparent is not None and hasattr(myparent, "runmacro"):
            # logger.debug(f'run macro {myparent.mylastdotdic}: {mylist}')
            print(f"run macro {myparent.mylastdotdic}: {mylist}")
            result = myparent.runmacro(mylist, **kwargs)
        else:
            # logger.error(f'No instruction how to should interprete the list: {mylist}')
            print(f"No instruction how to should interprete the list: {mylist}")
        return result


class setupstr(str):
    """ A custom string class for handling arange-like strings, allowing for parsing of strings in the format 'start:step:end' to generate a list of values. """
    
    def arange(items):
        """ Parse an arange-like string in the format 'start:step:end' and return a list of values generated according to the specified start, step, and end values. """
        return common.arange(items)

    def start(items):
        """ Get the starting value from an arange-like string in the format 'start:step:end'. """
        return common.arange(items)[0]

    def end(items):
        """ Get the ending value from an arange-like string in the format 'start:step:end'. """
        return common.arange(items)[-1]


class dotdict(dict):
    """ dot.notation access to dictionary attributes. """

    def myget(keyname, value):
        """ Get the value associated with 'keyname' in the dictionary. If 'keyname' is not found, return None. 
        
        Parameters
        ----------
            keyname : str
                The key to search for in the dictionary.
            value : any
                The value associated with the key, used for logging purposes. If the key is not found, this value is included in the error message.
                 If the key is found, this value is not used.
                 
        Returns
        -------
            result : any
                The value associated with 'keyname' in the dictionary, or None if the key is not found.
        """
        result = dict.get(keyname, value)
        if value not in ["size", "shape"]:
            myparent.mylastdotdic = value
            # print(f'keyname: {keyname},\nvalue: {value},\nresult: {result},\n')
            if result is None:
                # logger.warning(f"'dotdict' has no attribute {value} -> result is None")
                raise AttributeError(f"'dotdict' has no attribute {value} ")
        return result

    __getattr__ = myget  # __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class JsonDict(object):
    """ 
    Class for the handling json dictionaries. It includes methods for loading a json file, converting it to a dot-dictionary format, 
    replacing environment variables, and writing the modified data back to a json file. 
    """

    _RESULT = "result_projectsetup.json"
    _SETUPFILE = "tb_projectsetup.json"
    _MYCLASS = "myclass"

    def __init__(self, filename):
        """ Open a json-file and assign the values to a dot-dictionary. """
        if filename is dict:
            self.contents = filename
        elif os.path.exists(filename):
            print(filename)
            with file_io.openFile(filename, "r") as file:
                try:
                    self.contents = json.load(file, cls=JsonDecoder)
                except Exception as error:
                    # logger.error(f"JsonDict: syntax error in {filename} : {error}")      # TODO!: add json validator: pip install jsonschema
                    print(f"    JsonDict: syntax error in {filename} : {error}")
                    return None
        else:
            # logger.error(f"JsonDict: {filename} not exists:")
            print(f"    JsonDict: {filename} not exists:")
            return None
        self.contents = self.create_dotdic(self.contents, self)
        self.mylastdotdic = None
        self.lastresult = None
        self.lastmacro = None

    def create_dotdic(self, dic, root=None):
        """ 
        Make from a dictionary a dot-dictionary with diclist. 
        If the dictionary contains a list, make from this list a diclist.
        If the dictionary contains a string with arange-function, make from this string a setupstr
        
        eg. create_dotdic({'instruments': {'smu': {'port': 'pxie5'}}}) will return a dot-dictionary where you can access the port with setup.instruments.smu.port.
        
        Parameters
        ----------
            dic : dict
                The dictionary to convert into a dot-dictionary format.
            root : dotdict, optional
                The root dot-dictionary to use for recursive calls. Defaults to None, in which case the current instance is used as the root.
                
        Returns
        -------
            dotdict
                The converted dot-dictionary.
        """
        if type(dic) == list:
            mydic = diclist(root, dic)
            for index in range(0, len(dic)):
                mydic[index] = self.create_dotdic(mydic[index])
            return mydic
        for mydic in dic.keys():
            if type(dic[mydic]) == dict:
                if root is not None:
                    object.__setattr__(root, mydic, self.create_dotdic(dic[mydic]))
                dic[mydic] = self.create_dotdic(dic[mydic])
            elif type(dic[mydic]) == list:
                dic[mydic] = diclist(self, dic[mydic])
            elif type(dic[mydic]) == str and dic[mydic].find(":") > 0:  # found an arange-function -> change to setupstr
                dic[mydic] = setupstr(dic[mydic])
        return dotdict(dic)

    def _replaceSomeThing(self, jsontable):
        """
        Check if jsontable has environment-variables starts with $, or jsontable has path-value.

        eg. If jsontable is {'path': '$NETWORK_PATH'} and the 'NETWORK_PATH' environment variable is set to '//samba', 
        then this function will replace '$NETWORK_PATH' with '//samba' in jsontable, resulting in {'path': '//samba'}.
        
        Parameters
        ----------
            jsontable : dict or list
                The dictionary or list to check for environment variables and path values. If it's a dictionary, it will check the values for environment variables. If it's a list, it will check the items in the list for environment variables.
                
        Returns
        -------
            None
                This function modifies jsontable in place and does not return anything.
        """
        for key in jsontable:
            if type(jsontable) == dict:
                value = jsontable[key]
            else:
                value = key
            if type(value) == dict or type(value) == list:
                self._replaceSomeThing(value)
            elif type(value) == str and value.find("$") > -1:  # find environment variables inside the value?
                tmp = value.split("/")
                nvalue = ""
                for s in tmp:
                    if s.find("$") == 0:
                        s = os.environ.get(s[1:])
                    nvalue += s + "/"
                if nvalue != "":
                    if type(jsontable) == dict:
                        jsontable[key] = nvalue[:-1]
                    else:
                        jsontable[1] = nvalue[:-1]
            elif (
                type(value) == str
                and len(value) > 0
                and value[0] == "/"
                and os.name == "nt"
                and value.find(f"{self.network}") != 0
            ):
                if type(jsontable) == dict:
                    jsontable[key] = self.network + value
                else:
                    jsontable[1] = self.network + value

    def write(self, path, name=None, value=None):
        """
        Write path to the dictionary in my class ProjectSetup.

        Path must be a string like 'instruments.smu'
        normaly append this path to result
        if path start with setup than write to setup.path

        eg. write('instruments.smu', 'port', 'pxie5')
             write('setup.HostName', os.environ.get('COMPUTERNAME'))
             
        Parameters
        ----------
            path : str
                The dot-separated path indicating where to write the value in the dictionary. 
                For example, 'instruments.smu' would indicate that the value should be written to the 'smu' dictionary within the 'instruments' dictionary.
            name : str, optional
                The key name to use when writing the value. If None, the value will be appended to the list at the specified path. 
                If provided, the value will be written as a dictionary with 'name' as the key and 'value' as the value.
            value : any, optional
                The value to write to the dictionary at the specified path. 
                This can be of any type depending on the structure of the dictionary and the intended use. 
                If 'name' is provided, this value will be associated with 'name' in a new dictionary; if 'name' is None, this value will be appended directly to the list at the specified path.
                
        Returns
        -------
            None
                This function modifies the dictionary in place and does not return anything.
        """
        path = path.split(".")
        lastindex = "result"
        if path[0] == "setup":
            lastindex = "setup"
            path.pop(0)
        mydic = self.__dict__[lastindex]
        lastdic = mydic
        for index in path:
            if index not in mydic.keys():  # than create new dictionary
                if type(mydic) is diclist:
                    if mydic == []:
                        lastdic[lastindex] = dotdict({index: diclist(self)})
                        mydic = lastdic[lastindex]
                    else:
                        mydic.append(dotdict({index: diclist(self)}))
                        mydic = lastdic[lastindex][-1]
                else:
                    mydic[index] = diclist(self)
            lastdic = mydic
            if type(mydic) is diclist:
                mydic = mydic.values(index)
            else:
                mydic = mydic[index]
            lastindex = index
        if name is None:
            mydic += [value]
        else:
            mydic += [{name: value}]

    def runmacro(self, cmdlist, **kwargs):
        """
        Execute commands in the cmdlist.
        
        eg. If cmdlist is ['instruments.smu.port'], this function will attempt to access the 'port' attribute of the 'smu' dictionary within the 'instruments' dictionary, and return its value.

        Parameters
        ----------
            cmdlist : list
                A list of commands to execute. Each command is a string that represents a path to access within the dictionary. 
                For example, 'instruments.smu.port' would indicate that the function should access the 'port' attribute of the 'smu' dictionary within the 'instruments' dictionary.
            **kwargs : dict
                Optional keyword arguments for macro execution. 
                If 'output' is set to 'wr2setup', the result of the macro execution will be written to the setup.result json file.
                
        Returns
        -------
            result : any
                The result of the macro execution, which can be of any type depending on the macro's functionality. 
                If the macro is not defined, a warning message is printed and None is returned.
        """
        wr2setup = False
        if "output" in kwargs:
            wr2setup = kwargs["output"] == "wr2setup"
        result = []
        macro = myparent.mylastdotdic
        self.lastmacro = macro
        for cmd in cmdlist:
            myresult = self.call(cmd)
            if myresult is not None:
                result.append(myresult)
                self.lastresult = result
            if wr2setup:
                self.write(macro, cmd, myresult)
        if len(result) == 1:
            result = result[0]
        self.lastresult = result
        if cmdlist == []:
            # logger.warning(f'Macro {macro} not defined in setup')
            print(f"Macro {macro} not defined in setup")
            if wr2setup:
                self.write("macro", macro, "not defined in setup")
        return result

    def _write(self):
        """ Write the dictionary to the logfile. """
        # self.__dict__.pop('init')
        with open(self._RESULT, "w") as outfile:
            outfile.write("{")
            self.jsondump(outfile, self.setup)
            outfile.write("    ,\n")
            self.jsondump(outfile, "result")
            # json.dump(self.setup, outfile, indent=2)
            # json.dump(self.result, outfile, indent=2)     # sort_keys=True
            outfile.write("\n}")
        # logger.info(f'write results to {self._RESULT}')
        print(f"write results to {self._RESULT}")

    def jsondump(self, file, dictionary, ident=4):
        """
        Dump the dictionary to json-format.
        You can also use json.dump but I think this generated output-format is better for easy reading.
        
        Parameters
        ----------
            file : file object
                The file object to which the dictionary will be written in json format.
            dictionary : dict or list
                The dictionary or list to be written in json format.
            ident : int, optional
                The indentation level for formatting the json output. Defaults to 4.
                
        Returns
        -------
            None
                This function writes the dictionary to the specified file in json format and does not return anything.
        """

        def space(ident, lenght=2):
            if lenght < 2 and ident > 4:
                return
            for i in range(0, ident):
                file.write(" ")

        end = ""
        spara = "{"
        if type(dictionary) is str:
            space(ident, 3)
            file.write(f'"{dictionary}": {spara}')
            dictionary = self.__dict__[dictionary]
            end = "}"
            ident = 8
            space(ident, 3)
        length = len(dictionary)
        index = 0
        more = ","
        cr = "\n"
        if length < 2 and ident > 4:
            cr = ""
        else:
            pass
        file.write(f"{cr}")
        for item in dictionary:
            index += 1
            if index == length:
                more = ""
            if type(dictionary) in [dict, dotdict]:
                value = dictionary[item]
            else:
                value = dictionary[index - 1]
            spara = "{"
            epara = "}"
            if type(value) in [list, diclist]:
                spara = "["
                epara = "]"
            if type(value) in [dict, dotdict, list, diclist]:
                space(ident, length)
                try:
                    if item == value and type(item) is dict:  # is it a list with dictionaries
                        json.dump(item, file)
                        file.write(f"{more}{cr}")
                    elif item == value:  # it is a list with dotdictionaries
                        file.write(f"{spara}")
                        self.jsondump(file, value, ident + 4)
                        file.write(f"{epara}{more}{cr}")
                    else:  # it is dict or dotdict
                        file.write(f'"{item}": {spara}')
                        self.jsondump(file, value, ident + 4)
                        file.write(f"{epara}{more}{cr}")
                except Exception:
                    file.write(f"ERROR!!!: coudn't write {item} as json dump {more}{cr}")
            else:
                if type(value) == str:
                    value = f'"{value.replace(os.sep, "/")}"'
                space(ident, length)
                if item != value:
                    file.write(f'"{item}": {value}{more}{cr}')
                else:
                    file.write(f"{value}{more}{cr}")
        if cr != "":
            space(ident - 4, length)
        file.write(f"{end}")

    def __repr__(self):
        # return f"{self.contents}"
        return f"{self.__class__}"


if __name__ == "__main__":
    from pytestsharing.instruments.base_instrument import logsetup

    logsetup()

    tests = JsonDict(
        r"C:\Users\jung\Work Folders\Projecte\Repository\hatc\0203\units\lab\source\python\tb_ate\definitions\test\test.json"
    )
    print(tests.contents.keys())
    print(tests.contents.values(key="name"))
    print(tests.contents.values(key="hardware"))
    tests.contents.index(0)
    shmoo_values = []
    for name in tests.contents.values(key="name"):
        input_paramters = tests.contents.index("name", name).definition.input_parameters
        for key in input_paramters.keys():
            if input_paramters[key].Shmoo and key not in shmoo_values:
                shmoo_values.append(key)
    print(shmoo_values)
