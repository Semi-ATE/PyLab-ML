"""
This script contains functions to handle the environment, such as inserting paths to sys.path and getting environment variables. 
It also includes a function to replace environment variables in a dictionary with their values.
"""
from pathlib import Path
import os
import pathlib
import inspect
from pylab_ml.common.data import str2num
from pylab_ml.common.common import choice
from pylab_ml.common.data import complement
# from pylab_ml.base_instrument import logger


def help():
    """ Lists all functions available in file_io module. """
    
    print("Lists all functions available in file_io module:")
    print("********************************************************")
    print(readVlogMemFile.__doc__)
    print("********************************************************")
    print(writeVlogMemFile.__doc__)


NETWORK = '//samba'


def filedialog(initialdir, title, filetypes):
    """
    Open a file dialog to select a file.
    
    eg. filedialog(initialdir='/path/to/directory', title='Select a file', filetypes=[('Text files', '*.txt'), ('All files', '*.*')]) will open a file dialog with the 
    specified initial directory, title, and file types to filter the displayed files. 
    The user can select a file, and the function will return the path to the selected file as a string.

    Parameters
    ----------
        initialdir : str
            The initial directory to open in the file dialog.
        title : str
            The title of the file dialog.
        filetypes : list of tuples
            The file types to display in the file dialog.

    Returns
    -------
        str
            filename : The selected file path.
    """
    
    from tkinter import Tk
    from tkinter import filedialog as fd

    root = Tk()
    root.withdraw()
    filename = fd.askopenfilename(initialdir=initialdir, title=title, filetypes=filetypes)
    root.destroy()
    return filename


def openFile(fileName, *argv, **kwargs):
    """
    Open a file with the given name.
    
    eg. openFile('data.txt', 'r') will open the file 'data.txt' in read mode and return the file object.
    
    Parameters
    ----------
        fileName : str
            The name of the file to open.
        *argv :
            Additional positional arguments to pass to the open function (e.g., mode, buffering, encoding).
        **kwargs :
            Additional keyword arguments to pass to the open function (e.g., mode='r', encoding='utf-8').
        
    Returns
    -------
        file : file object
            The opened file object, or None if the file cannot be opened.
    """
    fileName = replaceFilename(fileName)
    file = None
    try:
        file = open(fileName, *argv, **kwargs)
    except Exception:
        # logger.error(f'{inspect.stack()[1][3]}: Cannot open {fileName}')
        print(f'ERROR: {inspect.stack()[1][3]}: Cannot open {fileName}')
    return file


def replaceFilename(fileName):
    """
    Replace environment variables in the given file name with their values.
    
    eg. If the fileName is '$NETWORK/data.txt' and the 'NETWORK' environment variable is set to '//samba/proot', then this function will return '//samba/proot/data.txt'.
    
    Parameters
    ----------
        fileName : str
            The file name in which to replace environment variables.
            
    Returns
    -------
        str
            filename : The file name with environment variables replaced by their values.
    """
    
    if fileName.find('$') > -1:   # find environment variables inside the value?
        tmp = fileName.split('/')
        index = 0
        for s in tmp:
            if s.find('$') == 0:
                env = os.environ.get(s[1:])
                tmp[index] = env if env is not None else ''
            index += 1
        fileName = '/'.join(tmp)
    if len(fileName) > 0 and fileName[0] == '/' and os.name == "nt" and fileName.find(NETWORK) != 0:
        fileName = NETWORK + fileName
    return fileName


def get_latestfile(filename, logerror=None):
    """
    Get the file with the latest date.
    
    eg. If there are multiple files with the same prefix and suffix, this function will return the one with the latest date in the directory. 
    For example, if there are files named 'data_20210101.txt', 'data_20210201.txt', and 'data_20210301.txt', 
    and you call get_latestfile('data_*.txt'), it will return 'data_20210301.txt' as it has the latest date.

    Parameters
    ----------
        filename : str
            The file name with a prefix and suffix to search for. The prefix is the part of the file name before the wildcard '*', 
            and the suffix is the part of the file name after the wildcard '*'.
        logerror : function, optional
            A function to log errors. If None, errors will be printed to the console. Default is None.

    Returns
    -------
        str or None
            The file name with the latest date, or None if no matching files are found.
    """
    directory = os.path.split(filename)[0]
    prefix = os.path.basename('.'.join(filename.split('.')[:-1]))
    suffix = Path(filename).suffix
    files = os.listdir(directory)
    filesfound = []
    for f in files:
        if f.find(prefix) == 0 and Path(f).suffix == suffix:
            filesfound.append(f)
    if len(filesfound) == 0:
        msg = f"no files '{prefix}*{suffix}' found"
        if logerror is None:
            print(f"Error: {msg}")
        else:
            logerror(msg)
    else:
        return os.path.join(directory, filesfound[-1])


