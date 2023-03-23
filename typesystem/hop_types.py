import typesystem.typelexer as typelexer
import typesystem.typeparser as typeparser
import ply.lex as lex
import ply.yacc as yacc
import numpy as np

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



    def typeMatch(var):
        'Convert variable to the correspoinding HoP Type'
        # Existing type case
        if (isinstance(var, Type)):
            return var

        # Numpy case
        if type(var).__module__ == np.__name__:
            if np.isscalar(var):
                return Base(var.itemsize * 8)

        # Tuple case
        if isinstance(var, tuple):
            tupList = []
            for e in var:
                tupList.append(Type.typeMatch(e))
            return Tuple(tupList)

        # List case
        if isinstance(var, list):
            listType = Type.typeMatch(var[0])
            if listType.is_base():
                # Assume that if it is a numpy type it was made from an
                # ndarray, which is type homogenous. This may cause bugs
                # if ppl are doing funky things.
                if np.issubdtype(type(var[0]), np.integer):
                    return List(listType)

                # If it is a base type, find the minimum base width we need
                # This is prone to errors (hi future debugging me, ilu :))
                maxWidth = listType.width
                for e in var:
                    w = e.bit_length()
                    if w > maxWidth:
                        maxWidth = w
                return List(Base.for_num(maxWidth))
            else:
                raise NotImplementedError(f'Only list of first-order types are currently supported, '
                                          + f'not {listType}!')
        # Int case
        if isinstance(var, int):
            return Base.for_num(var)

        raise NotImplementedError(f'Type of \'{var}\' not yet implemented in HoP.')


class Base(Type):
    # Match with numpy widths
    widths = [8, 16, 32, 64]
    npType = {8: np.int8,
              16: np.int16,
              32: np.int32,
              64: np.int64}
    def __init__(self, width=32):
        self.width = width

    def align_width(width):
        for w in Base.widths:
            if width <= w:
                return w
        raise TypeError(f'Type of width {width} is bigger than ' +
                        f'max supported width ({Base.widths[-1]})!')

    @classmethod
    def for_num(base, num) -> 'Base':
        return base(Base.align_width(num.bit_length()))

    def __str__(self):
        return f'b{self.width}'

    def __eq__(self, other):
        return other.is_base() and self.width >= other.width

    def is_base(self):
        return True

    def getNumpyType(self):
        return npType[self.width]


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

    # See how many arguments are in function chain
    def arity(self):
        if not self.typeout.is_function():
            return 1
        else:
            return 1 + self.typeout.arity()

    def getArgumentType(self, n:int) -> 'Type':
        if n == 0:
            return self.typein
        if n >= self.arity() or n < 0:
            return None
        if self.typeout.is_function():
            return self.typeout.getArgumentType(n - 1)
        else:
            return None


    def typeCheck(self, argStubs) -> bool:
        checkStack = list(map(lambda stub: stub.signature, argStubs))
        currTerm = self.typein
        nextTerm = self.typeout
        termNum = 0
        while checkStack:
            a = checkStack.pop()
            termNum += 1
            if not currTerm == a:
                # Type doesn't match
                print(f'warn: arg {termNum} {a} mismatch with {currTerm}')
                return False
            if checkStack and not nextTerm.is_function():
                # Argument count mismatch
                return False

            if checkStack:
                currTerm = nextTerm.typein
                nextTerm = nextTerm.typeout

        if not nextTerm.is_function():
            # We've checked all arguments
            return True
        else:
            # Not enough arguments supplied
            return False

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
