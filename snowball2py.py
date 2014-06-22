#!/usr/bin/env python

'''
A Snowball to Python compiler.
'''

from pyparsing import *


def para_group(x):
	return Group(Suppress('(') + x + Suppress(')'))

# Keywords

keyword = None

def make_keyword(s):
	kw = Keyword(s)
	globals()[s.upper()] = kw
	global keyword
	if keyword is None:
		keyword = kw
	else:
		keyword = keyword | kw

map(make_keyword, """maxint minint cursor limit size sizeof or and strings
integers booleans routines externals groupings define as not test try do fail
goto gopast repeat loop atleast insert attach delete hop next setmark tomark
atmark tolimit atlimit setlimit for backwards reverse substring among set unset
non true false backwardmode stringescapes stringdef hex decimal""".split())

# Variables and literals
name = ~keyword + Word(alphas, alphanums + '_').setName('name')
str_literal = sglQuotedString.setName('string literal')
int_literal = Word(nums).setName('integer literal')
string = (name | str_literal).setName('string')
grouping = (name | str_literal).setName('grouping')

# Declarations
make_decl = lambda kw: Group(kw + para_group(ZeroOrMore(name)))
declaration = (make_decl(STRINGS) | make_decl(INTEGERS) | make_decl(BOOLEANS) |
		make_decl(ROUTINES) | make_decl(EXTERNALS) | make_decl(GROUPINGS))

# Expressions
expr_operand = (MAXINT | MININT | CURSOR | LIMIT | SIZE | Group(SIZEOF + name) |
		name | int_literal).setName('operand')
expr = Forward()
expr << operatorPrecedence(
	expr_operand,
	[
		('-', 1, opAssoc.RIGHT),
		(oneOf('* /'), 2, opAssoc.LEFT),
		(oneOf('+ -'), 2, opAssoc.LEFT)
	]
) | para_group(expr)
expr.setName('expression')

# Integer commands
ic = lambda op: Group(Suppress('$') + name + op + expr)
int_cmd = (ic('=') | ic('+=') | ic('*=') | ic('==') | ic('>') | ic('<') |
		ic('-=') | ic('/=') | ic('!=') | ic('>=') | ic('<='))

# String commands
c = Forward()
str_cmd = Group(Suppress('$') + name + c)
call = lambda cmd: Group(cmd + c)
str_fun = lambda fun: Group(fun + string)
str_cmd_operand = (int_cmd | str_cmd | call(NOT) | call(TEST) | call(TRY) |
		call(DO) | call(FAIL) | call(GOTO) | call(GOPAST) | call(REPEAT) |
		Group(LOOP + expr + c) | Group(ATLEAST + expr + c) | string |
		Group('=' + string) | str_fun(INSERT) | str_fun('<+') | str_fun(ATTACH) |
		str_fun('<-') | DELETE | Group(HOP + expr) | NEXT | Group('=>' + name) |
		'[' | ']' | Group('->' + name) | Group(SETMARK + name) |
		Group(TOMARK + expr) | Group(ATMARK + expr) | TOLIMIT | ATLIMIT |
		Group(SETLIMIT + c + FOR + c) | call(BACKWARDS) | call(REVERSE) | SUBSTRING |
		Group(AMONG + para_group(ZeroOrMore((str_literal + Optional(name)) +
		para_group(c)))) | Group(SET + name) | Group(UNSET + name) | name |
		Group(NON + Optional('-') + name) | TRUE | FALSE | '?')
c << (operatorPrecedence(str_cmd_operand, [(OR | AND, 2, opAssoc.LEFT)]) |
		para_group(ZeroOrMore(c)))

# Routine definition
routine_def = DEFINE + name + AS + c

# Grouping definition
grouping_def = DEFINE + name + delimitedList(name | str_literal,
		delim=oneOf('+ -'))

# String escapes and definitions
str_escapes = Group(STRINGESCAPES + Combine(printables + printables))
str_def = Group(STRINGDEF + Word(printables) + Optional(HEX | DECIMAL) +
		str_literal)

# Program
program = Forward()
program << ZeroOrMore(declaration | routine_def | grouping_def | Group(BACKWARDMODE + para_group(program)) | str_escapes | str_def)
