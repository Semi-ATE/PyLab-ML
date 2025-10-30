# -*- coding: utf-8 -*-
"""
Created on Fri Aug  8 15:18:15 2025

@author: Zlin526F
"""
import math
from time import time
from pylab_ml.common.data import complement


class MER:
    SIZE = 4

    pmer = ["r0", "r1", "w0", "w1"]

    def __init__(self, log_error):
        self.log_error = log_error
        self._values = ["read 0"] * self.SIZE                           # define 4 March Element Register, default value = "read 0"

    def __getitem__(self, index):
        if not isinstance(index, int) or not (1 <= index < self.SIZE+1):
            self.log_error(f"Index={index}, must be between 1 and {self.SIZE}")
        return self._values[index-1]

    def __setitem__(self, index, value):
        if not isinstance(index, int) or not (1 <= index < self.SIZE+1):
            self.log_error(f"Index must be between 1 and {self.SIZE}")
            return
        if not isinstance(value, str) or value not in self.pmer:
            self.log_error(f'Wert must be {self.pmer}')
            return
        trvalue = 'read ' if value[0] == 'r' else 'write '
        trvalue = trvalue + value[1]
        self._values[index-1] = trvalue
        for i in range(index, self.SIZE):
            self._values[i] = None
        self.cnt = index


