import typesystem.typelexer as typelexer
import typesystem.typeparser as typeparser
import ply.lex as lex
import ply.yacc as yacc

class Type:
    def is_function(self):
        return False
    def is_tuple(self):
        return False
    def is_base(self):
        return False
    def is_list(self):
        return False
    def __ne__(self, other):
        return not (self == other)
    def __eq__(self, other):
        return NotImplemented

    # Currently only allow to typecheck tuples
    # Please re-implement this after you read some theory
    def typeMatch(self, sigGiven):
        if self.is_tuple():
            if not sigGiven.is_tuple():
                return False
        else:
            return False

        for i in range(self.arity):
            # Only checks one eval level down
            if self.elements[i].is_base() and sigGiven.elements[i].is_function():
                if self.elements[i] != sigGiven.elements[i].typeout:
                    return False
            elif self.elements[i] != sigGiven.elements[i]:
                return False
        return True

class Base(Type):
    def __init__(self, width=32):
        self.width = width

    @classmethod
    def for_num(base, num) -> 'Base':
        width = num.bit_length()
        return base(width)

    def __str__(self):
        return f'b{self.width}'

    def is_base(self):
        return True

    def __eq__(self, other):
        return other.is_base() and self.width == other.width

class Tuple(Type):
    def __init__(self, elementList):
        self.elements = elementList
        self.arity = len(elementList)
        self.empty = self.arity == 0

    @classmethod
    def from_objects(cls, objectList):
        '''Get the tuple type from some objects
           Assumes those objects are children of the HoP typesystem.'''
        elementList = list()
        for o in objectList:
            elementList.append(o.signature)

        return cls(elementList)


    def __str__(self):
        if self.empty:
            out = '()'
        else:
            out = '('
            for e in self.elements:
                out += f'{str(e)},'
            out = out[:-1] + ')'
        return out

    def is_tuple(self):
        return True

    def __eq__(self, other):
        if not other.is_tuple():
            return False

        for i in range(self.arity):
            if self.elements[i] != other.elements[i]:
                return False
        return True



class Function(Type):
    def __init__(self, typein, typeout):
        self.typein = typein
        self.typeout = typeout

    def __str__(self):
        return f'{str(self.typein)} -> {str(self.typeout)}'

    def is_function(self):
        return True

    def __eq__(self, other):
        return other.is_function() and self.typein != other.typein and self.typeout != other.typeout

class List(Type):
    def __init__(self, listType):
        self.listType = listType
    def __str__(self):
        return f'[{str(self.listType)}]'
    def is_list(self):
        return True
    def __eq__(self, other):
        return other.is_list() and self.listType == other.listType

def parse(typestr):
    lexer = lex.lex(module = typelexer, debug = False)
    parser = yacc.yacc(module = typeparser, debug = False)
    return parser.parse(typestr)
