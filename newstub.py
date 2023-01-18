import time
import multiprocessing
import string
import types
import traceback
import random
import numpy as np
from pynq import MMIO
import typesystem.hop_types as ht
start_time = time.time()
# config/debug space
REGSPACE_ADDR = 0x40
STATUS_OFFSET = 4


class Stub:
    def __init__(self, context, name, signature):
        self.context = context
        self.name = name
        self.signature = signature
        (self.result_offset, self.result_addr) = context.add(name, 2)
        self.result_status_offset = self.result_offset + 1

    def from_meta_dict(context, funcType, name, meta):
        stubDict = {
            "hardware" : HardwareStub,
            "python"   : None, # TODO: allow python stubs to be initialised from files
            "cpp"      : None # TODO: Create CPP Stub
        }

        return stubDict[funcType](context, name, meta)

    def stubFromVar(context, var, sig = None, name = None):
        if not sig:
            sig = ht.Type.typeMatch(var)

        if sig.is_list():
            ps = ListStub(context, sig, var, name)
        elif sig.is_base() or sig.is_tuple():
            ps = VarStub(context, sig, var, name)
        else:
            raise RuntimeError("Python function arguments not yet implemented")

        return ps

    def printContext(self):
        print(self.signature)
        self.context.print(self.result_offset, self.result_status_offset+1)



class HardwareStub(Stub):
    def __init__(self, context, name, meta, debugWrites = False):
        signature = ht.parse(meta['signature'])
        self.base_addr = meta['base']
        self.regspace_offset = REGSPACE_ADDR
        self.hwMemory = MMIO(self.base_addr, 65536, debug=debugWrites)
        self.debugWrites = debugWrites
        super().__init__(context, name, signature)

        if signature.is_function():
            self.__createFunctionStub(meta)

    def __createFunctionStub(self, meta):
        self.regspace_addr = REGSPACE_ADDR
        self.arg_offsets = list()
        for i in range(0, self.signature.arity()):
            self.arg_offsets.append(meta['regspace'][f'arg{i + 1}_offset'])

        self.ret_offset = meta['regspace']['ret_offset']

    def __transformToStub(self, args):
        stubArgs = list()
        for a in args:
            aStub = a
            if not isinstance(a, Stub):
                aStub = Stub.stubFromVar(self.context, a)
            stubArgs.append(aStub)
        return stubArgs


    def __printWrite(self, address, data):
        if self.debugWrites:
            print(f'[{time.time() - start_time}] {self.name}: write: ' +
                  f'*({address}) = {data}')

    def __regspaceWrite(self, offset, data):
        realOffset = offset * 0x4
        self.__printWrite(f'{self.hwMemory.base_addr} + {self.regspace_offset} + {realOffset}', data)
        self.hwMemory.write(self.regspace_offset + realOffset, data)

    def __call__(self, *args):
        args = self.__transformToStub(args)
        if not self.signature.typeCheck(args):
            raise TypeError(f'expected \'{self.signature}\'')

        # Control Register: AP_START = 1, AUTO_RESTART = 1
        self.__printWrite(self.hwMemory.base_addr, 1 | (1 << 7))
        self.hwMemory.write(0x0, 1 | (1 << 7))

        # HARDWARE STATUS: Should be in idle state

        # All of the following code fills out the CEP
        # Specify the CEP address
        self.__regspaceWrite(1, self.base_addr + self.regspace_offset)
        # If this is a function, it we need to supply where to fetch arguments from
        if self.signature.is_function():
            ## Supply the argument addresses for all
            for i in range(self.signature.arity()):
                ## Supply argument addresses in CEP
                self.__regspaceWrite(self.arg_offsets[i], args[i].result_addr)

        ## Specify REP address
        self.__regspaceWrite(self.ret_offset, self.result_addr)

        # HARDWARE STATUS: Should now be waiting for the first argument if it needs any.
        # It would have written where it expects the first argument to the result address of the argument

        # Evaluate the arguments
        if self.signature.is_function():
            # Argument Loop - Call the arguments and insert their results
            for i in range(self.signature.arity()):
                ## Leaving this here just in case
                while self.context.value(args[i].result_addr) == 0:
                    print(f'[{time.time() - start_time}] Waiting in evaluation loop.')
                    if self.debugWrites:
                        print(self.context.mem.device_address + self.result_offset)
                        self.printRegspace(10)
                        self.context.print(self.result_offset, self.result_offset+2)
                    time.sleep(1)

                # Initiate our own MMIO interface that points to this stub's CEP
                # The result offset is what the hardware has written to be used as the argument
                # value address. Look in the previous HARDWARE STATUS.
                regIO = MMIO(self.context.get(args[i].result_offset), 0x8, debug=True)
                ## Write the arguments
                a = int(args[i]())
                self.__printWrite(regIO.base_addr, a)
                regIO.write(0x0, a)

                ## Write the status flag
                self.__printWrite(f'{regIO.base_addr} + 4', 1)
                regIO.write(0x4, 1)

                ## Clears the above values (I've yet to figure this part out)
                self.context.clear(args[i].result_addr + 4)

        # HARDWARE STATUS: Should now be performing function.
        # We have filled in all the arguments in the above loop.

        # CEP is now filled, we wait until HW has filled REP
        self.__listen()
        if self.debugWrites:
            print('-----------------------------------')
            self.printRegspace(0,16)
            self.context.print(self.result_offset, self.result_offset+2)
            print(f'res = {self.res}')
        return self.res

    def __listen(self):
        while self.context.get(self.result_status_offset) == 0:
            # Massive sleep for debug
            print(f'[{time.time() - start_time}] Waiting in listen loop.')
            if self.debugWrites:
                print(self.context.mem.device_address + self.result_offset)
                self.printRegspace(10)
                self.context.print(self.result_offset, self.result_offset+2)
            time.sleep(1)
        self.context.clear(self.result_addr + 4)
        self.res = self.context.get(self.result_offset)

    # ---- Debugging -----
    def printRegspace(self, start, stop=None):
        if not stop:
            stop = start + 1
        regMMIO = MMIO(self.base_addr + self.regspace_offset, 16 * 0x4)
        print(f'{self.name} regspace ({self.hwMemory.base_addr} + '
              f'{self.regspace_offset} = {self.hwMemory.base_addr + self.regspace_offset}):')
        for i in range(start, stop):
            print(f'[{i}] = {regMMIO.read(i*4)}')

    def printRegStatus(self):
        self.printRegspace(STATUS_OFFSET)

# This is currently unused
class PythonStub(Stub):
    def __init__(self, context, signature, obj, name) -> None:
        if signature.is_function():
            self.function = obj
        else:
            self.function = lambda : obj

        super().__init__(context, name, signature)

    def __call__(self, *args)->int:
        return self.function()

    def __str__(self):
        # This will cause problems
        return str(self.function())

class VarStub(Stub):
    def __init__(self, context, signature, var, name=None):
        if callable(var):
            # Since for the moment we ignore side effects, functions which
            # take no input and give an output might as well be pre-computed.
            # The type system would see such a function as just a variable.
            self.var = var()
        else:
            self.var = var

        super().__init__(context, name, signature)

    def __call__(self):
        return self.var



class ListStub(Stub):
    def __init__(self, context, signature, l, name=None):
        self.l = l
        super().__init__(context, name, signature)

    def __call__(self, i):
        return l[i]

    def __str__(self):
        return str(self.l)