class Memory_test():
    """
    
    TODO:   
        - only data background = sdb implemented, missing: 'bdb', 'rdb', 'cdb'
        - Address counting according to the actual layout structure is missing. 
            - bin x = linear counting
            - bin y missing
        - operation next missing
        - operation hammer missing
    """
    pdata_background = ['sdb',              # solid DB - all bits with same data
                        'bdb'               # checkerboard DB - adjacent cells with different data    not implemented
                        'rdb'               # row stripes DB                                          not implemented
                        'cdb'               # column striped DB                                       not implemented
                         ]
    pcount_method = ['bin x', 'complement']
    padr_order = ['up', 'down']
    
    algo_ops = {'Scan':            {'len' :4, 'ops': [['up', 'w0'],
                                                      ['r0'],
                                                      ['down', 'w1'],
                                                      ['r1']]},
                'Scan Complement': {'len': 4, 'ops': [['up', 'w0'],
                                                      ['complement', 'r0'],
                                                      ['bin x', 'down', 'w1'],
                                                      ['complement', 'r1']]},
                'Scan+':           {'len': 8, 'ops': [['up', 'w0'],
                                                      ['r0'],
                                                      ['down', 'w1'],
                                                      ['r1'],
                                                      ['w0'],
                                                      ['r0'],
                                                      ['up', 'w1'],
                                                      ['r1']]},
                'MATS+':           {'len': 5, 'ops': [['up', 'w0'],
                                                      ['r0', 'w1'],
                                                      ['down', 'r1', 'w0']]},
                'March C-':        {'len': 10, 'ops': [['up', 'w0'],
                                                       ['r0', 'w1'],
                                                       ['r1', 'w0'],
                                                       ['down', 'r0', 'w1'],
                                                       ['r1', 'w0'],
                                                       ['r0']]},
                'PMOVI':           {'len': 13, 'ops': [['down', 'w0'],
                                                       ['up', 'r0', 'w1', 'r1'],
                                                       ['r1', 'w0', 'r0'],
                                                       ['down', 'r0', 'w1', 'r1'],
                                                       ['r1', 'w0', 'r0']]},
                'March U':         {'len': 13, 'ops': [['up', 'w0'],
                                                       ['r0', 'w1', 'r1', 'w0'],
                                                       ['r0', 'w1'],
                                                       ['down', 'r1', 'w0', 'r0', 'w1'],
                                                       ['r1', 'w0']]},
                'March LR':        {'len': 14, 'ops': [['up', 'w0'],
                                                       ['down', 'r0', 'w1'],
                                                       ['up', 'r1', 'w0', 'r0', 'w1'],
                                                       ['r1', 'w0'],
                                                       ['r0', 'w1', 'r1', 'w0'],
                                                       ['r0']]},
               # 'BLIF = 10n':     # TODO implement next command
               # 'HAMW8 = 41n':    # TODO implement hammer command
                'BLIF-':           {'len': 8, 'ops':  [['up', 'w0'],
                                                       ['w1', 'r1', 'w0'],
                                                       ['w1'],
                                                       ['w0', 'r0', 'w1']]},
                'Algor. B':        {'len': 17, 'ops': [['up', 'w0'],
                                                       ['r0', 'w1', 'w0', 'w1'],
                                                       ['r1', 'w0', 'r0', 'w1'],
                                                       ['down', 'r1', 'w0', 'w1', 'w0'],
                                                       ['r0', 'w1', 'r1']]},
                # 'HAMR8 = 18n':    # TODO implement hammer command
              }
              

    def __init__(self, parent, bitwidth, start, end, readfunc, writefunc, beforefunc=None, afterfunc=None):
        self.parent = parent
        self.start = start
        self.end = end
        self.readfunc = readfunc
        self.writefunc = writefunc
        self.beforefunc = beforefunc
        self.afterfunc = afterfunc
        self._ao = 'up'                             # address order
        self._cm = 'bin x'                          # counting method posible values = self.pcount_method
        self._db = 'sdb'                            # data background = self.pdata_background
        self.bitwidth = bitwidth

        self.mer = MER(self.parent.log_error)
        self.error_values = []
        
    def algorithmen(self, alist):
        if type(alist) != list:
            self.parent.log_error(f'Argument have to be a list. Values are {list(self.algo_ops.keys())}')
            return 1
        errors = 0
        for name in alist:
            if name not in self.algo_ops.keys():
                self.parent.log_error(f'Name from algorithmus not availabe, values are {list(self.algo_ops.keys())}')
                errors += 1
            else:
                errors += self.algorithmus(f"{name} = {self.algo_ops[name]['len']}n", self.algo_ops[name]['ops'])
        return errors

    def algorithmus(self, name, operations):
        starttime = time()
        self.parent.log_info(f'Memory-Test: will run {name}')
        errors = 0
        # set default values
        self._ao = 'up'                             # address order
        self._cm = 'bin x'                          # counting method posible values = self.pcount_method
        self._db = 'sdb'                            # data background = self.pdata_background
        for operation in operations:
            mer_index = 1
            for sop in operation:
                if sop in self.padr_order:
                    self.adr_order = sop
                elif sop in self.pcount_method:
                    self._cm = sop
                elif sop in self.pdata_background:
                    self._db = sop
                elif sop in self.mer.pmer:
                    self.mer[mer_index] = sop
                    mer_index += 1
                else:
                    self.parent.log_error(f'  Memory_test operation {sop} not valid')
            errors += self.run()
        msg = f"   Memory_test result: {name} run in {time()-starttime:.2f}s, found {errors} Errors"
        if errors != 0:
            self.parent.log_error(msg)
        else:
            self.parent.log_info(msg)
        return errors

    def run(self, start=None, end=None):
        """read/write memory with the commands in the march element registers."""
        if self.beforefunc is not None:
            self.beforefunc()
        start = start if start is not None else self.start
        end = end if end is not None else self.end

        self._inc = 1 if self.adr_order == 'up' or self._cm == 'complement' else -1
        self._startadr = start if self.adr_order == 'up' or self._cm == 'complement' else end
        self._endadr = end + self._inc if self.adr_order == 'up' or self._cm == 'complement' else start+self._inc
        self._space = abs(self._endadr - self._startadr)
        space_bits = int(math.log2(self._space))

        self.error_values = []
        counting = f"{self.adr_order:10s}" if not self._cm == 'complement' else "complement"
        self.parent.log_info(f'    Memory_test: from 0x{self._startadr:0x} to 0x{self._endadr-self._inc:0x} {counting} = {self._space} values do {self.mer._values}')

        adr = self._startadr
        compare_data = [[] for _ in range(self.mer.SIZE)]
        errors = 0
        docomp = False
        dump = []
        for cnt in range(self._space):
            mer_cnt = 1
            while mer_cnt != self.mer.cnt+1:
                operand, dat = self.mer[mer_cnt].split(' ')
                cdata = int(f"{dat*self.bitwidth}", 2)                  # data to write, or target read data
                data = getattr(self, operand)(adr, cdata)               # call read/write
                if operand == 'read':
                    compare_data[mer_cnt-1].append([adr, cdata])
                    dump.append(data)
                mer_cnt += 1

            if self._cm == 'complement' and not docomp:
                docomp = True
                lastadr = adr
                adr = self._startadr + complement(adr - self._startadr, space_bits)
            elif docomp:
                docomp = False
                adr = lastadr + self._inc
            else:
                adr += self._inc
                    
        if self.afterfunc is not None:
            dump = self.afterfunc()                                   # get list from all read (=captured) values,
        compare_data_length = sum(len(row) for row in compare_data)
        if len(dump) != compare_data_length:
            self.parent.log_error(f' Memory_test: dump error, read {len(dump)} values, should be {compare_data_length}')
            return 1
        len_compare_data = [len(adata) for adata in compare_data]
        cntarrays = len(compare_data) - len_compare_data.count(0)
        pdump_start = 0
        read_data = compare_data.copy()
        for length, index in zip(len_compare_data, range(len(len_compare_data))):
            if length > 0:
                pdump = dump[pdump_start::cntarrays]           # assign the result to the correct operation (=array)
                pdump_start += 1
                read_data[index] = [[x[0], y] for x, y in zip(read_data[index], pdump)]
                read_data[index].sort(key=lambda x: x[0])
                compare_data[index].sort(key=lambda x: x[0])
                mer_error = 0
                if read_data[index] != compare_data[index]:
                    for rd, cd in zip(read_data[index], compare_data[index]):
                        if rd[1] != cd[1]:
                            mer_error += 1
                            self.parent.log_error(f"  read error 0x{rd[0]:0x} = 0x{rd[1]:0x} != target 0x{cd[1]:0x}")
                    self.parent.log_error(f"Memorytest '{self.mer[index+1]}' found {mer_error} errors")                 
                errors += mer_error
        return errors

    def read(self, adr, compare=None):
        dat = self.readfunc(adr)
        return dat

    def write(self, adr, dat):
        self.writefunc(adr, dat)

    @property
    def adr_order(self):
        """Address Order, up or down."""
        return self._ao

    @adr_order.setter
    def adr_order(self, value):
        if value not in self.padr_order:
            self.parent.log_error(f"Memory_test: wrong address order: {value} should be {self.padr_order}")
            return
        self._ao = value

    @property
    def count_method(self):
        """Counting method."""
        return self._cm

    @count_method.setter
    def count_method(self, value):
        if type(value) is not str and value not in self.pcount_method:
            self.parent.log_error(f"Memory_test: wrong counter: {value} should be {self.pcount_method}")
            return
        self._cm = value

    @property
    def data_background(self):
        """Data background.

         'sdb' - solid DB - all bits with same data
         'bdb' - checkerboard DB - adjacent cells with different data
         'rdb' - row stripes DB
         'cdb' - column striped DB
        """
        return self._ao

    @data_background.setter
    def data_background(self, value):
        if value not in self.pdata_background:
            self.parent.log_error(f"Memory_test: data_background: {value} should be {self.pdata_background}")
            return
        self._db = value
