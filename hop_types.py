from enum import Enum
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
