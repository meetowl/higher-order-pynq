from typedef import tokens
from hop_types import Base

def p_t(p):
    '''t : BASE
         | LPAREN tu RPAREN
         | t ARROW t'''
    p[0] = Base(p[1])

def p_tu(p):
    '''tu : t
          | t COMMA tu'''
    p[0] = tuple([p[1]])

def p_error(p):
    print('uh oh!!!!')
