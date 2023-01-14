import time
import multiprocessing
import string
import types
import traceback
import random
import numpy
from pynq import MMIO
import typesystem.hop_types as ht
start_time = time.time()
# config/debug space
REGSPACE_ADDR = 0x40



class Stub:
    def __init__(self, context, name, signature):
        self.context = context
        self.name = name
        self.signature = signature
        self.context_addr = context.add(name, 2)

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
    def __init__(self, context, name, meta):
        signature = ht.parse(meta['signature'])
        self.base_addr = meta['base']
        self.regspace_offset = REGSPACE_ADDR
        self.hwMemory = MMIO(self.base_addr, 65536, debug=True)
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


    def __regspaceWrite(self, offset, data):
        realOffset = offset * 0x4
        self.hwMemory.write(self.regspace_offset + realOffset, self.data)

    def __call__(self, *args):
        args = self.__transformToStub(args)
        if not self.signature.typeCheck(args):
            raise TypeError(f'expected \'{self.signature}\'')

        # Control Register: AP_START = 1, AUTO_RESTART = 1
        self.mmio.write(0x0, 1 | (1 << 7))

        # All of the following code fills out the CEP
        # Specify the CEP address
        self.__regspaceWrite(1, self.base_addr + 0x40)
        # If this is a function, it we need to supply where to fetch arguments from
        if self.signature.is_function():
            ## Supply the argument addresses for all
            for i in range(self.signature.arity()):
                ## Supply argument addresses in CEP
                self.__regspaceWrite(self.arg_offsets[i], args[i].context_addr)
        ## Specify REP address
        self.__regspaceWrite(self.ret_offset, self.context_addr)

        # Evaluate the arguments
        if self.signature.is_function():
            # Argument Loop - Call the arguments and insert their results
            for i in range(self.signature.arity()):
                ## Leaving this here just in case
                count = 0
                while self.context.value(args[i].context_addr) == 0:
                    # I want to see if this ever trips
                    print(f'[{time.time() - start_time}] BEING HELD IN ARG LOOP')
                    time.sleep(1)
                    count += 1

                ## Initiate our own MMIO interface that points to this stub's CEP
                cepIO = MMIO(self.context.value(args[i].context_addr), 65536)
                ## Write the arguments
                cepIO.write(0, args[i])
                ## Write the result status (not zero = success) to (&argument + 0x4)
                cepIO.write(4, 1)

                ## Clears the above values (I've yet to figure this part out)
                self.context.clear(args[i].context_addr)

        # CEP is now filled, we wait until HW has filled REP
        self.__listen()
        return self.res

    def __listen(self):
        count = 0
        while self.context.get(4) == 0:
            # I want to see if this ever trips
            assert(False)
            print(f'[{time.time() - start_time}] BEING HELD IN LISTEN LOOP WITH VAL: {self.context.get(4)}')
            count = count + 1
        self.context.clear(self.context_addr+4)
        self.res = self.context.get(0)
    # ---- Debugging -----
    def __printRegspace(self, start, stop=None):
        if not stop:
            stop = start + 1
        regMMIO = MMIO(self.base_addr + self.regspace_offset, 16 * 0x4)
        for i in range(start, stop):
            print(f'[{i}] = {regMMIO.read(i*4)}')

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

class ListStub(Stub):
    def __init__(self, context, signature, l, name=None):
        self.l = l
        super().__init__(context, name, signature)

    def __call__(self, i):
        return l[i]

    def __str__(self):
        return str(self.l)
