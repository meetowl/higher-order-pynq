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
import newstub as stubs
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
        self.functions['hardware'] = dict()
        self.functions['python'] = dict()
        self.functions['cpp'] = dict()

        self.populate_stubs(self.overlay_metadata_name)


    def watch(self):
        '''Function to watch the allocated range for a certain range'''
        n = 6
        w = [i for i in range(0, n)]
        old = [-1 for i in range(n)]
        while True:
            for i in range(len(w)):
                cap = self.mem[i]
                if cap != old[i]:
                    old[i] = cap
                    print(f'mem[{i}]: {cap}')

    def add_py(self, hopFunc):
        self.functions['python'][hopFunc.name] = hopFunc

    def populate_stubs(self, overlay_metadata_file)->None:
        # Load the metadata
        overlay_metadata = None
        with open(overlay_metadata_file, "r") as f:
            overlay_metadata = json.load(f)

        for funcType in overlay_metadata.keys():
            if funcType in self.functions.keys():
                for funcName in overlay_metadata[funcType].keys():
                    funcMeta = overlay_metadata[funcType][funcName]
                    self.functions[funcType][funcName] = stubs.Stub.from_meta_dict(self,
                                                                                   funcType,
                                                                                   funcName,
                                                                                   funcMeta)


    def print_all_objects(self)->None:
        for objType in self.functions.keys():
            print(f'{objType}:')
            for objName in self.functions[objType].keys():
                print(f'\t{objName} : {str(self.functions[objType][objName].signature)}')
        return

    def add(self, name, slots):
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
        self.mem.invalidate
        self.mem.flush
        offset = math.ceil((address - self.mem.physical_address)/4)
        return self.mem[offset]

    def register(self, pyobj, typestr, name=None):
        """
        Registers a PushPush software object and gives it a type.
        """
        if name is None:
            (filename,line_number,function_name,text)=traceback.extract_stack()[-2]
            n_name = text[:text.find('=')].strip()
        else:
            n_name = name

        signature = ht.parse(typestr)
        stub = stubs.Stub.stubFromVar(self, pyobj, sig=signature, name=n_name)
        self.add_py(stub)
        return stub

    # ---- Debugging -----
    def print(self,size=16):
        for i in range(0,size):
            print("["+str(i)+"] = "+str(self.mem[i]))

    def reloadModules():
        import importlib as il
        il.reload(stubs)
        il.reload(ht)
