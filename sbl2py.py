#!/usr/bin/env python

"""
A Snowball to Python compiler.
"""

import re
import sys
import traceback

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
	return []

str_escapes = Suppress(STRINGESCAPES) + Word(printables, exact=2)
str_escapes.setParseAction(str_escapes_action)


class StringLiteral(Token):
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
		super(StringLiteral, self).__init__()
		self.escape_chars = escape_chars
		self.replacements = replacements

	def __str__(self):
		if self.escape_chars:
			return 'StringLiteral("%s%s")' % self.escape_chars
		else:
			return 'StringLiteral("")'

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
name = ~keyword + Word(alphas, alphanums + '_')
name.setParseAction(lambda t: t[0])

# Declarations
strings = []
integers = []
externals = []
booleans = []
routines = []
groupings = []

def make_declaration(kw, targets):
	decl = Suppress(kw) + Suppress('(') + ZeroOrMore(name) + Suppress(')')

	def action(tokens):
		for target in targets:
			target.extend(tokens)
		return []

	decl.setParseAction(action)
	return decl
		
declaration = MatchFirst([make_declaration(kw, targets) for kw, targets in [
	(STRINGS, [strings]), (INTEGERS, [integers]), (BOOLEANS, [booleans]),
	(ROUTINES, [routines]), (EXTERNALS, [externals, routines]),
	(GROUPINGS, [groupings])
]])


# Chars that are valid in a ``Reference``
REFERENCE_CHARS = set(alphanums + '_')

class Reference(Token):
	"""
	A reference to a previously declared variable.

	This class works like pyparsing's ``Or`` in combination with ``Keyword``.
	However, the list of candidates can be updated later on.
	"""

	def __init__(self, declarations):
		"""
		Constructor.

		``declarations`` is a list of previously declared variables. Any of them
		will match if they occur as a separate word (cf. ``Keyword``). Matching is
		done in decreasing length of candidates (cf. ``Or``). Later updates of
		``declarations`` are taken into account.
		"""
		super(Reference, self).__init__()
		self.declarations = declarations

	def __str__(self):
		return 'Reference(%s)' % self.declarations

	def parseImpl(self, instring, loc, doActions=True):
		candidates = sorted(self.declarations, key=lambda x: len(x), reverse=True)
		for candidate in candidates:
			if instring.startswith(candidate, loc):
				n = len(candidate)
				if (len(instring) == loc + n or instring[loc + n] not in
						REFERENCE_CHARS):
					return loc + n, candidate
		raise ParseException("Expected one of " + ", ".join(candidates))


def make_ref_action(prefix):
	return lambda t: 'self.' + prefix + '_' + t[0]

str_ref = Reference(strings).setParseAction(make_ref_action('s'))
grouping_ref = Reference(groupings).setParseAction(make_ref_action('g'))
int_ref = Reference(integers).setParseAction(make_ref_action('i'))
boolean_ref = Reference(booleans).setParseAction(make_ref_action('b'))
routine_ref = Reference(routines)

str_literal = StringLiteral(str_escape_chars, str_defs)
int_literal = Word(nums).setName('integer literal')
string = str_ref | str_literal
grouping = grouping_ref | str_literal


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
	return []

str_def = Suppress(STRINGDEF) + Word(printables) + Optional(HEX | DECIMAL,
		default=None) + str_literal
str_def.setParseAction(str_def_action)


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
	cmd = (Suppress('$') + int_ref + Suppress(op) + expr)
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
call = lambda cmd: Suppress(cmd) + c
str_fun = lambda fun: Suppress(fun) + string


def remove_empty_lines(s):
	return '\n'.join(line for line in s.split('\n') if line)

def prefix_lines(s, p):
	"""
	Prefix each line of ``s`` by ``p``.
	"""
	return p + ('\n' + p).join(s.split('\n'))


def debug_exceptions(f):

	def wrapper(*args, **kwargs):
		try:
			return f(*args, **kwargs)
		except:
			traceback.print_exc()
			raise

	return wrapper


# Variable index for unique local variables
var_index = 0

def code(s):
	"""
	Create a parse action that produces Python code.

	``s`` is a string containing pseudo Python code which is prepared by
	removing empty lines and replacing words of the form ``v\d*`` with unique
	identifiers.

	The resulting code is then wrapped into a parse action. The parse action
	takes a list of tokens and inserts them into the pseudo code. The ``i``-th
	token replaces the string ``ti``. Similarly, ``Ti`` is replaced by the
	same token. However, in that case the indentation of ``Ti`` is preserved,
	even if the token consists of multiple lines.
	"""
	global var_index

	s = remove_empty_lines(s)

	for v in set(re.findall(r"\bv\d*\b", s)):
		unique = "var%d" % var_index
		var_index += 1
		s = re.sub(r"\b%s\b" % v, unique, s)

	def action(tokens):
		result = s
		for t in set(re.findall(r"\bt\d+\b", result)):
			i = int(t[1:])
			result = re.sub(r"\b%s\b" % t, tokens[i], result)

		def sub(match):
			i = int(match.group(2))
			return prefix_lines(tokens[i], match.group(1))

		result = re.sub(r"( *)T(\d+)\b", sub, result)
		
		return result

	return action

