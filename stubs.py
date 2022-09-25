# Stubs File
# This contains the stubs for each hardware or software function.
# Ideally, a lot of this will be auto-generated. Aim to class the parameters based on whether
# we can generate them or not.
import multiprocessing
import string
import types
import traceback
import random
from pynq import MMIO


# Stubs Base Class
class Stub:
    def __init__(self, context, base_addr, signature, name) -> None:
        self.base = base
        self.name = name
        self.cep = 8
        self.mmio = MMIO(self.base, 65536)
        self.res = 0
        self.done = False
        self.context = context

    def listen(self):
        raise NotImplementedError from Exception

    def __call__(self):
        raise NotImplementedError from Exception

    def cep_addr(self)->int:
        # 0x40 is what we put in our HLS
        return self.base+0x40

# Higher-Order Function Stub
class HopFunction:
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
        self.cep = context.add(self.name,1)
        self.context = context
        multiprocessing.Process(target=self.listen).start()




    def listen(self) -> None:
        while True:
            count = 0
            while self.context.value(self.cep) == 0:
                count = count + 1
            addr = self.context.value(self.cep)
            mmio = MMIO(addr, 65536)
            mmio.write(0, self.function())
            mmio.write(4, 1)
            self.context.clear(self.cep)

    def __call__(self)->int:
        return self.function()

    def cep_addr(self) -> int:
        return self.cep

# Concrete stubs
## add
class AddStub(Stub):
    def __init__(self, context, base, name) -> None:
        super().__init__(context, base, name)
        self.rep = self.context.add(name, 2)


    def listen(self):
        count = 0
        while self.context.value(self.rep+4) == 0:
            count = count + 1
        self.context.clear(self.rep+4)
        self.res = self.context.value(self.rep)

    def __call__(self, a, b) -> int:
        # Check if the args are anonymous functions and wrap them up if so
        a_mod = a
        letters = string.ascii_lowercase
        if isinstance(a, types.FunctionType) :
            anon_a_name = "anon_"+''.join(random.choice(letters) for i in range(10))
            a_mod = HopFunction(self.context, a, anon_a_name)
            self.context.add_py(anon_a_name, "exp")

        b_mod = b
        if isinstance(b, types.FunctionType) :
            anon_b_name = "anon_"+''.join(random.choice(letters) for i in range(10))
            b_mod = HopFunction(self.context, b, anon_b_name)
            self.context.add_py(anon_b_name, "exp")

        # Control Register:
        ## AP_START = 1, AUTO_RESTART = 1
        self.mmio.write(0x0, 1 | (1 << 7))
        # Regspace:
        ## regspace[1]  = GLOBAL_MEMORY_ADDR + &regspace[0]
        self.mmio.write(0x40 + 1*0x4, self.base + 0x40)
        ## regspace[8]  = caller endpoint address of first argument
        self.mmio.write(0x40 + 8*0x4, a_mod.cep_addr())
        ## regspace[9]  = caller endpoint address of second argument
        self.mmio.write(0x40 + 9*0x4, b_mod.cep_addr())
        ## regspace[10] = return endpoint address
        self.mmio.write(0x40 + 10*0x4, self.rep)
        self.listen()
        return self.res

## example_a
class AStub(Stub):
    def __init__(self, context, base, name) -> None:
        super().__init__(context, base, name)
        self.rep = self.context.add(name, 2)

    def listen(self):
        count = 0
        # REP Base adress + 4 is our status register
        while self.context.value(self.rep+4) == 0:
            count = count + 1
        # Clear the status register
        self.context.clear(self.rep+4)
        self.res = self.context.value(self.rep)

    def __call__(self) -> int:
        # Control Register:
        ## AP_START = 1, AUTO_RESTART = 1
        self.mmio.write(0x0, 1 | (1 << 7))
        # Regspace:
        ## regspace[1]  = GLOBAL_MEMORY_ADDR + &regspace[0]
        self.mmio.write(0x40 + 1*0x4, self.base + 0x40)
        ## regspace[10] = return endpoint address (0)
        self.mmio.write(0x40 + 10*0x4, self.rep)
        self.listen()
        return self.res

## cmp
class CmpStub:
    def __init__(self, context, base, name) -> None:
        self.base = base
        self.name = name
        self.cep = 8
        self.mmio = MMIO(self.base, 65536)
        self.rep = context.add(name, 2)
        self.res = 0
        self.done = False
        self.context = context

    def listen(self):
        count = 0
        while self.context.value(self.rep+4) == 0:
            count = count + 1
        self.context.clear(self.rep+4)
        self.res = self.context.value(self.rep)

    def __call__(self, a, b) -> int:
        # Check if the args are anonymous functions and wrap them up if so
        a_mod = a
        letters = string.ascii_lowercase
        if isinstance(a, types.FunctionType) :
            anon_a_name = "anon_"+''.join(random.choice(letters) for i in range(10))
            a_mod = HopFunction(self.context, a, anon_a_name)
            self.context.add_py(anon_a_name, "exp")

        b_mod = b
        if isinstance(b, types.FunctionType) :
            anon_b_name = "anon_"+''.join(random.choice(letters) for i in range(10))
            b_mod = HopFunction(self.context, b, anon_b_name)
            self.context.add_py(anon_b_name, "exp")

        self.mmio.write(0x0, 1 | (1 << 7))
        self.mmio.write(0x40 + 1*0x4, self.base + 0x40)
        self.mmio.write(0x40 + 8*0x4, a_mod.cep_addr())
        self.mmio.write(0x40 + 9*0x4, b_mod.cep_addr())
        self.mmio.write(0x40 + 10*0x4, self.rep)
        self.listen()
        return self.res


stub_dict = {
        "add": AddStub,
        "a": AStub,
        "cmp": CmpStub
}
