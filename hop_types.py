from enum import Enum
import hop_types
import functools

class Base:
    def __init__(self, width=32):
        self.width = width

    @classmethod
    def for_num(base, num) -> 'Base':
        width = num.bit_length()
        return base(width)

    def __str__(self):
        return f'b{self.width}'

class Tuple:
    def __init__(self, elementList):
        # Make sure everything in arguments is an instance of Base
        # all_base = functools.reduce(lambda a,b: a & b,
        #                             map(lambda a:
        #                                 isinstance(a, hop_types.Base) or
        #                                 isinstance(a, hop_types.Tuple),
        #                                 elements))
        # if not all_base:
        #     raise TypeError("Must be HoP type") from Exception

        print(f'hello {elementList}')
        self.elements = elementList

    def __str__(self):
        out = '('
        for e in self.elements:
            out += f'{str(e)},'
        return out[:-1] + ')'

#class Signature:
#    def __init__(self, typestr):
