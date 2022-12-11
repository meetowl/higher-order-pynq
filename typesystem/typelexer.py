tokens = (
    'BASE',
    'LPAREN',
    'RPAREN',
    'COMMA',
    'LBRACK',
    'RBRACK',
    'ARROW'
)

t_LPAREN = r'\('
t_RPAREN = r'\)'
t_COMMA = r','
t_ARROW = r'->'
t_LBRACK = r'\['
t_RBRACK = r'\]'
t_ignore = ' \t'

def t_BASE(t):
    r'b[0-9]+'
    t.value = int(t.value[1:])
    return t

def t_error(t):
    print("Illegal character '%s'" % t.value[0])
    t.lexer.skip(1)
