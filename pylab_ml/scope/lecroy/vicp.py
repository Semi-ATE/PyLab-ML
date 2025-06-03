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

    def __init__(self, addr='LCRY3703N15966', port=1861, timeout=5, debug=False):
        self.debug = debug
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addr = addr
        self.s.connect((self.addr, port))

    def __del__(self):
        self.s.close()

    def write_raw(self, data):
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
        data += term
        self.write_raw(data.encode())

    def read_bytes(self, size=1):
        data = b''
        while len(data) < size:
            data += self.s.recv(size - len(data))
            if self.debug:
                print('    read_bytes: {} / {}'.format(len(data), size))
        return data

    def read_chunk(self, size=None):
        header = self.read_bytes(8)
        if size is None:
            size = struct.unpack('>I', header[4:])[0]
        if self.debug:
            print('    read_chunk: {!r} => size = {}'.format(header, size))
        data = self.read_bytes(size)
        return data

    def read_raw(self):
        chunks = []
        while True:
            chunk = self.read_chunk()
            chunks.append(chunk)
            if chunk.endswith(b'\n'):
                break
        return b''.join(chunks)

    def read(self):
        return self.read_raw().decode().rstrip('\n')

    def query(self, data):
        self.write(data)
        return self.read()

    def close(self):
        self.s.close()
