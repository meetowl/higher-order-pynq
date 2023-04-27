![HoP Logo](./hop.png)
# HoP: Higher-order PYNQ
## Abstract
Field-Programmable Gate Arrays (FPGAs) are hardware devices which consist of thousands of logic blocks, that can be reconfigured to create digital circuits on-the-fly.
The advantage of using FPGAs is their flexibility for acceleration purposes.
A programmer can identify sections of their applications that would benefit from speedups, generate the hardware image which accelerates the given functionality, and offload it onto the FPGA to be used within the application.
The development process for generating FPGA images is notoriously difficult, as it requires a sizeable toolchain and expertise.
PYNQ is a framework which provides Python interfaces to existing FPGA images, which allows a software programmer to use hardware from a familiar environment.
While it achieves its goal, PYNQ lacks many of the abstractions and constructs of modern Python.
This work aims at extending PYNQ with (a) aspects of higher order functionality for hardware functions, (b) a heterogenous type system for software and hardware and (c) seemless list processing acceleration.
The project serves as an exploration into introducing more abstract concepts into hardware, and aims to introduce a framework that can allow drop-in acceleration of existing functions with the use of an FPGA.
This work creates a Python library, Higher-order PYNQ (HoP), which utilises the PushPush protocol to achieve higher-order execution principles, such as transparently using a mix of hardware and software functionality.
HoP has a Haskell-inspired typesystem to avoid run-time errors, which are much more difficult to debug with hardware.
The initial implementation of HoP does not get any speedups compared to using existing functions, specifying where performance is lost and specifies a forward path towards acceleration.
HoP creates a proof of work into higher-order programming of PYNQ and FPGAs as a whole, promoting the increasing usage of modern programming constructs in hardware.
