
import multiprocessing
import string
import types
import traceback
import random
from pynq import MMIO
import typesystem.hop_types as ht

# config/debug space
REGSPACE_ADDR = 0x40

class Stub:
    def __init__(self, context, name, signature, cep_offset):
        self.context = context
        self.name = name
        self.signature = signature
        self.regspace_addr = REGSPACE_ADDR
        self.cep_offset = cep_offset
        # TODO: Understand & replace this line
        self.rep_addr = context.add(name, 2)

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
        cep_offset = meta['cep_offset']
        self.mmio = MMIO(self.base_addr, 65536)
        super().__init__(context, name, signature, cep_offset)

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

    def __call__(self, *args):
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
            if argTuple.elements[i].is_function():
                evalArgs.append(args[i]())
            else:
                evalArgs.append(args[i])

        # Control Register: AP_START = 1, AUTO_RESTART = 1
        self.mmio.write(0x0, 1 | (1 << 7))

        # Initialise Argument Space::
        ## regspace[1]  = GLOBAL_MEMORY_ADDR + &regspace[0]
        self.mmio.write(self.regspace_addr + 1*0x4, self.base_addr + 0x40)
        ## Insert the argument addresses (where the argument loop will insert them) into regspace
        for i in range(self.signature.typein.arity):
            ## regspace[n]  = caller endpoint address of argument
            self.mmio.write(0x40 + self.arg_addrs[i] * 0x4, args[i].cep_offset)
        ## Provide the return address (if(regspace[REP_addr] != 0) doesn't run unless this runs)
        ## regspace[n] = return endpoint address
        self.mmio.write(0x40 + self.ret_addr * 0x4, self.rep_addr)

        # Argument Loop - Call the arguments and insert their results
        for i in range(self.signature.typein.arity):
            ## Leaving this here just in case
            # count = 0
            # while self.context.value(args[i].cep_offset) == 0:
            #     count += 1
            #     time.sleep(1)

            ## Initiate our own MMIO interface that points to this argument's argument space
            mmio = MMIO(self.context.value(args[i].cep_offset), 65536)
            ## Write the result to argument space + 0
            mmio.write(0, evalArgs[i])
            ## Write the result status (not zero = success) to argument space + 1
            mmio.write(4, 1)

            # ## Clears the above values
            # self.context.clear(args[i].cep_offset)


        self.listen()
        return self.res

    def listen(self):
        count = 0
        while self.context.value(self.rep_addr+4) == 0:
            print(f'[{time.time() - start_time}] hw loop: while self.context.value({self.rep_addr} + 4) = {self.context.value(self.rep_addr + 4)}')
            count = count + 1
            time.sleep(1)
        self.context.clear(self.rep_addr+4)
        self.res = self.context.value(self.rep_addr)


class PythonStub(Stub):
    def __init__(self, context, signature, func, name) -> None:
        # Function definition
        self.context = context
        self.signature = signature
        self.function = func
        self.name = name
        super().__init__(context, name, signature, context.add(self.name,1))

    def __call__(self)->int:
        return self.function()

    def cep_offset(self) -> int:
        return self.cep_offset
