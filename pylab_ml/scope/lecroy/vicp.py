"""
This script provides an interface to the LeCroy Oscilloscopes using the VICP protocol.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>

"""
import socket
import struct


class OP():
    DATA = 0b10000000
    REMOTE = 0b01000000
    LOCKOUT = 0b00100000
    CLEAR = 0b00010000
    SQR = 0b00001000
    SERIAL_POLL = 0b00000100
    Reserved = 0b00000010
    EOI = 0b00000001


class VICP():
    """ Interface to LeCroy Oscilloscopes using the VICP protocol. """

    def __init__(self, addr='LCRY3703N15966', port=1861, timeout=5, debug=False):
        """ 
        Initialize the VICP interface.
        
        Parameters
        ----------
            addr : str
                The IP address or hostname of the LeCroy Oscilloscope.
            port : int
                The TCP/IP port of the LeCroy Oscilloscope (default is 1861).
            timeout : float
                The timeout for socket operations in seconds (default is 5).
            debug : bool
                If True, enables debug output (default is False).
        """
        self.debug = debug
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addr = addr
        self.s.connect((self.addr, port))

    def __del__(self):
        """ Ensure the socket is closed when the object is deleted. """
        self.s.close()

    def write_raw(self, data):
        """
        Write raw bytes to the VICP interface.
        
        Parameters
        ----------
            data : bytes
                The raw bytes to send to the VICP interface.
        """
        
        if self.debug:
            print('    write_raw:{!r}'.format(data))
        header = [0] * 4
        header[0] = OP.DATA + OP.EOI
        header[1] = 1       # header version
        header[2] = 0       # sequence number
        header[3] = 0       # unused
        header = bytes(header) + struct.pack('>I', len(data))
        self.s.send(header + bytes(data))

    def write(self, data, term=''):
        """
        Write a string to the VICP interface, optionally with a termination string. 
        
        Parameters
        ----------
            data : str
                The string to send to the VICP interface.
            term : str
                An optional termination string to append to the data (default is '').
        """
        data += term
        self.write_raw(data.encode())

    def read_bytes(self, size=1):
        """
        Read a specified number of bytes from the VICP interface.
        
        Parameters
        ----------
            size : int
                The number of bytes to read (default is 1).
        
        Returns
        -------
            data : bytes
                The bytes read from the VICP interface.
        """
        
        data = b''
        while len(data) < size:
            data += self.s.recv(size - len(data))
            if self.debug:
                print('    read_bytes: {} / {}'.format(len(data), size))
        return data

    def read_chunk(self, size=None):
        """
        Read a chunk of data from the VICP interface, optionally specifying the size.
        
        Parameters
        ----------
            size : int
                The number of bytes to read (if None, the size is determined from the header).
                
        Returns
        -------
            data : bytes
                The chunk of data read from the VICP interface.
        """
        header = self.read_bytes(8)
        if size is None:
            size = struct.unpack('>I', header[4:])[0]
        if self.debug:
            print('    read_chunk: {!r} => size = {}'.format(header, size))
        data = self.read_bytes(size)
        return data

    def read_raw(self):
        """
        Read raw data from the VICP interface until a newline character is encountered.
        
        Returns
        -------
            data : bytes
                The raw data read from the VICP interface.
        """
        chunks = []
        while True:
            chunk = self.read_chunk()
            chunks.append(chunk)
            if chunk.endswith(b'\n'):
                break
        return b''.join(chunks)

    def read(self):
        """
        Read a string from the VICP interface until a newline character is encountered.
        
        Returns
        -------
            data : str
                The string read from the VICP interface.
        """
        return self.read_raw().decode().rstrip('\n')

    def query(self, data):
        """
        Send a query to the VICP interface and read the response.
        
        Parameters
        ----------
            data : str
                The query string to send to the VICP interface.
                
        Returns
        -------
            str
                The response string read from the VICP interface.
        """
        self.write(data)
        return self.read()

    def close(self):
        """ Close the VICP interface. """
        self.s.close()