def loadIHexFile(fileName, bytemem=None, size=0x10000):
    """
    Load an Intel Hex file into a byte array.
    
    eg. loadIHexFile('firmware.hex') will read the Intel Hex file 'firmware.hex' and return a byte array containing the data from the file. 
    The function will read the file line by line, parse the Intel Hex format, and fill the byte array with the data from the file. 
    The function will also keep track of the address range of the data read from the file and print it out at the end.
    
    Parameters
    ----------
        fileName : str
            The name of the Intel Hex file to load.
        bytemem : list, optional
            A pre-allocated byte array to fill with the data from the file. If None, a new byte array will be created. Default is None.
        size : int, optional
            The size of the byte array to create if bytemem is None. Default is 0x10000 (64 KB).
            
    Returns
    -------
        list
            bytemem : A byte array containing the data from the Intel Hex file, with None entries for unused/initialized values.
    """

    try:
        fop = open(fileName, 'rt')
        print('loadIHexFile: open %s' % fileName)
    except Exception:
        print('loadIHexFile: Cannot open %s' % fileName)
        return None

    if bytemem is None:
        bytemem = [0] * size
    firstaddr = 0xffffffff
    lastaddr = 0x0
    addr_offset = 0
    # read const file
    for line in fop:
        if line[0:3] != ':00' and line[7:9] == '00':                # Data Record (Typ 00)
            byte_count = int(line[1:3], 16)
            addr = int(line[3:7], 16) + addr_offset
            if addr < firstaddr:
                firstaddr = addr
            if addr < size:
                if addr+byte_count-1 > lastaddr:
                    lastaddr = addr+byte_count-1
                    for i in range(byte_count):
                        bytemem[addr + i] = int(line[9 + (i * 2):11 + (i * 2)], 16)
        elif line[7:9] == '01':                                    # Enf of File Record (Typ 01)
            break
        elif line[7:9] == '02':                                    # Extended Segment Address Record (Typ 02)
            addr_offset = line[10:12] << 4
    fop.close()
    print('  Read IHex image in address range 0x%0X to 0x%0X' % (firstaddr, lastaddr))
    return bytemem


def readMemFile(filename, typ=None, interpret=None):
    """
    Read a memory file in the specified format (verilog, txt, or QEMem).
    
    eg. readMemFile('memory.txt', typ='txt') will read the memory data from the file 'memory.txt' in text format and return the starting address and a list of memory data. 
    The function will determine the type of the memory file based on the file extension if the 'typ' parameter is not provided. 
    It will then call the appropriate function to read the memory data based on the determined type (verilog, txt, or QEMem). 
    The function will return the starting address and a list of memory data, with None entries for unused/initialized values.
    
    Parameters
    ----------
        filename : str
            The name of the memory file to read.
        typ : str, optional
            The type of the memory file (e.g., 'verilog', 'txt', 'QEMem'). If None, the type will be determined based on the file extension. Default is None.
        interpret : dict, optional
            A dictionary with keys 'adr' and 'dat' to specify the base for interpreting addresses and data in text files. Default is None.
            
    Returns
    -------
        int
            start : The starting address of the memory data.
        list
            data : A list of memory data, with None entries for unused/initialized values.
    """
    extensions = {'v': 'verilog', 'txt': 'txt'}
    start = None
    if typ is None:
        file_extension = pathlib.Path(filename).suffix[1:]
        if file_extension in extensions.keys():
            typ = extensions[file_extension]
        else:
            typ = f'.{file_extension}'
    if not choice(typ, ['verilog', 'txt']):
        return False
    if typ == 'verilog':
        start, data = readVlogMemFile(filename, 0)      # TODO!:  change  readVlogMemFile to get automatically the size
    elif typ == 'txt':
        start, data = readtxtMemFile(filename, interpret)
    return start, data


