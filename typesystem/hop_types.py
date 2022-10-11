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

class Tuple(Type):
    def __init__(self, elementList):
        self.elements = elementList
        self.arity = len(elementList)
        self.empty = self.arity == 0

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

class Function(Type):
    def __init__(self, typein, typeout):
        self.typein = typein
        self.typeout = typeout

    def __str__(self):
        return f'{str(self.typein)} -> {str(self.typeout)}'

    def is_function(self):
        return True


def parse(typestr):
    lexer = lex.lex(module = typelexer, debug = False)
    parser = yacc.yacc(module = typeparser, debug = False)
    return parser.parse(typestr)
