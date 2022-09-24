from typedef import tokens
from hop_types import Base,Tuple,Function

def p_t_1(p):
    't : BASE'
    p[0] = Base(p[1])

def p_t_2(p):
    't : LPAREN tu RPAREN'
    p[2].reverse()
    p[0] = Tuple(p[2])

def p_t_3(p):
    't : t ARROW t'
    p[0] = Function(p[1], p[3])

def p_tu(p):
    'tu : t'
    p[0] = [p[1]]

def p_tu_2(p):
    'tu : t COMMA tu'
    p[3].append(p[1])
    p[0] = p[3]

def p_error(p):
    print('error: cannot parse type string')
