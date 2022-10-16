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

class HardwareStub(Stub):
    def __init__(self, context, name, meta):
        signature = ht.parse(meta['signature'])
        self.base_addr = meta['base']
        self.regspace_offset = REGSPACE_ADDR
        self.regspace_addr = self.base_addr + self.regspace_offset
        self.mmio = MMIO(self.base_addr, 65536)
        super().__init__(context, name, signature)

        if signature.is_function():
            self._createFunctionStub(meta)

    def _createFunctionStub(self, meta):
        self.regspace_addr = REGSPACE_ADDR
        if self.signature.typein.is_tuple():
            self.arity = self.signature.typein.arity
        else:
            self.arity = 1

        self.arg_addrs = list()
        for i in range(0, self.arity):
            self.arg_addrs.append(meta[f'arg{i + 1}_addr'])

        self.ret_addr = meta['ret_addr']

    def __transformToStub(self, args):
        stubArgs = list()
        for a in args:
            aStub = a
            if not isinstance(a, Stub):
                aStub = stubsFromVar(self.context, a)
            stubArgs.append(aStub)
        return stubArgs

    def __call__(self, *args):
        args = self.__transformToStub(args)
        # Argument checking
        if len(args) != self.arity:
            raise RuntimeError(f'error: {self.name} expects {self.arity} arguments but {len(args)} given.')

        # Type checking (very naive)
        # TODO: rewrite after reading type theory
        argTuple = ht.Tuple.from_objects(args)
        if not self.signature.typein.typeMatch(argTuple):
            raise RuntimeError(f'error: expected type {self.signature.typein} does not match given {argTuple}')

        # Evaluate arguments (very naive)
        # TODO: Read about how Haskell evaluates
        evalArgs = list()
        for i in range(self.signature.typein.arity):
            # We cast to int because things tend to return things like 'numpy.uint32'
            evalArgs.append(int(args[i]()))


        # Control Register: AP_START = 1, AUTO_RESTART = 1
        self.mmio.write(0x0, 1 | (1 << 7))

        # Initialise Argument Space::
        ## regspace[1]  = GLOBAL_MEMORY_ADDR + &regspace[0]
        self.mmio.write(self.regspace_offset + 1*0x4, self.base_addr + 0x40)
        ## Insert the argument addresses (where the argument loop will insert them) into regspace
        for i in range(self.signature.typein.arity):
            ## regspace[n]  = where to take the argument from
            self.mmio.write(self.regspace_offset + self.arg_addrs[i] * 0x4, args[i].argspace_addr)
        ## Provide the return address (if(regspace[return offset] != 0) doesn't run unless this runs)
        ## regspace[n] = return endpoint address
        self.mmio.write(self.regspace_offset + self.ret_addr * 0x4, self.argspace_addr)

        # Argument Loop - Call the arguments and insert their results
        for i in range(self.signature.typein.arity):
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
            print(f'[{time.time() - start_time}] BEING HELD IN LISTEN LOOP WITH VAL: {self.context.value(self.argspace_addr+4)}')
            count = count + 1
        self.context.clear(self.argspace_addr+4)
        self.res = self.context.value(self.argspace_addr)


class PythonStub(Stub):
    def __init__(self, context, signature, obj, name) -> None:
        # Function definition
        self.context = context
        self.signature = signature

        self.name = name
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

def stubsFromVar(context, var):
    t = type(var)
    # Basic variable case
    if t == int:
        sig = ht.Base(var.bit_length())
        ps = PythonStub(context, sig, var, f'num_{var}')
        return ps

    # Numpy Case
    if t.__module__ == numpy.__name__ and numpy.isscalar(var):
        sig = ht.Base(numpy.intc(var).itemsize * 8)
        ps = PythonStub(context, sig, var, f'num_{var}')
        return ps

    raise NotImplementedError(f'type {t} not yet implemented')