def readtxtMemFile(fileName, memSize=None, bitsize_source=None, bitsize_target=None, numerative=None, raw_data=False):
    """
    Read a file with memory data in simple hex or integer format.
    
    eg. readtxtMemFile('memory.txt') will read the memory data from the file 'memory.txt' in text format and return the starting address and a list of memory data. 
    The function will read the file line by line, parse the address and data values, and fill a list with the memory data. 
    The function will also handle different bit sizes for the source and target data, and can return raw data if specified.

    Parameters
    ----------
        fileName : string
            The name of the text file containing memory data. 
            The file should have lines in the format "address data", where address and data can be in hex or decimal format.
        memSize : int
            Size from the reserved memory array.
        bitsize_source: int
            Size from one datum, eg. 8-bit, 16-bit, must be multiple times of 8
            This has an effect on the address counting.
            If None, each datum will be assigned to an address, otherwise each 8-bit datum has an address.
            Only little endian is supported yet.
        bitsize_target: int
            Size from one datum in the array result.
            Needed if negative values in the sourcefile.
        numerative : {adr : base, dat : base}
            Base for interpreting addresses and data in text files, e.g. 10 for decimal, 16 for hex.
            If None then default is 10 for both.
        raw_data: bool
            If True then return with a list of adr + data.
            If False then return with a coherent memory, beginning with startadr.

    Returns
    -------
        int
            minadr : The starting address of the memory data.
        list
            array : A list of memory data, with None entries for unused/initialized values.
            data : A list of tuples containing address and data pairs if raw_data is True, with None entries for unused/initialized values.

    """
    file = openFile(fileName)
    if file is None:
        return None
    base_adr = numerative['adr'] if (numerative is not None and 'adr' in numerative.keys()) else 10
    base_dat = numerative['dat'] if (numerative is not None and 'dat' in numerative.keys()) else 10

    data = []
    for line in file:
        parts = line.split()
        for index in range(0, len(parts)):
            value = parts[index]
            if value == '//':
                break
            value = str2num(value, base_adr if index == 0 else base_dat)
            if type(value) is str:
                continue
            if index == 0:
                adr = value
                continue
            if bitsize_source is None:
                data.append((adr, value))
            else:
                for i in range(bitsize_source // 8):
                    data.append((adr, value % 256))
                    value = value // 256
                    adr += 1
                continue
            adr += 1
    file.close()
    if raw_data:
        return data
    minadr = min(data)[0]
    maxadr = max(data)[0]+1
    bitsize_source = 8 if bitsize_source is None else bitsize_source
    array = [None]*((maxadr-minadr) // (bitsize_source//8)) if memSize is None else [None]*memSize
    adr = minadr
    for index in range(0, len(data)):
        adr = data[index][0]
        dat = data[index][1]
        realadr = (adr-minadr) // (bitsize_source//8)
        oldat = 0 if array[realadr] is None else array[realadr]
        shift = adr % (bitsize_source//8)
        array[realadr] = (dat << (shift*8)) + oldat
    if bitsize_target is not None:
        for index in range(0, len(array)):
            if array[index] < 0:
                array[index] = complement(abs(array[index]), bitsize_target) + 1   # calculated 2 complement
    return minadr, array


def readQEMemFile(fileName, base=0x20):
    """
    Read a file with memory data in the DUMP_QE Software format.

        base address 0
        address 0
        data hex	0000	data dec	0
        address 1
        data hex	0000	data dec	0

    Parameters
    ----------
        fileName : string
            The name of the text file containing memory data in DUMP_QE format.
        base : int
            The base address for the memory data.

    Returns
    -------
        int
            minadr : The starting address of the memory data.
        list
            array : A list of memory data, with None entries for unused/initialized values.
    """
    file = openFile(fileName)
    if file is None:
        return None
    data = []
    for line in file:
        parts = line.split()
        if parts[0] == 'base':
            baseadr = int(parts[2])
            continue
        elif parts[0] == 'address':
            adr = baseadr * base + int(parts[1])
        elif parts[0] == 'data':
            value = str2num(parts[2], 16)
            data.append((adr, value))
    file.close()
    minadr = min(data)[0]
    maxadr = max(data)[0]+1
    array = [None]*(maxadr-minadr)
    for index in range(0, len(data)):
        array[data[index][0]-minadr] = data[index][1]
    return minadr, array


def readVlogMemFile(fileName, memSize=0, defaultvalues=None, bitwidth=None, debug=False):
    """
    Read a file with memory data in verilog hex format. 

    eg. readVlogMemFile('memory.v') will read the memory data from the file 'memory.v' in verilog hex format and return the starting address and a list of memory data.
        The function will read the file line by line, parse the address and data values in verilog hex format, and fill a list with the memory data.
        The function will also determine the memory size and bit width from the data in the file if memSize and bitwidth parameters are not provided.
                
    Parameters
    ----------
        fileName : string
            The name of the verilog file containing memory data.
        memSize : int
            The number of memory addresses. If 0, the size will be calculated from the data in the file.
        defaultvalues : int
            The default values for the memory array if no data is read.
        bitwidth : int
            The bit width of the data.
        debug : bool
            If True, it prints out the data loaded.

    Returns
    -------
        int
            startadr : The starting address of the memory data.
        list
            data : A list of memory data, with None entries for unused/initialized values.
    """
    fi = openFile(fileName, 'rt')
    if fi is None:
        return fi

    startadr = 0
    calc_memSize = 0
    calc_bitwidht = bitwidth
    for line in fi:         # get the memsize from the file
        parts = line.split()
        try:
            if len(parts) == 0 or (len(parts) > 0 and parts[0] == '//'):
                continue
            elif parts[0][0] == "@":
                adr = int(parts[0][1:], 16)
                calc_memSize = adr if adr >= calc_memSize else calc_memSize
                startadr = adr if adr <= startadr else startadr
                parts.pop(0)
            if len(parts) > 0:
                for value in parts:
                    int(value, 16)
                    calc_memSize += len(value) * 4 // bitwidth
                    calc_bitwidht = len(value) * 4
        except Exception:
            continue
    fi.seek(0)

    memSize = calc_memSize if memSize == 0 else memSize
    data = [defaultvalues]*(memSize)
    adr = 0
    for line in fi:
        parts = line.split()
        try:
            if len(parts) == 0 or (len(parts) > 0 and parts[0] == '//'):
                continue
            elif parts[0][0] == "@":
                adr = int(parts[0][1:], 16)
                if len(parts[1] * 4) > bitwidth:
                    v = []
                    for i in range(0, len(parts[1]), 2):
                        v.append(int(parts[1][i:i+2], 16))
                else:
                    v = int(parts[1], 16)
            else:
                v = int(parts[0], 16)
            if adr < len(data):
                if type(v) is not list:
                    data[adr] = v
                else:
                    i = len(v) - 1
                    for dat in v:
                        data[adr+i] = dat
                        i -= 1
            else:
                # logger.error('VlogMemFile: %s > %d value(s)' % (fileName, memSize))
                print('ERROR: VlogMemFile: %s > %d value(s)' % (fileName, memSize))
                fi.close()
                return
            adr += 1
        except Exception:
            continue
    # logger.info('VlogMemFile: %s read with %d value(s)' % (fileName, len(data)))
    print('VlogMemFile: %s read with %d value(s)' % (fileName, len(data)))
    if debug:
        for i, v in enumerate(data):
            # logger.debug('0x%X: 0x%X' % (i, v))
            print('0x%X: 0x%X' % (i, v))
    fi.close()
    return startadr, data


def writeVlogMemFile(fileName, mem, a_dig=4, d_dig=8, adroffset=0, adrinc=1, header=["", "verilog memory data file", ""]):
    """
    Write memory data to a file in verilog hex format.
    
    eg. writeVlogMemFile('memory.v', mem) will write the memory data from the list 'mem' to the file 'memory.v' in verilog hex format. 
    The function will write the data to the file in the format "@address data", where address is the memory address in hexadecimal and data is the memory data in hexadecimal. 
    The function will also include a header at the top of the file as comments, and will allow for customization of the address and data formatting through the parameters.
    
    Parameters
    ----------
        fileName : string
            Path to the verilog file.
        mem : list
            List with integer memory data.
        a_dig : int
            Minimum address digits.
        d_dig : int
            Minimum data digits.
        adroffset : int
            Address offset.
        adrinc : int
            Increment address by.
        header : list
            List of strings placed as comments at the top of the file.

    Returns
    -------
        bool
            True if the file was successfully written, False otherwise.
    """
    fi = openFile(fileName, 'wt', newline='\n')
    if fi is None:
        return False
    for comment in header:
        fi.write(f'// {comment}\n')
    for i, v in enumerate(mem):
        if v is not None:
            fi.write('@{:0{}x} {:0{}x}\n'.format(i*adrinc+adroffset, a_dig, v, d_dig))
    fi.write(' ')
    fi.close()
    return True

def readVerilogMemFile(filename):
    """
    Parses an EEPROM file with format '@Address Data' in hex and returns a dictionary with decimal keys and values.

    Parameters
    ----------
        filename : string
            Path to the EEPROM file.

    Returns
    -------
        eeprom_dict : dict
            Dictionary with address (decimal) as keys and data (decimal) as values.
    """
    eeprom_dict = {}
    
    try:
        with open(filename, 'r') as file:
            for line in file:
                line = line.strip()
                # Ensure the line starts with '@' and has both address and data
                if line.startswith('@'):
                    parts = line.split()
                    if len(parts) >= 2:
                        # Extract and clean hex strings
                        hex_address = parts[0].replace('@', '')
                        hex_data = parts[1]
                        
                        # Convert hex to decimal
                        address_decimal = int(hex_address, 16)
                        data_decimal = int(hex_data, 16)
                        
                        # Store in dictionary
                        eeprom_dict[address_decimal] = data_decimal
        
        return eeprom_dict

    except FileNotFoundError:
        print(f"Error: The file '{filename}' was not found.")
        return {}
    except ValueError:
        print(f"Error: Could not convert a value in the file. Check the hex format.")
        return {}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {}


if __name__ == '__main__':
    data = [1, 2, 3, 4, 5]
    writeVlogMemFile('schrott.v', data)
