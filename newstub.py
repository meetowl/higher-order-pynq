import time
import threading
import string
import types
import traceback
import random
import numpy as np
import asyncio

from pynq import MMIO as pynq_MMIO
from pynq import allocate as pynq_allocate

import typesystem.hop_types as ht
start_time = time.time()
# config/debug space
REGSPACE_OFFSET = 0x40
STATUS_OFFSET = 4

class Stub:
    def __init__(self, context, name, signature):
        self.context = context
        self.name = name
        self.signature = signature
        (self.result_offset, self.result_addr) = context.add(name)
        self.result_status_offset = self.result_offset + 1

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

    def __del__(self):
        self.context.remove(self.name)




class HardwareStub(Stub):
    def __init__(self, context, name, meta, debugWrites = False):
        signature = ht.parse(meta['signature'])
        self.module_name = meta['module_name']
        self.base_addr = context.overlay.ip_dict[self.module_name]['phys_addr']
        self.regspace_offset = REGSPACE_OFFSET
        self.hwMemory = pynq_MMIO(self.base_addr, 65536, debug=debugWrites)
        self.debugWrites = debugWrites

        super().__init__(context, name, signature)

        if signature.is_function():
            self.__createFunctionStub(meta)
        self.ret_offset = meta['regspace']['ret_offset']


    def __createFunctionStub(self, meta):
        self.regspace_offset = REGSPACE_OFFSET
        self.arg_offsets = list()
        self.list_dma = dict()
        for i in range(0, self.signature.arity()):
            self.arg_offsets.append(meta['regspace'][f'arg{i + 1}_offset'])
            # If a list, fill the associated DMA
            if (self.signature.getArgumentType(i).is_list()):
                dma = meta['lists'][f'arg{i+1}_dma']
                self.list_dma[i] = eval(f'self.context.overlay.{dma}')

    def __transformToStub(self, args):
        stubArgs = list()
        argsToDelete = list()
        for a in args:
            aStub = a
            if not isinstance(a, Stub):
                aStub = Stub.stubFromVar(self.context, a)
                argsToDelete.append(aStub)
            stubArgs.append(aStub)
        return (stubArgs, argsToDelete)


    def __printWrite(self, address, data, label=None):
        if self.debugWrites:
            if label:
                print(f'[{time.time() - start_time}] {self.name}: \'{label}\' write: ' +
                      f'*({address}) = {data}')
            else:
                print(f'[{time.time() - start_time}] {self.name}: write: ' +
                      f'*({address}) = {data}')

    def __regspaceWrite(self, offset, data, label=None):
        realOffset = offset * 0x4
        self.__printWrite(f'{self.hwMemory.base_addr} + {self.regspace_offset} + {realOffset}', data, label)
        self.hwMemory.write(self.regspace_offset + realOffset, data)

    def writeRegspace(self, offset, data):
        realOffset = offset * 0x4
        self.__printWrite(f'{self.hwMemory.base_addr} + {self.regspace_offset} + {realOffset}', data)
        self.hwMemory.write(self.regspace_offset + realOffset, data)

    def transferList(self, listStub, argNum, buf_size=65536):
        inc_size = len(listStub) // buf_size
        rem_size = len(listStub) % buf_size
        buf = pynq_allocate(shape=(buf_size,), dtype=np.uint32)

        # Fill Remainder Buffer
        if rem_size > 0:
            rem_buf = pynq_allocate(shape=(rem_size))
            listStub.copyTo(rem_buf, inc_size*buf_size, len(listStub) + 1)

        # Toggle CREADY to 1
        self.__regspaceWrite(self.arg_offsets[argNum], 1, label='cready1')

        # Transfer the bulk of the list
        for i in range(0, inc_size):
            listStub.copyTo(buf, i*buf_size, (i+1)*buf_size)
            self.list_dma[argNum].sendchannel.transfer(buf)
            self.list_dma[argNum].sendchannel.wait()


        # Transfer the remainder
        if rem_size > 0:
            self.list_dma[argNum].sendchannel.transfer(rem_buf)
            self.list_dma[argNum].sendchannel.wait()
            del rem_buf

        # Toggle CREADY to 0
        self.__regspaceWrite(self.arg_offsets[argNum], 0, label='cready0')
        del buf
        return

    def __baseArgCall(self, args, streamFutureQueue):
        self.__regspaceWrite(self.ret_offset, 0, label='result_addr0')
        # HARDWARE STATUS: Should be in idle state

        # All of the following code fills out the CEP
        # Specify the CEP address
        self.__regspaceWrite(1, self.base_addr + self.regspace_offset, label='cep_addr')
        # If this is a function, it we need to supply where to fetch arguments from
        if self.signature.is_function():
            ## Supply the argument addresses for all
            for i in range(self.signature.arity()):
                ## Supply argument addresses in CEP
                arg = args[i]
                if not arg.signature.is_list():
                    self.__regspaceWrite(self.arg_offsets[i], arg.result_addr, label='arg_result_addr')
                else:
                    streamFuture = self.context.tpool.submit(self.transferList, arg, i)
                    streamFutureQueue.append(streamFuture)

        ## Specify the return address (this should be the last step for any module)
        self.__regspaceWrite(self.ret_offset, self.result_addr, label='result_addr1')
        # HARDWARE STATUS: Should now be waiting for the first argument if it needs any.
        # It would have written where it expects the first argument to the result address of the argument

        # Evaluate the arguments
        if self.signature.is_function():
            # Argument Loop - Call the arguments and insert their results
            for arg in args:
                if not arg.signature.is_list():
                    # List arguments are already sending through __transferList task
                    ## Leaving this here just in case
                    while self.context.value(arg.result_addr) == 0:
                        print(f'[{time.time() - start_time}] Waiting in evaluation loop.')
                        if self.debugWrites:
                            self.printRegspace(10)
                        time.sleep(1)

                    # Initiate our own MMIO interface that points to this stub's CEP
                    # The result offset is what the hardware has written to be used as the argument
                    # value address. Look in the previous HARDWARE STATUS.
                    regIO = pynq_MMIO(self.context.get(arg.result_offset), 0x8, debug=self.debugWrites)
                    ## Write the arguments
                    a = int(arg())
                    self.__printWrite(regIO.base_addr, a)
                    regIO.write(0x0, a)

                    ## Write the status flag
                    self.__printWrite(f'{regIO.base_addr} + 4', 1)
                    regIO.write(0x4, 1)

                    ## Clears the above values (I've yet to figure this part out)
                    self.context.clear(arg.result_addr + 4)

        # HARDWARE STATUS: Should now be performing function.
        # We have filled in all the arguments in the above loop.

    def __call__(self, *args):
        # Queue of future's from streaming threads
        streamFutureQueue = list()

        if self.signature.is_function():
            (args, argsToDelete) = self.__transformToStub(args)
            if not self.signature.typeCheck(args):
                raise TypeError(f'expected \'{self.signature}\'')
        else:
            if len(args) > 0:
                raise TypeError(f'arguments given to type \'{self.signature}\'')

        # Control Register: AP_START = 1, AUTO_RESTART = 1
        self.__printWrite(self.hwMemory.base_addr, 1 | (1 << 7))
        self.hwMemory.write(0x0, 1 | (1 << 7))

        if self.signature.is_function():
            self.__baseArgCall(args, streamFutureQueue)

        # CEP is now filled, we wait until HW has filled REP
        self.__listen(streamFutureQueue)
        if self.debugWrites:
            print('-----------------------------------')
            self.printRegspace(0,15)
            self.context.print(self.result_offset, self.result_offset+2)
            print(f'res = {self.res}')

        if self.signature.is_function():
            for a in argsToDelete:
                del a

        return self.res

    def __listen(self, streamFutureQueue):
        # Wait for the streaming interfaces to finish streaming
        while len(streamFutureQueue) > 0:
            future = streamFutureQueue.pop()
            fr = future.result()

        while self.context.get(self.result_status_offset) == 0:
            # Massive sleep for debug
            print(f'[{time.time() - start_time}] Waiting in listen loop.')
            if self.debugWrites:
                print(self.context.mem.device_address + self.result_offset)
                self.printRegspace(1, 4)
                self.printRegspace(8)
                self.printRegspace(10)
                time.sleep(1)
            else:
                time.sleep(0.1)

        self.context.clear(self.result_addr + 4)

        self.res = self.context.get(self.result_offset)

    # ---- Debugging -----
    def printRegspace(self, start, end=None):
        if not end:
            end = start
        regMMIO = pynq_MMIO(self.base_addr + self.regspace_offset, 16 * 0x4)
        print(f'{self.name} regspace ({self.hwMemory.base_addr} + '
              f'{self.regspace_offset} = {self.hwMemory.base_addr + self.regspace_offset}):')
        for i in range(start, end+1):
            print(f'[{i}] = {regMMIO.read(i*4)}')

    def printRegStatus(self):
        self.printRegspace(STATUS_OFFSET)

    def printRegspacePretty(self):
        # This is hard-coded so its easier for the programmer (me <3)
        print(f'sig:         {self.hwMemory.read(self.respace_offset)}')
        print(f'status:      {self.hwMemory.read(self.respace_offset + 4 * 0x4)}')
        print(f'call_count:  {self.hwMemory.read(self.respace_offset + 2 * 0x4)}')
        print(f'debug:       {self.hwMemory.read(self.respace_offset + 3 * 0x4)}')
        print(f'rep_addr:    {self.hwMemory.read(self.respace_offset + 10 * 0x4)}')
        print(f'cready:      {self.hwMemory.read(self.respace_offset + 8 * 0x4)}')

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

    def __call__(self):
        return self.var



class ListStub(Stub):
    # I am following this example on how to use stream IPs:
    # https://discuss.pynq.io/t/tutorial-using-a-hls-stream-ip-with-dma-part-3-using-the-hls-ip-from-pynq
    def __init__(self, context, signature, l, name=None):
        # TODO: Should we transfer the entire thing into an np array?
        self.l = l
        self.llen = len(l)
        # This makes this NOT thread safe
        super().__init__(context, name, signature)

    def copyTo(self, buf:'pynq.buffer', start, end):
        # We use unsafe casting because we only care about bit lengths,
        # assume everything is uint32
        np.copyto(buf, self.l[start:end], casting='unsafe')

    def __call__(self, sendChannel, buf_size=65536):
        return l

    def __str__(self):
        return str(self.l)

    def __len__(self):
        return self.llen
