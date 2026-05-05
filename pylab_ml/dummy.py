"""
Basic Dummy class for instance.

:Date: |today|
:Author: Semi-ATE <info@Semi-ATE.org>
"""


class Dummy(object):
    """Dummy object  for an communication-instance .

    :Date: |today|
    :Author: Semi-ATE <info@Semi-ATE.org>

    Usable if you have no real serial device, but you want avoid an Exception if you make access to this device

    """

    def __init__(self, parent, logger, **kwargs):
        """Initialise."""
        self.parent = parent
        self.logger = logger
        # kwargs = {"addr": addr, "interface": interface, "backend": backend, "identify": identify, "instName": instName}
        if 'message' in kwargs:
            self.logger.error(kwargs['message'])
        else:
            self.logger.error(f'{self.parent.instName}.inst: Device or no connection found,  use Dummy instead')
        self._lastcmd = ''
        self.bytes_in_buffer = 0

    def query(self, cmd):
        if cmd == '*IDN?':
            return f'{self.__class__}\r'
        cmd = cmd[:cmd.find('?')]
        try:
            value = super(__class__, self).__getattribute__(cmd)
            try:
                value = int(value)
            except Exception:
                pass
            self.logger.debug(f'Dummy {self.parent.instName} query {cmd} == {value}')
        except Exception:
            value = 0xdeadbeef
            self.logger.debug(f'Dummy {self.parent.instName} query {cmd} == {hex(value)}')
        return value

    def write(self, cmd):
        self._lastcmd = cmd[:cmd.find('?')] if cmd.find('?') > -1 else ''
        cmd = cmd.split(' ')
        if len(cmd) > 1:
            object.__setattr__(self, cmd[0], cmd[1])
        self.logger.debug(f'Dummy {self.parent.instName} write {cmd}')

    def read(self):
        # value = 0xdeadbeef
        value = '-2'
        self.logger.debug(f'Dummy {self.parent.instName} read value')
        return value

    def flush(self, arg=None):
        pass

    def __getattribute__(self, name):
        try:
            value = super(__class__, self).__getattribute__(name)
        except Exception:
            # value = 0xdeadbeef
            value = '-2'
        return value

    def close(self):
        self.logger.debug(f'Dummy {self.parent.instName} close Dummy instance')
