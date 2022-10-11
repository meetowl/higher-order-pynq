
import multiprocessing
import string
import types
import traceback
import random
from pynq import MMIO
import typesystem.hop_types as ht

REGSPACE_ADDR = 0x40

class Stub:
    def __init__(self, context, name, signature, base_addr, cep_offset):
        self.context = context
        self.name = name
        self.signature = signature
        self.base_addr = base_addr
        self.regspace_addr = REGSPACE_ADDR
        self.cep_offset = cep_offset
        # TODO: Understand & replace this line
        self.rep_addr = context.add(name, 2)

#    @classmethod
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
        base_addr = meta['base']
        cep_offset = meta['cep_offset']
        self.mmio = MMIO(base_addr, 65536)
        super().__init__(context, name, signature, base_addr, cep_offset)

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

    def __call__(self, a, b):
        # Assign anonymous prefix to functions if no name given
        a_mod = a
        letters = string.ascii_lowercase
        if isinstance(a, types.FunctionType) :
            anon_a_name = "anon_"+''.join(random.choice(letters) for i in range(10))
            a_mod = PythonStub(self.context, a, anon_a_name)
            self.context.add_py(anon_a_name, self.signature)

        b_mod = b
        if isinstance(b, types.FunctionType) :
            anon_b_name = "anon_"+''.join(random.choice(letters) for i in range(10))
            b_mod = PythonStub(self.context, b, anon_b_name)
            self.context.add_py(anon_b_name, self.signature)

        # Control Register:
        ## AP_START = 1, AUTO_RESTART = 1
        self.mmio.write(0x0, 1 | (1 << 7))
        # Regspace:
        ## regspace[1]  = GLOBAL_MEMORY_ADDR + &regspace[0]
        self.mmio.write(self.regspace_addr + 1*0x4, self.base_addr + 0x40)


        # TODO: Ideally automate argument generation
        ## regspace[8]  = caller endpoint address of first argument
        self.mmio.write(0x40 + self.arg_addrs[0] * 0x4, a.cep_offset)
        ## regspace[9]  = caller endpoint address of second argument
        self.mmio.write(0x40 + self.arg_addrs[1] * 0x4, b.cep_offset)

        ## regspace[10] = return endpoint address
        self.mmio.write(0x40 + self.ret_addr * 0x4, self.rep_addr)
        self.listen()
        return self.res

    def listen(self):
        count = 0
        while self.context.value(self.rep_addr+4) == 0:
            count = count + 1
        self.context.clear(self.rep_addr+4)
        self.res = self.context.value(self.rep_addr)

# TODO: Replace with a child of stub
class PythonStub:
    def __init__(self, context, signature, func, name=None) -> None:
        # Function definition
        self.signature = signature
        self.function = func
        if name is None:
            (filename,line_number,function_name,text)=traceback.extract_stack()[-2]
            self.name = text[:text.find('=')].strip()
        else:
            self.name = name

        # Plumbing
        self.cep_offset = context.add(self.name,1)
        self.context = context
        multiprocessing.Process(target=self.listen).start()

    def listen(self) -> None:
        while True:
            count = 0
            while self.context.value(self.cep_offset) == 0:
                count = count + 1
            addr = self.context.value(self.cep_offset)
            mmio = MMIO(addr, 65536)
            mmio.write(0, self.function())
            mmio.write(4, 1)
            self.context.clear(self.cep_offset)

    def __call__(self)->int:
        return self.function()

    def cep_offset(self) -> int:
        return self.cep_offset
