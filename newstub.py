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
        self.argspace_addr = context.add(name, 2)

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
            #ps = PythonStub(self.context, sig, var, f'num_{var}')

        return ps

class HardwareStub(Stub):
    def __init__(self, context, name, meta):
        signature = ht.parse(meta['signature'])
        self.base_addr = meta['base']
        self.regspace_offset = REGSPACE_ADDR
        self.regspace_addr = self.base_addr + self.regspace_offset
        self.mmio = MMIO(self.base_addr, 65536)
        super().__init__(context, name, signature)

        if signature.is_function():
            self.__createFunctionStub(meta)

    def __createFunctionStub(self, meta):
        self.regspace_addr = REGSPACE_ADDR

        self.arg_addrs = list()
        for i in range(0, self.signature.arity()):
            self.arg_addrs.append(meta[f'arg{i + 1}_addr'])

        self.ret_addr = meta['ret_addr']

    def __transformToStub(self, args):
        stubArgs = list()
        for a in args:
            aStub = a
            if not isinstance(a, Stub):
                aStub = Stub.stubFromVar(self.context, a)
            stubArgs.append(aStub)
        return stubArgs



    def __call__(self, *args):
        args = self.__transformToStub(args)
        if not self.signature.typeCheck(args):
            raise TypeError(f'expected \'{self.signature}\'')

        # Control Register: AP_START = 1, AUTO_RESTART = 1
        self.mmio.write(0x0, 1 | (1 << 7))

        # Initialise Argument Space::
        ## regspace[1]  = GLOBAL_MEMORY_ADDR + &regspace[0]
        self.mmio.write(self.regspace_offset + 1*0x4, self.base_addr + 0x40)
        # If this is a function, it we need to supply arguments
        if self.signature.is_function():
            ## Insert the argument addresses (where the argument loop will insert them) into regspace
            for i in range(self.signature.arity()):
                ## regspace[n]  = where to take the argument from
                self.mmio.write(self.regspace_offset + self.arg_addrs[i] * 0x4, args[i].argspace_addr)
        ## Provide the return address (if(regspace[return offset] != 0) doesn't run unless this runs)
        ## regspace[n] = return endpoint address
        self.mmio.write(self.regspace_offset + self.ret_addr * 0x4, self.argspace_addr)

        # If a function, populate properly
        if self.signature.is_function():
            # Argument Loop - Call the arguments and insert their results
            for i in range(self.signature.arity()):
                ## Leaving this here just in case
                count = 0
                while self.context.value(args[i].argspace_addr) == 0:
                    # I want to see if this ever trips
                    print(f'[{time.time() - start_time}] BEING HELD IN ARG LOOP')
                    time.sleep(1)
                    count += 1

                ## Initiate our own MMIO interface that points to this argument's argument space
                mmio = MMIO(self.context.value(args[i].argspace_addr), 65536)
                ## Write the result to argument space + 0
                mmio.write(0, evalArgs[i])
                ## Write the result status (not zero = success) to argument space + 1
                mmio.write(4, 1)

                ## Clears the above values
                self.context.clear(args[i].argspace_addr)

        self.listen()
        return self.res

    def listen(self):
        count = 0
        while self.context.value(self.argspace_addr+4) == 0:
            # I want to see if this ever trips
            assert(False)
            print(f'[{time.time() - start_time}] BEING HELD IN LISTEN LOOP WITH VAL: {self.context.value(self.argspace_addr+4)}')
            count = count + 1
        self.context.clear(self.argspace_addr+4)
        self.res = self.context.value(self.argspace_addr)

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
            # The type system would see such a function as just a type.
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
