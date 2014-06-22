#!/usr/bin/env python

"""
A Snowball to Python compiler.
"""

import re

from pyparsing import *


def para_group(x):
	return Group(Suppress('(') + x + Suppress(')'))

# Keywords

keywords = []

def make_keyword(s):
	kw = Keyword(s)
	globals()[s.upper()] = kw
	keywords.append(kw)

map(make_keyword, """maxint minint cursor limit size sizeof or and strings
integers booleans routines externals groupings define as not test try do fail
goto gopast repeat loop atleast insert attach delete hop next setmark tomark
atmark tolimit atlimit setlimit for backwards reverse substring among set unset
non true false backwardmode stringescapes stringdef hex decimal""".split())

keyword = MatchFirst(keywords)

# String escapes
str_escape_chars = []
str_defs = {}

def str_escapes_action(tokens):
	str_escape_chars[:] = tokens[0]
	str_defs["'"] = "'"
	str_defs['['] = '['
	print "String escapes are now", str_escape_chars
	del tokens[:]

str_escapes = Suppress(STRINGESCAPES) + Word(printables, exact=2)
str_escapes.setParseAction(str_escapes_action)

class SnowballStringLiteral(Token):
	"""
	String literal that supports dynamically changing escape characters.
	"""

	def __init__(self, escape_chars, replacements):
		"""
		Constructor.

		``escape_chars`` is a list containing either two or no characters. These
		characters are the left and right escape marker, respectively. You may
		change the content of the list afterwards, the parsing code always uses
		the latest values.

		``replacements`` is a dict that maps escape sequences to their replacements.
		"""
		super(SnowballStringLiteral, self).__init__()
		self.escape_chars = escape_chars
		self.replacements = replacements

	def __str__(self):
		if self.escape_chars:
			return 'SnowballStringLiteral("%s%s")' % self.escape_chars
		else:
			return 'SnowballStringLiteral("")'

	def parseImpl(self, instring, loc, doActions=True):
		if instring[loc] != "'":
			raise ParseException('Expected "\'".')
		# Find next "'" that is not contained in escape chars
		pos = loc + 1
		while True:
			try:
				candidate = instring.index("'", pos)
			except ValueError:
				raise ParseException('Runaway string literal.')
			if not self.escape_chars:
				break
			left = instring.rfind(self.escape_chars[0], loc, candidate)
			right = instring.rfind(self.escape_chars[1], loc, candidate)
			if right >= left:
				break
			pos = candidate + 1
		s = instring[loc + 1 : candidate]
		if self.escape_chars:
			# Replace escape sequences
			left = re.escape(self.escape_chars[0])
			right = re.escape(self.escape_chars[1])
			for k, v in self.replacements.iteritems():
				s = re.sub(left + re.escape(k) + right, v, s)
		return candidate + 1, s


# Variables and literals
name = ~keyword + Word(alphas, alphanums + '_').setName('name')
str_literal = SnowballStringLiteral(str_escape_chars, str_defs)
int_literal = Word(nums).setName('integer literal')
string = (name | str_literal).setName('string')
grouping = (name | str_literal).setName('grouping')


# String definitions

def str_def_action(tokens):
	key = tokens[0]
	mode = tokens[1]
	value = tokens[2]
	if mode == 'hex':
		value = ''.join(chr(int(x, 16)) for x in value.split())
	elif mode == 'decimal':
		value = ''.join(chr(int(x)) for x in value.split())
	str_defs[key] = value
	del tokens[:]

str_def = Suppress(STRINGDEF) + Word(printables) + Optional(HEX | DECIMAL,
		default=None) + str_literal
str_def.setParseAction(str_def_action)


# Declarations
strings = []
integers = []
externals = []
booleans = []
routines = []
groupings = []

def make_declaration(kw, target):
	decl = (Suppress(kw) + Suppress('(') + ZeroOrMore(name) + Suppress(')'))

	def action(tokens):
		target.extend(tokens)
		del tokens[:]

	decl.setParseAction(action)
	return decl
		
declaration = MatchFirst([make_declaration(kw, target) for kw, target in [
	(STRINGS, strings), (INTEGERS, integers), (BOOLEANS, booleans),
	(ROUTINES, routines), (EXTERNALS, externals), (GROUPINGS, groupings)
]])

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

# Program
program = Forward()
program << ZeroOrMore(declaration | routine_def | grouping_def |
		Group(BACKWARDMODE + para_group(program)) | str_escapes | str_def)