CMD_NOT = call(NOT)
CMD_NOT.setParseAction(code("""
v = s.cursor
T0
if not r:
  s.cursor = v
r = not r
"""))

CMD_TEST = call(TEST)
CMD_TEST.setParseAction(code("""
v = s.cursor
T0
s.cursor = v
"""))

CMD_TRY = call(TRY)
CMD_TRY.setParseAction(code("""
v = s.cursor
T0
if not r:
  r = True
  s.cursor = v
"""))

CMD_DO = call(DO)
CMD_DO.setParseAction(code("""
v = s.cursor
T0
s.cursor = v
r = True
"""))

CMD_FAIL = call(FAIL)
CMD_FAIL.setParseAction(code("""
T0
r = False
"""))

CMD_GOTO = call(GOTO)
CMD_GOTO.setParseAction(code("""
while True:
  v = x.cursor
  T0
  if r or x.cursor == x.limit:
    x.cursor = v
    break
  x.cursor += 1
"""))

CMD_GOPAST = call(GOPAST)
CMD_GOPAST.setParseAction(code("""
while True:
  T0
  if r or x.cursor == x.limit:
    break
  x.cursor += 1
"""))

CMD_REPEAT = call(REPEAT)
CMD_REPEAT.setParseAction(code("""
while True:
  v = x.cursor
  T0
  if not r:
    x.cursor = v
    break
r = True
"""))

CMD_LOOP = Suppress(LOOP) + expr + c
CMD_LOOP.setParseAction(code("""
for v in range(t0):
  T1
"""))

CMD_ATLEAST = Suppress(ATLEAST) + expr + c
CMD_ATLEAST.setParseAction(code("""
for v in range(t0):
  T1
while True:
  v = x.cursor
  T1
  if not r:
    x.cursor = v
    break
r = True
"""))

CMD_ASSIGN = Suppress('=') + string
CMD_ASSIGN.setParseAction(code("""
r = x.assign(t0)
"""))

CMD_INSERT = str_fun(INSERT) | str_fun('<+')
CMD_INSERT.setParseAction(code("""
r = x.insert(t0)
"""))

CMD_ATTACH = str_fun(ATTACH)
CMD_ATTACH.setParseAction(code("""
r = x.attach(t0)
"""))

CMD_REPLACE_SLICE = str_fun('<-')
CMD_REPLACE_SLICE.setParseAction(code("""
r = x.set_range(t0, left, right)
"""))

CMD_EXPORT_SLICE = Suppress('->') + str_ref
CMD_EXPORT_SLICE.setParseAction(code("""
r = t0.set_chars(x.get_range(left, right))
"""))

CMD_HOP = Suppress(HOP) + expr
CMD_HOP.setParseAction(code("""
r = x.hop(t0)
"""))

CMD_SET_STRING = Suppress('=>') + str_ref
CMD_SET_STRING.setParseAction(code("""
t0.set_chars(x.get_range())
r = True
"""))

CMD_SET_LEFT_MARK = Literal('[')
CMD_SET_LEFT_MARK.setParseAction(code("""
left = x.cursor
"""))

CMD_SET_RIGHT_MARK = Literal(']')
CMD_SET_RIGHT_MARK.setParseAction(code("""
right = x.cursor
"""))

CMD_SETMARK = Suppress(SETMARK) + int_ref
CMD_SETMARK.setParseAction(code("""
self.i_j = x.cursor
r = True
"""))

CMD_TOMARK = Suppress(TOMARK) + expr
CMD_TOMARK.setParseAction(code("""
r = x.tomark(t0)
"""))

CMD_ATMARK = Group(ATMARK + expr)
CMD_ATMARK.setParseAction(code("""
r = (x.cursor == t0)
"""))

CMD_SETLIMIT = Suppress(SETLIMIT) + c + Suppress(FOR) + c
CMD_SETLIMIT.setParseAction(code("""
v1 = x.cursor
v2 = x.limit
T0
if r:
  x.limit = x.cursor
  x.cursor = v1
  T1
  x.limit = v2
"""))

CMD_BACKWARDS = call(BACKWARDS)

CMD_REVERSE = call(REVERSE)

CMD_AMONG = Group(AMONG + para_group(ZeroOrMore((str_literal +
		Optional(routine_ref)) + para_group(c))))

CMD_SET = Suppress(SET) + boolean_ref
CMD_SET.setParseAction(code("""
t0 = True
r = True
"""))

CMD_UNSET = Suppress(UNSET) + boolean_ref
CMD_UNSET.setParseAction(code("""
t0 = False
r = True
"""))

