#!/usr/bin/env python

"""
A Snowball to Python compiler.
"""

import re
import sys

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

TRUE.setParseAction(replaceWith('True'))
FALSE.setParseAction(replaceWith('False'))

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
		return candidate + 1, repr(s)


# Variables and literals
def make_name(title):
	return ~keyword + Word(alphas, alphanums + '_').setName(title + ' name')

def ref_action(var):
	return lambda t: "self.%s['%s']" % (var, t[0])

name_action = lambda t: repr(t[0])

str_name = make_name('string').setParseAction(name_action)
grouping_name = make_name('grouping').setParseAction(name_action)
int_name = make_name('integer').setParseAction(name_action)
boolean_name = make_name('boolean').setParseAction(name_action)
routine_name = make_name('routine').setParseAction(name_action)

str_ref = make_name('string').setParseAction(ref_action('strings'))
grouping_ref = make_name('grouping').setParseAction(ref_action('groupings'))
int_ref = make_name('integer').setParseAction(ref_action('integers'))
boolean_ref = make_name('boolean').setParseAction(ref_action('booleans'))
routine_ref = make_name('routine').setParseAction(lambda t: "self.%s" % t[0])

str_literal = SnowballStringLiteral(str_escape_chars, str_defs)
int_literal = Word(nums).setName('integer literal')
string = str_name | str_literal
grouping = grouping_name | str_literal


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

def make_declaration(kw, name, target):
	decl = (Suppress(kw) + Suppress('(') + ZeroOrMore(name) + Suppress(')'))

	def action(tokens):
		target.extend(tokens)
		del tokens[:]

	decl.setParseAction(action)
	return decl
		
declaration = MatchFirst([make_declaration(kw, name, target) for kw, name,
		target in [
	(STRINGS, str_name, strings), (INTEGERS, int_name, integers),
	(BOOLEANS, boolean_name, booleans), (ROUTINES, routine_name, routines),
	(EXTERNALS, routine_name, externals), (GROUPINGS, grouping_name, groupings)
]])

# Expressions
MAXINT.setParseAction(replaceWith(str(sys.maxint)))
MININT.setParseAction(replaceWith(str(-sys.maxint - 1)))
CURSOR.setParseAction(replaceWith('self.string.cursor'))
LIMIT.setParseAction(replaceWith('self.string.limit'))
SIZE.setParseAction(replaceWith('len(self.string)'))
sizeof_call = Suppress(SIZEOF) + str_ref
sizeof_call.setParseAction(lambda t: "len(%s)" % t[0])
expr_operand = (MAXINT | MININT | CURSOR | LIMIT | SIZE | sizeof_call | int_ref |
		int_literal).setName('operand')
mult_action = lambda t: ' '.join(t[0])
add_action = lambda t: '(' + ' '.join(t[0]) + ')'
expr = Forward()
expr << operatorPrecedence(
	expr_operand,
	[
		('-', 1, opAssoc.RIGHT),
		(oneOf('* /'), 2, opAssoc.LEFT, mult_action),
		(oneOf('+ -'), 2, opAssoc.LEFT, add_action)
	]
)
expr.setName('expression')

# Integer commands
def make_int_assign_cmd(op, name):
	cmd = (Suppress('$') + int_name + Suppress(op) + expr)
	cmd.setParseAction(lambda t: 'self._int_%s(%s, %s)' % (name, t[0], t[1]))
	return cmd

int_assign_cmd = MatchFirst(make_int_assign_cmd(op, name) for op, name in [
	('=', 'assign'), ('+=', 'add_assign'), ('*=', 'mult_assign'),
	('-=', 'sub_assign'), ('/=', 'div_assign')
])
int_rel_cmd = Suppress('$') + int_ref + oneOf('== > < != >= <=') + expr
int_rel_cmd.setParseAction(lambda t: '(' + ' '.join(t) + ')')
int_cmd = int_assign_cmd | int_rel_cmd


# String commands
c = Forward()
str_cmd = Group(Suppress('$') + str_ref + c)
call = lambda cmd: Group(cmd + c)
str_fun = lambda fun: Group(fun + string)
str_cmd_operand = (int_cmd | str_cmd | call(NOT) | call(TEST) | call(TRY) |
		call(DO) | call(FAIL) | call(GOTO) | call(GOPAST) | call(REPEAT) |
		Group(LOOP + expr + c) | Group(ATLEAST + expr + c) | string |
		Group('=' + string) | str_fun(INSERT) | str_fun('<+') | str_fun(ATTACH) |
		str_fun('<-') | DELETE | Group(HOP + expr) | NEXT | Group('=>' + str_ref) |
		'[' | ']' | Group('->' + str_ref) | Group(SETMARK + int_ref) |
		Group(TOMARK + expr) | Group(ATMARK + expr) | TOLIMIT | ATLIMIT |
		Group(SETLIMIT + c + FOR + c) | call(BACKWARDS) | call(REVERSE) | SUBSTRING |
		Group(AMONG + para_group(ZeroOrMore((str_literal + Optional(routine_ref)) +
		para_group(c)))) | Group(SET + boolean_ref) | Group(UNSET + boolean_ref) |
		name | Group(NON + Optional('-') + grouping_name) | TRUE | FALSE | '?')
# FIXME: Both routine_name and grouping_name are allowed in str_cmd_operand, but we cannot distinguish them on a syntactic level.
# FIXME: Similarly, there is no way to distinguish string and integer assignments on the syntactic level.
c << operatorPrecedence(str_cmd_operand, [(OR | AND, 2, opAssoc.LEFT)])

# Routine definition
routine_def = Suppress(DEFINE) + routine_name + Suppress(AS) + c

# Grouping definition
grouping_def = Suppress(DEFINE) + grouping_ref + delimitedList(grouping_ref |
		str_literal, delim=oneOf('+ -'))

# Program
program = Forward()
program << ZeroOrMore(declaration | routine_def | grouping_def |
		Group(BACKWARDMODE + para_group(program)) | str_escapes | str_def)
