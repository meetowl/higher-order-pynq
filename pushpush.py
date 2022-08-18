import math
import string
import types
import multiprocessing
import traceback
import time
import random
import json
import os
from pathlib import Path

from pynq import allocate
from pynq import MMIO
from pynq import Overlay

# Local imports
import stubs

class Context:
    """
    Used to keep track of what is where in the end point space
    * the hardware metadata file keeps track of the pushpush objects instantiated in the hardware. This will be replaced by metadata.
    """
    def __init__(self, overlay:Overlay, size=1024) -> None:
        # Get paths and names
        self.overlay_bitfile_name = overlay.bitfile_name
        self.overlay_path = os.path.dirname(self.overlay_bitfile_name)
        self.overlay_name = Path(self.overlay_bitfile_name).stem

        self.overlay_metadata_name = f'{self.overlay_path}/{self.overlay_name}.json'
        stubs_module_name = f'{self.overlay_path}/{self.overlay_name}.py'
        
        self.size = size
        self.mem = allocate(shape=(self.size,), dtype='u4')
        self.top = 0
        self.objects = dict()
        self.global_state = None
        self.load_global_state(self.overlay_metadata_name)
        self.hw = dict()
        self.cpp = dict()
        self.py = dict()
        self.populate_stubs()

    def add_py(self, name, typestr):
        self.py[name] = typestr
        
    def populate_stubs(self)->None:
        # # populate hardware stubs (old way)
        # for h in self.global_state["hardware"]:
        #     if self.global_state["hardware"][h]["type"] == "exp":
        #         base = self.global_state["hardware"][h]["base"]
        #         self.hw[h] = exp_stub(self, base, h)
        #     if self.global_state["hardware"][h]["type"] == "exp->exp->val":
        #         base = self.global_state["hardware"][h]["base"]
        #         self.hw[h] = exp_exp_val_stub(self, base, h)

        # Populate stubs by name
        for h in self.global_state['hardware'].keys():
            base = self.global_state['hardware'][h]['base']
            self.hw[h] = stubs.stub_dict[h](self, base, h)

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

    def register(self, func, typestr, name=None):        
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
            ret_object = stubs.HopFunction(self, func, n_name)
            self.add_py(n_name, "exp")
        # if(typestr == "(exp->exp->val)->(val->com)->com"):
        #     ret_object = lf_exp_exp_val_rf_lf_val_com_rf_com(self,func,n_name)
        #     self.add_py(n_name, "(exp->exp->val)->(val->com)->com")
        # if(typestr == "val->com"):
        #     ret_object = val_com(self,func,n_name)
        #     self.add_py(n_name, "val_com")
        else:
            print("error: Unable to create pushpush object "+n_name)

        return ret_object   

    # ---- Debugging -----
    def print(self,size=16):
        for i in range(0,size):
            print("["+str(i)+"] = "+str(self.mem[i]))