CMD_NON = Suppress(NON + Optional('-')) + grouping_ref
CMD_NON.setParseAction(code("""
if x.cursor == x.limit:
  r = False
else:
  r = x.chars[x.cursor] not in t0
  if r:
    x.cursor += 1
"""))

CMD_DELETE = Suppress(DELETE)
CMD_DELETE.setParseAction(code("""
r = x.set_range('', left, right)
"""))

CMD_ATLIMIT = Suppress(ATLIMIT)
CMD_ATLIMIT.setParseAction(code("""
r = (x.cursor == x.limit)
"""))

CMD_TOLIMIT = Suppress(TOLIMIT)
CMD_TOLIMIT.setParseAction(code("""
r = x.tolimit()
"""))

str_cmd_operand = (int_cmd | str_cmd | CMD_NOT | CMD_TEST | CMD_TRY | CMD_DO |
		CMD_FAIL | CMD_GOTO | CMD_GOPAST | CMD_REPEAT | CMD_LOOP | CMD_ATLEAST |
		string | CMD_ASSIGN | CMD_INSERT | CMD_ATTACH | CMD_REPLACE_SLICE |
		CMD_DELETE | CMD_HOP | NEXT | CMD_SET_STRING | CMD_SET_LEFT_MARK |
		CMD_SET_RIGHT_MARK | CMD_EXPORT_SLICE | CMD_SETMARK | CMD_TOMARK |
		CMD_ATMARK | CMD_TOLIMIT | CMD_ATLIMIT | CMD_SETLIMIT | CMD_BACKWARDS |
		CMD_REVERSE | SUBSTRING | CMD_AMONG | CMD_SET | CMD_UNSET | routine_ref |
		grouping_ref | CMD_NON | TRUE | FALSE | '?')
c << operatorPrecedence(
	str_cmd_operand,
	[
		(OR | AND, 2, opAssoc.LEFT),
		(Empty(), 2, opAssoc.LEFT, lambda t: '\n'.join(t[0])), # Concatenation without operator
		]                                         # FIXME: We need to abort concatenated chains after a false result
)

# Routine definition
routine_defs = []
routine_def = Suppress(DEFINE) + routine_ref + Suppress(AS) + c


ROUTINE_TEMPLATE = """
  def r_%(name)s(self, s):
%(code)s
    return s
"""

def routine_def_action(tokens):
	routine_defs.append(ROUTINE_TEMPLATE % {
		'name':tokens[0],
		'code':prefix_lines(tokens[1], '    ')
	})
	return []

routine_def.setParseAction(routine_def_action)

# Grouping definition
grouping_defs = []
grouping_def = Suppress(DEFINE) + grouping_ref + delimitedList(grouping_ref |
		str_literal.setParseAction(lambda t: "set(%s)" % t[0]), delim=oneOf('+ -'))

def grouping_def_action(tokens):
	grouping_defs.append(tokens[0] + " = " + " | ".join(tokens[1:]))
	return []

grouping_def.setParseAction(grouping_def_action)

# Program
program = Forward()
program << (ZeroOrMore(declaration | routine_def | grouping_def |
		Group(BACKWARDMODE + para_group(program)) | str_escapes | str_def) +
		StringEnd())


MODULE_TEMPLATE = """
class _String(object):
  pass


class _Program(object):
  def __init__(self):
    %(groupings)s
    %(integers)s
    %(booleans)s
    %(strings)s

  %(routines)s

%(functions)s
"""


def translate_file(infile):
	"""
	Translate a Snowball file to Python.

	``infile`` is an open readable file containing the Snowball source code. The
	return value is a string containing the translated Python code.
	"""
	return translate_code(infile.read())


def translate_code(code):
	"""
	Translate a Snowball code string to Python.
	"""
	py_code = program.parseString(code)

	groups = '\n    '.join(grouping_defs)
	ints = '\n    '.join('self.i_%s = 0' % s for s in integers)
	bools = '\n    '.join('self.b_%s = False' % s for s in booleans)
	strs = '\n    '.join('self.s_%s = String("")' % s for s in strings)
	defs = '\n\n  '.join(routine_defs)

	external_funs = []
	for ext in externals:
		external_funs.append('%s = lambda s: _Program().r_%s(s)' % (ext, ext))
	funs = '\n'.join(external_funs)

	return MODULE_TEMPLATE % {
		'groupings':groups,
		'integers':ints,
		'booleans':bools,
		'strings':strs,
		'routines':defs,
		'functions':funs,
	}

if __name__ == '__main__':

	import sys
	import argparse
	parser = argparse.ArgumentParser(description='Compile Snowball to Python')
	parser.add_argument('infile', help='Input file (default STDIN)', nargs='?',
			type=argparse.FileType('r'), default=sys.stdin)
	parser.add_argument('outfile', help='Output file (default STDOUT)', nargs='?',
			type=argparse.FileType('w'), default=sys.stdout)
	args = parser.parse_args()

	args.outfile.write(translate_file(args.infile) + "\n")
