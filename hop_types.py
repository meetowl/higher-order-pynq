from enum import Enum
import hop_types
import functools

class Base:
    class Attributes(Enum):
        EQ =     0b01
        ORD =    0b10

        def to_num(attr):
            out = 0;
            if type(attr) is list:
                for a in attr:
                    out |= a.value
            else:
                out = attr.value
            return out

        @classmethod
        def from_num(cls, num) -> list:
            out = []
            if num & cls.EQ.value:
                out.append(cls.EQ)
            if num & cls.ORD.value:
                out.append(cls.ORD)
            return out


    def __init__(self, width=32, name='base', attributes=[]):
        self.width = width
        self.name = name
        self.attributes = attributes

    @classmethod
    def for_num(base, num) -> 'Base':
        width = num.bit_length()
        name = 'int'
        attributes = [Base.Attributes.EQ, Base.Attributes.ORD]
        return base(width, name, attributes)

    def __str__(self):
        return f'{self.name}-{self.width}'

class Tuple:
    def __init__(self, *elements):
        # Make sure everything in arguments is an instance of Base
        self.initialised = False

    def from_list(self, l):
        assert not self.initialised

        all_base = functools.reduce(lambda a,b: a & b,
                                    map(lambda a: isinstance(a, hop_types.Base), l))
        if not all_base:
            raise TypeError("Must be HoP type") from Exception

        self.elements = tuple(l)
        self.initialised = True

    def __str__(self):
        out = '('
        for e in self.elements:
            out += f'{str(e)},'
        return out[:-1] + ')'
