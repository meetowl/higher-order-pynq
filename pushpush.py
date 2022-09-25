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
import typesystem.hop_types as ht

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

        self.functions = dict()
        self.functions['hardware'] = dict
        self.functions['python'] = dict
        self.functions['cpp'] = dict

        self.populate_stubs(self.overlay_metadata_name)

    def add_py(self, hopFunc):
        self.py[hopFunc.name] = hopFunc

    def populate_stubs(self, overlay_metadata_file)->None:
        # Load the metadata
        overlay_metadata = None
        with open(overlay_metadata_file, "r") as f:
            overlay_metadata = json.load(f)

        # Construct the current context stubs
        for h in self.global_state['hardware'].keys():
            base = self.global_state['hardware'][h]['base']
            self.hw[h] = stubs.stub_dict[h](self, base, h)

        for funcType in overlay_metadata.keys():
            if funcType in self.functions.keys():
                for funcName in overlay_metadata[funcType].keys():
                    funcMeta = self.overlay_metadata[funcType][funcName]
                    self.functions[funcType][funcName] = Stub.from_meta_dict(funcType, funcName, funcMeta)

    def print_all_objects(self)->None:
        print("Hardware:")
        for h in self.global_state["hardware"]:
            print("\t"+h + " : "+self.global_state["hardware"][h]["type"])

        print("Python:")
        for p in self.py:
            print("\t"+p + " : "+str(self.py[p].signature))

        print("C++:")
        for c in self.global_state["CPP"]:
            print("\t"+c+" : "+self.global_state["CPP"][c]["type"])
        return




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

        signature = ht.parse(typestr)
        hopFunc = stubs.HopFunction(self, signature, func, n_name)
        self.add_py(hopFunc)
        return hopFunc

    # ---- Debugging -----
    def print(self,size=16):
        for i in range(0,size):
            print("["+str(i)+"] = "+str(self.mem[i]))
