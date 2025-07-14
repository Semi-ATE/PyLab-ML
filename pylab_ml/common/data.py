"""Data manipulation functions."""
import time
import numpy as np
import datetime as dt


def unsigned_data(f):
    """
    Convert to 16-bit unsigned_data.

    Parameters
    ----------
    f : 16-bit value

    Returns
    -------
    unsigned 16-bit value

    """
    if f < 0.0:
        f += 65536.0
    return int(f)


def signed_data(f, bitwidth=16):
    """
    Convert to signed_data.

    Parameters
    ----------
    f : default 16-bit value or define bitwidht
    bitwidth: bit width

    Returns
    -------
    signed value

    """
    if f > (1 << bitwidth-1)-1:
        f -= (1 << bitwidth)
    return int(f)


def byte2word(list8):
    """Return a list with 16-bit data from a imput list with 8-bit data."""
    list16 = []
    for index in range(0, len(list8), 2):
        list16.append(list8[index] + (list8[index+1] << 8))
    return list16


def byte2uint(list8):
    """Return a list with 32-bit data from a imput list with 8-bit data."""
    list32 = []
    for index in range(0, len(list8), 4):
        list32.append(list8[index] + (list8[index+1] << 8) + (list8[index+2] << 16) + (list8[index+3] << 24))
    return list32


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


def crc16(word_array):
    """
    Calculate CRC-16 on array.

    Parameters
    ----------
    word_array : 16-bit word array

    Returns
    -------
    CRC-16

    """
    crctable = [0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50A5, 0x60C6, 0x70E7,
                0x8108, 0x9129, 0xA14A, 0xB16B, 0xC18C, 0xD1AD, 0xE1CE, 0xF1EF,
                0x1231, 0x0210, 0x3273, 0x2252, 0x52B5, 0x4294, 0x72F7, 0x62D6,
                0x9339, 0x8318, 0xB37B, 0xA35A, 0xD3BD, 0xC39C, 0xF3FF, 0xE3DE,
                0x2462, 0x3443, 0x0420, 0x1401, 0x64E6, 0x74C7, 0x44A4, 0x5485,
                0xA56A, 0xB54B, 0x8528, 0x9509, 0xE5EE, 0xF5CF, 0xC5AC, 0xD58D,
                0x3653, 0x2672, 0x1611, 0x0630, 0x76D7, 0x66F6, 0x5695, 0x46B4,
                0xB75B, 0xA77A, 0x9719, 0x8738, 0xF7DF, 0xE7FE, 0xD79D, 0xC7BC,
                0x48C4, 0x58E5, 0x6886, 0x78A7, 0x0840, 0x1861, 0x2802, 0x3823,
                0xC9CC, 0xD9ED, 0xE98E, 0xF9AF, 0x8948, 0x9969, 0xA90A, 0xB92B,
                0x5AF5, 0x4AD4, 0x7AB7, 0x6A96, 0x1A71, 0x0A50, 0x3A33, 0x2A12,
                0xDBFD, 0xCBDC, 0xFBBF, 0xEB9E, 0x9B79, 0x8B58, 0xBB3B, 0xAB1A,
                0x6CA6, 0x7C87, 0x4CE4, 0x5CC5, 0x2C22, 0x3C03, 0x0C60, 0x1C41,
                0xEDAE, 0xFD8F, 0xCDEC, 0xDDCD, 0xAD2A, 0xBD0B, 0x8D68, 0x9D49,
                0x7E97, 0x6EB6, 0x5ED5, 0x4EF4, 0x3E13, 0x2E32, 0x1E51, 0x0E70,
                0xFF9F, 0xEFBE, 0xDFDD, 0xCFFC, 0xBF1B, 0xAF3A, 0x9F59, 0x8F78,
                0x9188, 0x81A9, 0xB1CA, 0xA1EB, 0xD10C, 0xC12D, 0xF14E, 0xE16F,
                0x1080, 0x00A1, 0x30C2, 0x20E3, 0x5004, 0x4025, 0x7046, 0x6067,
                0x83B9, 0x9398, 0xA3FB, 0xB3DA, 0xC33D, 0xD31C, 0xE37F, 0xF35E,
                0x02B1, 0x1290, 0x22F3, 0x32D2, 0x4235, 0x5214, 0x6277, 0x7256,
                0xB5EA, 0xA5CB, 0x95A8, 0x8589, 0xF56E, 0xE54F, 0xD52C, 0xC50D,
                0x34E2, 0x24C3, 0x14A0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
                0xA7DB, 0xB7FA, 0x8799, 0x97B8, 0xE75F, 0xF77E, 0xC71D, 0xD73C,
                0x26D3, 0x36F2, 0x0691, 0x16B0, 0x6657, 0x7676, 0x4615, 0x5634,
                0xD94C, 0xC96D, 0xF90E, 0xE92F, 0x99C8, 0x89E9, 0xB98A, 0xA9AB,
                0x5844, 0x4865, 0x7806, 0x6827, 0x18C0, 0x08E1, 0x3882, 0x28A3,
                0xCB7D, 0xDB5C, 0xEB3F, 0xFB1E, 0x8BF9, 0x9BD8, 0xABBB, 0xBB9A,
                0x4A75, 0x5A54, 0x6A37, 0x7A16, 0x0AF1, 0x1AD0, 0x2AB3, 0x3A92,
                0xFD2E, 0xED0F, 0xDD6C, 0xCD4D, 0xBDAA, 0xAD8B, 0x9DE8, 0x8DC9,
                0x7C26, 0x6C07, 0x5C64, 0x4C45, 0x3CA2, 0x2C83, 0x1CE0, 0x0CC1,
                0xEF1F, 0xFF3E, 0xCF5D, 0xDF7C, 0xAF9B, 0xBFBA, 0x8FD9, 0x9FF8,
                0x6E17, 0x7E36, 0x4E55, 0x5E74, 0x2E93, 0x3EB2, 0x0ED1, 0x1EF0]

    crc = 0xFFFF

    for currWord in word_array:
        for j in range(2):
            if j == 0:
                currByte = (np.uint8)(currWord & 0x00FF)
            else:
                currByte = (np.uint8)((currWord >> 8) & 0x00FF)
            crc = (np.uint16)((crc << 8) & 0xFFFF) ^ crctable[((crc >> 8) ^ currByte) & 0x00FF]
    crc_low = (np.uint8)(crc >> 8)
    crc_high = (np.uint8)(crc)
    crc_swap = crc_low | (np.uint16(crc_high) << 8)
    return crc_swap


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


def datetime(typ=None):
    """Return the acual time as a string (year, month, day, _, hour, min, sec)."""
    if typ is None:
        date = time.localtime(time.time())
        return f'{date.tm_year:04d}{date.tm_mon:02d}{date.tm_mday:02d}_{date.tm_hour:02d}{date.tm_min:02d}{date.tm_sec:02d}'
    elif typ == "str""":
        return dt.datetime.now().strftime("%Y/%m/%d %H:%M:%S")


def str2num(value, base=10, default=""):
    """translate str to numeric value.

    if value start with 0x than it is a hex number.
    if value start with 0b than it is a binary number.
    if value = '' -> set to default value
    """
    #    if type(value) in [bool, int, float, np.int32, np.float64]:
    if type(value) is not str:
        return value
    value = value.strip()
    if value == "" or value is None:
        value = default
        return
    if value.find("0x") == 0:
        base = 16
    elif value.find("0b") == 0:
        base = 2
    try:
        return int(value, base)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value
