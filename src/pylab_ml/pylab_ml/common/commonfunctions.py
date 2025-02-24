"""Common functions."""
import os
from pathlib import Path


def complement(value, bits):
    """Binary complement from a value with number of bits."""
    formatstring = '{:0%ib}' % bits
    bvalue = formatstring.format(value)
    return int(''.join({'0': '1', '1': '0'}[x] for x in bvalue), 2)


def crc4(data):             # width
    """
    Calculate 4-bit crc from a data with widht bits.

    polynomial = X4+X+1

    """
    data = f'{data:0b}'
    crcdat = 0
    for bit in data:
        doinvert = int(bit) ^ ((crcdat & 8) >> 3)      # DoInvert = ('1'==BitString[i]) ^ CRC[3];
        crc = (crcdat << 1) & 0xc                      # CRC[3] = CRC[2]; CRC[2] = CRC[1];
        crc |= ((crcdat & 1) ^ doinvert) << 1          # CRC[1] = CRC[0] ^ DoInvert;
        crc |= doinvert                                # CRC[0] = DoInvert;
        crcdat = crc
    return crc


def Parity(data, even=True):
    """
    Return the parity-bit from the data.

    Parameters
    ----------
    data : int
    even : selection parity, even or odd

    Returns
    -------
      1 if data is even numbers of "1"
      0 if data is odd numbers of "1"
    """
    data = bin(data)
    parity = 1 if even else 0
    for i in range(0, len(data)):
        parity += 1 if data[i] == '1' else 0
    return parity % 2


def j1850_crc(buffer, length=None):
    """J1850 CRC-Calculation.


    Parameters
    ----------
    buffer : arry of byte
        DESCRIPTION.
    length : integer value
        frame length

    Returns
    -------
       crc result
    """
    length = len(buffer) if length is None else length
    crc_reg = 0xff

    for byte_count in range(0, length):
        bit_point = 0x80
        for bit_count in range(0, 8):
            if bit_point & buffer[byte_count]:                 # case for new bit = 1
                poly = 1 if crc_reg & 0x80 else 0x1c           # define the polynomial
                crc_reg = ((crc_reg << 1) & 0xff | 1) ^ poly
            else:                                              # case for new bit = 0
                poly = 0x1d if crc_reg & 0x80 else 0
                crc_reg = ((crc_reg << 1) & 0xff) ^ poly
            bit_point >>= 1
    return complement(crc_reg, 8)                            # Return CRC


def get_latestfile(filename, logerror=None):
    """
    Get the file with the latest date.

    Parameters
    ----------
    logger :
    filename : string
        prefix from the file

    Returns
    -------
    return with the latest file with the name 'filename'.

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
    elif len(filesfound) == 1:
        return os.path.join(directory, filesfound[0])
    else:
        msg = f"more than one file '{prefix}*{suffix}' found\n this is not implemented yet:-("
        if logerror is None:
            print(f"Error: {msg}")
        else:
            logerror(msg)
    return filename
