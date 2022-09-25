import typesystem.hop_types as ht
from typesystem.typelexer import tokens

# Type Parser
# BNF (V4):
#   t  ::= ( )
#        | Base n
#        | ( tu )
#        | t -> t

#   tu ::= t
#        | t, tu

def p_t_1(p):
    't : LPAREN RPAREN'
    p[0] = ht.Tuple([])

def p_t_2(p):
    't : BASE'
    p[0] = ht.Base(p[1])

def p_t_3(p):
    't : LPAREN tu RPAREN'
    p[2].reverse()
    p[0] = ht.Tuple(p[2])

def p_t_4(p):
    't : t ARROW t'
    p[0] = ht.Function(p[1], p[3])

def p_tu_1(p):
    'tu : t'
    p[0] = [p[1]]

def p_tu_2(p):
    'tu : t COMMA tu'
    p[3].append(p[1])
    p[0] = p[3]

def p_error(p):
    print('error: cannot parse type string')
