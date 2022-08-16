from pynq import allocate
import math
import string
import types
from pynq import MMIO
import multiprocessing
import traceback
import time
import random
import json

class exp:
    def __init__(self, context, exp, name=None) -> None:
        if name is None:
            (filename,line_number,function_name,text)=traceback.extract_stack()[-2]
            self.name = text[:text.find('=')].strip()
        else:
            self.name = name
        self.cep = context.add(self.name,1)
        self.context = context
        self.exp = exp
        multiprocessing.Process(target=self.listen).start()
        
    def name(self) -> str:
        return self.name
    
    def listen(self) -> None:
        while True:
            count = 0
            while self.context.value(self.cep) == 0:
                count = count + 1
            addr = self.context.value(self.cep)
            mmio = MMIO(addr, 65536)
            mmio.write(0, self.exp())
            mmio.write(4, 1)
            self.context.clear(self.cep)
        
    def __call__(self)->int:
        return self.exp()
        
    def cep_addr(self) -> int:
        return self.cep
 
class exp_stub:
    def __init__(self, context, base, name) -> None:
        self.base = base
        self.name = name
        self.cep_off = 8
        # We use this object for writing configuration bits
        self.mmio = MMIO(self.base, 65536)
        self.rep = context.add(name, 2)
        self.res = 0
        self.done = False
        self.context = context

    def cep_addr(self)->int:
        # 0x40 is what we put in our HLS
        return self.base+0x40
        
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

    
def register_pushpush(context, func, typestr, name=None):        
    """
    Registers a PushPush software object and gives it a type.
    """
    if name is None:
        (filename,line_number,function_name,text)=traceback.extract_stack()[-2]
        n_name = text[:text.find('=')].strip()
    else:
        n_name = name
            
    ret_object = None
    # Parse the typestring and build up a pushpush object
    if(typestr == "exp"):
        ret_object = exp(context, func, n_name)
        context.add_py(n_name, "exp")
    # if(typestr == "(exp->exp->val)->(val->com)->com"):
    #     ret_object = lf_exp_exp_val_rf_lf_val_com_rf_com(context,func,n_name)
    #     context.add_py(n_name, "(exp->exp->val)->(val->com)->com")
    # if(typestr == "val->com"):
    #     ret_object = val_com(context,func,n_name)
    #     context.add_py(n_name, "val_com")
    else:
        print("[PushPush] Unable to create pushpush object "+n_name)
        
    return ret_object   
        

class exp_exp_val_stub:
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
        if(isinstance(a, types.FunctionType)):
            anon_a_name = "anon_"+''.join(random.choice(letters) for i in range(10))
            a_mod = exp(self.context, a, anon_a_name)
            self.context.add_py(anon_a_name, "exp")
            
        b_mod = b
        if(isinstance(b, types.FunctionType)):
            anon_b_name = "anon_"+''.join(random.choice(letters) for i in range(10))
            b_mod = exp(self.context, b, anon_b_name)
            self.context.add_py(anon_b_name, "exp")

        self.mmio.write(0x0, 1 | (1 << 7))
        self.mmio.write(0x40 + 1*0x4, self.base + 0x40)
        self.mmio.write(0x40 + 8*0x4, a_mod.cep_addr())
        self.mmio.write(0x40 + 9*0x4, b_mod.cep_addr())
        self.mmio.write(0x40 + 10*0x4, self.rep)
        self.listen()
        return self.res
            
class Context:
    """
    Used to keep track of what is where in the end point space
    * the hardware metadata file keeps track of the pushpush objects instantiated in the hardware. This will be replaced by metadata.
    """
    def __init__(self, hw_metadata_file:str, size=1024) -> None:
        self.size = size
        self.mem = allocate(shape=(self.size,), dtype='u4')
        self.top = 0
        self.objects = dict()
        self.global_state = None
        self.load_global_state(hw_metadata_file)
        self.hw = dict()
        self.cpp = dict()
        self.py = dict()
        self.populate_stubs()

    def add_py(self, name, typestr):
        self.py[name] = typestr
        
    def populate_stubs(self)->None:
        # populate hardware stubs
        for h in self.global_state["hardware"]:
            if self.global_state["hardware"][h]["type"] == "exp":
                base = self.global_state["hardware"][h]["base"]
                self.hw[h] = exp_stub(self, base, h)
            if self.global_state["hardware"][h]["type"] == "exp->exp->val":
                base = self.global_state["hardware"][h]["base"]
                self.hw[h] = exp_exp_val_stub(self, base, h)   

    def print_all_objects(self)->None:
        print("Hardware:")
        for h in self.global_state["hardware"]:
            print("\t"+h + " : "+self.global_state["hardware"][h]["type"])
        
        print("Python:")
        for p in self.py:
            print("\t"+p + " : "+self.py[p])
            
        print("C++:")
        for c in self.global_state["CPP"]:
            print("\t"+c+" : "+self.global_state["CPP"][c]["type"])
        return 

    def load_global_state(self, hardware_metadata_file:str):
        """
        Loads the current global pushpush state
        """
        jsn_f = open(hardware_metadata_file, "r")
        self.global_state = json.load(jsn_f)
        
    def add(self, name, slots) -> None: 
        """
        Adds a named pushpush object to the endpoint space
        using a number of slots. Each slot is 4 bytes.
        """
        if self.top + slots >= self.size:
            raise RuntimeError('PyPushPush Context has run out of endpoint space')
            
        self.objects[name] = self.top
        self.top = self.top + slots
        return self.mem.physical_address + (self.objects[name]*4)
        
    def get_base(self, name) -> int:
        """
        Returns the base address in the context for this 
        PushPush objects endpoint space
        """
        if name not in self.objects:
            print("[Error] could not find the endpoint space for " + name)
        else:
            return self.mem.physical_address + (self.objects[name] * 4)
        
    def get_offset(self, address) -> int:
        return math.ceil((address - self.mem.physical_address)/4)
        
    def clear(self, address) -> None:
        """
        Clears a REP/CEP in the endpoint space
        """
        offset = math.ceil((address - self.mem.physical_address)/4)
        self.mem[offset] = 0
    
    def value(self, address) -> int:
        """
        Return the value for an offset in the endpoint space
        """
        self.mem.invalidate; self.mem.flush;
        offset = math.ceil((address - self.mem.physical_address)/4)
        return self.mem[offset]
    
    # ---- Debugging -----
    def print(self,size=16):
        for i in range(0,size):
            print("["+str(i)+"] = "+str(self.mem[i]))
