"""
This script contains functions to handle the environment, such as inserting paths to sys.path and getting environment variables. 
It also includes a function to replace environment variables in a dictionary with their values.
"""
import os
import sys

__author__ = "Zlin526F"
__copyright__ = "Copyright 2023, Lab"
__credits__ = ["Zlin526F"]
__email__ = "Zlin526F@github"
__version__ = '0.0.1'


def path_insert(self, path, check=True, append=False):
    """
    Insert a path into sys.path if it does not already exist.
    
    eg. path_insert('/path/to/directory', check=True, append=False) will insert the specified path at the beginning of sys.path if it does not already exist and if the path exists on the filesystem. 
    If check is False, it will insert the path without checking if it exists. 
    If append is True, it will insert the path at the end of sys.path instead of the beginning.

    Parameters
    ----------
        path : str
            The path to be inserted into sys.path.
        check : bool, optional
            If True, insert only if the path does not exist in sys.path. Default is True.
        append : bool, optional
            If True, insert the path at the bottom of sys.path. Default is False.

    Returns
    -------
        bool
            True if the path was successfully inserted or already exists, False otherwise.
    """
    if path is None:
        self.log_error('pylab_ml: setup path==None')
        return False
    path = os.path.normcase(path)
    found = False
    method = 'insert'
    if append:
        method = 'append'
    for entry in sys.path:
        if entry == path:
            found = True
    if not found and check and not os.path.exists(path):
        self.log_error('pylab_ml: setup path {} not exist'.format(path))
        return False                           # not OK
    elif not found and os.path.exists(path):
        if not append:
            sys.path.insert(0, path)
        else:
            sys.path.append(path)
        self.log_info("pylab_ml: add {} {} to Path".format(method, path))
        return True                            # OK
    elif found and os.path.exists(path):
        # print("   {} already exist in Path".format(path))
        return True                           # OK


def environ_getpath(self, key):
    '''
    Get the value of an environment variable and adjust it for network paths on Windows if necessary.
    
    eg. If the environment variable 'DATA_PATH' is set to '/data' and the 'NETWORK' environment variable is set to '\\\\samba', 
    then on Windows, this function will return '\\\\samba\\data' instead of '/data'.
    
    Parameters
    ----------
        key : str
            The name of the environment variable to retrieve.
            
    Returns
    -------
        str or None
            result : The value of the environment variable, adjusted for network paths on Windows if necessary. 
            Returns None if the environment variable is not found.
    '''
    result = os.environ.get(key)
    if result is None:
        msg = f'pylab_ml: key {key} not found in environment'
        if hasattr(self, "log_error"):
            self.log_error(msg)
        else:
            print(msg)
        return None
    network = os.environ['NETWORK'] if os.environ['NETWORK'] is not None else ''
    if network != '' and os.name == "nt" and (result.find('/') == 0 or result.find('\\') == 0) and result.find(network) != 0:
        result = network + result
        os.environ[key] = result
    return result

def checkNetworkPath(name, network=''):
    """
    Check if the given path name is a network path on Windows and adjust it if necessary.
    
    eg. If name is '/data' and the 'NETWORK' environment variable is set to '\\\\samba', 
    then on Windows, this function will return '\\\\samba\\data' instead of '/data'.
    
    Parameters
    ----------
        name : str
            The path name to check and adjust if necessary.
        network : str, optional
            The network path to prepend if the path is a network path on Windows. Defaults to ''.

    Returns
    -------
        str
            name : The adjusted path name.
    """
    
    envName = 'NETWORK'
    if envName in os.environ and os.environ[envName] and network=='':
        network = os.environ[envName]
    elif envName in os.environ and os.environ[envName] is None and network != '':
        os.environ[envName] == network
    if name is not None and network != '' and os.name == "nt" and (name.find('/') == 0 or name.find('\\') == 0) and name.find(network) != 0:
        name = network + name
    return name


def replaceEnvs(dictionary, network=''):
    """
    Recursively replace environment variables in a dictionary with their values.
    
    eg. If the dictionary is {'path': '$NETWORK_PATH'} and the 'NETWORK_PATH' environment variable is set to '//samba', 
    then this function will replace '$NETWORK_PATH' with '//samba' in the dictionary, resulting in {'path': '//samba'}.
    
    Parameters
    ----------
        dictionary : dict
            The dictionary in which to replace environment variables.
        network : str, optional
            The network path to prepend if the path is a network path on Windows. Defaults to ''.

    Returns
    -------
        dict
            The dictionary with environment variables replaced by their values.
    """
    for key in dictionary:
        if type(dictionary) == dict:
            value = dictionary[key]
        else:
            value = key
        if type(value) == dict or type(value) == list:
            replaceEnvs(value)
        elif type(value) == str and value.find('$') > -1:   # find environment variables inside the value?
            split = value.split(';')                        # better to use reg to replace $name
            nvalue = ''
            for paths in split:
                tmp = paths.split('/')
                pvalue = ''
                for s in tmp:
                    found = s.find('$')
                    if found >= 0:
                        s = os.environ.get(s[found+1:])
                        if s is None:
                            break
                    pvalue += s + '/'
                if pvalue != '':
                    nvalue += pvalue + ';'
            if nvalue != '':
                if type(dictionary) == dict:
                    dictionary[key] = nvalue[:-1]
                else:
                    dictionary[1] = nvalue[:-1]
        elif type(value) == str and len(value) > 0 and value[0] == '/' and os.name == "nt" and value.find(f'{network}') != 0:
            if type(dictionary) == dict:
                dictionary[key] = network + value
            else:
                dictionary[1] = network + value
    return(dictionary)
