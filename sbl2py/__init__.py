#!/usr/bin/env python

"""
A Snowball to Python compiler.
"""

import re
import sys
import traceback

from pyparsing import *

from sbl2py.utils import *

ParserElement.enablePackrat()


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


# Parse actions that correspond to Snowball declarations (``strings (...)``,
# ``booleans (...)``, ...) don't produce code but modify the parser's state by
# storing the declared names. This is necessary so that we can later correctly
# interpret the occurence of a declared name. The following lists hold the
# various declared names:

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
	return lambda t: prefix + t[0]

str_ref = Reference(strings).setParseAction(make_ref_action('self.s_'))
grouping_ref = Reference(groupings).setParseAction(make_ref_action('_g_'))
int_ref = Reference(integers).setParseAction(make_ref_action('self.i_'))
boolean_ref = Reference(booleans).setParseAction(make_ref_action('self.b_'))
routine_ref = Reference(routines)

str_literal = StringLiteral(str_escape_chars, str_defs)
int_literal = Word(nums).setName('integer literal')
string = str_ref | str_literal
grouping = grouping_ref | str_literal

str_ref_chars = str_ref.copy()
str_ref_chars.setParseAction(lambda t: 'self.s_' + t[0] + '.chars')


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
CURSOR.setParseAction(replaceWith('s.cursor'))
LIMIT.setParseAction(replaceWith('s.limit'))
SIZE.setParseAction(replaceWith('len(s)'))
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
		('-', 1, opAssoc.RIGHT, lambda t: ''.join(t[0])),
		(oneOf('* /'), 2, opAssoc.LEFT, mult_action),
		(oneOf('+ -'), 2, opAssoc.LEFT, add_action)
	]
)
expr.setName('expression')

# Integer commands
def make_int_assign_cmd(op):
	cmd = (Suppress('$') + int_ref + Suppress(op) + expr)
	cmd.setParseAction(lambda t: '%s %s %s' % (t[0], op, t[1]))
	return cmd

int_assign_cmd = MatchFirst(make_int_assign_cmd(op) for op in
		('=', '+=', '*=', '-=', '/='))
int_rel_cmd = Suppress('$') + int_ref + oneOf('== > < != >= <=') + expr
int_rel_cmd.setParseAction(lambda t: '(' + ' '.join(t) + ')')
int_cmd = int_assign_cmd | int_rel_cmd


# String commands
c = Forward()
str_cmd = Group(Suppress('$') + str_ref + c)

str_fun = lambda fun: Suppress(fun) + (str_literal | str_ref_chars)

def debug_parse_action(f):

	def wrapper(*args, **kwargs):
		print '%s(%s, %s)' % (f.__name__, ', '.join(repr(a) for a in args), ', '.join('%s=%s' % (k, repr(v)) for k, v in kwargs.iteritems()))
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
	removing empty lines and replacing words of the form ``<v\d*>`` with unique
	identifiers.

	The resulting code is then wrapped into a parse action. The parse action
	takes a list of tokens and inserts them into the pseudo code. The ``i``-th
	token replaces the string ``<i>``. Indentation is preserved.
	"""
	global var_index

	s = remove_empty_lines(s)

	for v in set(re.findall(r"<v\d*>", s)):
		unique = "var%d" % var_index
		var_index += 1
		s = s.replace(v, unique)

	def action(tokens):
		tokens = extract(tokens, lambda x: isinstance(x, basestring))

		def sub(match):
			return prefix_lines(tokens[int(match.group(2))], match.group(1))

		return re.sub(r"( *)<t(\d+)>", sub, s)

	return action

not_action = code("""
<v> = s.cursor
<t0>
if not r:
  s.cursor = <v>
r = not r
""")

test_action = code("""
<v> = s.cursor
<t0>
s.cursor = <v>
""")

try_action = code("""
<v> = s.cursor
<t0>
if not r:
  r = True
  s.cursor = <v>
""")

do_action = code("""
<v> = s.cursor
<t0>
s.cursor = <v>
r = True
""")

fail_action = code("""
<t0>
r = False
""")

goto_action = code("""
while True:
  <v> = s.cursor
  <t0>
  if r or s.cursor == s.limit:
    s.cursor = <v>
    break
  s.cursor += 1
""")

gopast_action = code("""
while True:
  <t0>
  if r or s.cursor == s.limit:
    break
  s.cursor += 1
""")

repeat_action = code("""
while True:
  <v> = s.cursor
  <t0>
  if not r:
    s.cursor = <v>
    break
r = True
""")

CMD_LOOP = Suppress(LOOP) + expr + c
CMD_LOOP.setParseAction(code("""
for <v> in xrange(<t0>):
  <t1>
"""))

CMD_ATLEAST = Suppress(ATLEAST) + expr + c
CMD_ATLEAST.setParseAction(code("""
for <v> in xrange(<t0>):
  <t1>
while True:
  <v> = s.cursor
  <t1>
  if not r:
    s.cursor = <v>
    break
r = True
"""))

CMD_INSERT = str_fun(INSERT | '<+')
CMD_INSERT.setParseAction(code("""
r = s.insert(<t0>)
"""))

CMD_ATTACH = str_fun(ATTACH)
CMD_ATTACH.setParseAction(code("""
r = s.attach(<t0>)
"""))

CMD_REPLACE_SLICE = str_fun('<-')
CMD_REPLACE_SLICE.setParseAction(code("""
r = s.set_range(<t0>, self.left, self.right)
"""))

CMD_EXPORT_SLICE = Suppress('->') + str_ref
CMD_EXPORT_SLICE.setParseAction(code("""
r = <t0>.set_chars(s.get_range(self.left, self.right))
"""))

CMD_HOP = Suppress(HOP) + expr
CMD_HOP.setParseAction(code("""
r = s.hop(<t0>)
"""))

CMD_NEXT = Suppress(NEXT)
CMD_NEXT.setParseAction(code("""
r = s.hop(1)
"""))


CMD_SET_LEFT_MARK = Literal('[')
CMD_SET_LEFT_MARK.setParseAction(code("""
self.left = s.cursor
"""))

CMD_SET_RIGHT_MARK = Literal(']')
CMD_SET_RIGHT_MARK.setParseAction(code("""
self.right = s.cursor
"""))

CMD_SETMARK = Suppress(SETMARK) + int_ref
CMD_SETMARK.setParseAction(code("""
<t0> = s.cursor
r = True
"""))

CMD_TOMARK = Suppress(TOMARK) + expr
CMD_TOMARK.setParseAction(code("""
r = s.tomark(<t0>)
"""))

CMD_ATMARK = Suppress(ATMARK) + expr
CMD_ATMARK.setParseAction(code("""
r = (s.cursor == <t0>)
"""))

CMD_SETLIMIT = Suppress(SETLIMIT) + c + Suppress(FOR) + c
CMD_SETLIMIT.setParseAction(code("""
<v1> = s.cursor
<v2> = len(s) - s.limit
<t0>
if r:
  s.limit = s.cursor
  s.cursor = <v1>
  <t1>
  s.limit = len(s) - <v2>
"""))

CMD_AMONG = Group(AMONG + para_group(ZeroOrMore((str_literal +
		Optional(routine_ref)) + para_group(c))))

CMD_SET = Suppress(SET) + boolean_ref
CMD_SET.setParseAction(code("""
<t0> = True
r = True
"""))

CMD_UNSET = Suppress(UNSET) + boolean_ref
CMD_UNSET.setParseAction(code("""
<t0> = False
r = True
"""))

CMD_NON = Suppress(NON + Optional('-')) + grouping_ref
CMD_NON.setParseAction(code("""
if s.cursor == s.limit:
  r = False
else:
  r = s.chars[s.cursor] not in <t0>
  if r:
    s.cursor += 1
"""))

CMD_DELETE = Suppress(DELETE)
CMD_DELETE.setParseAction(code("""
r = s.set_range('', self.left, self.right)
"""))

CMD_ATLIMIT = Suppress(ATLIMIT)
CMD_ATLIMIT.setParseAction(code("""
r = (s.cursor == s.limit)
"""))

CMD_TOLIMIT = Suppress(TOLIMIT)
CMD_TOLIMIT.setParseAction(code("""
r = s.tolimit()
"""))

CMD_STARTSWITH = string.copy()
CMD_STARTSWITH.setParseAction(code("""
r = s.startswith(<t0>)
"""))

CMD_ROUTINE = routine_ref.copy()
CMD_ROUTINE.setParseAction(code("""
r = self.r_<t0>(s)
"""))

and_action = code("""
<v> = s.cursor
<t0>
if r:
  s.cursor = <v>
  <t1>
""")

or_action = code("""
<v> = s.cursor
<t0>
if not r:
  s.cursor = <v>
  <t1>
""")


def debug(*args):
	print args

def make_chain(tokens):
	if not tokens:
		chain = ''
	elif len(tokens) == 1:
		chain = tokens[0]
	else:
		chain = tokens[0] + "\nif r:\n" + prefix_lines(make_chain(tokens[1:]), '  ')
	return chain

str_cmd_operand = (int_cmd | str_cmd | CMD_LOOP | CMD_ATLEAST | CMD_STARTSWITH |
		CMD_INSERT | CMD_ATTACH | CMD_REPLACE_SLICE | CMD_DELETE |
		CMD_HOP | CMD_NEXT | CMD_SET_LEFT_MARK | CMD_SET_RIGHT_MARK |
		CMD_EXPORT_SLICE | CMD_SETMARK | CMD_TOMARK | CMD_ATMARK | CMD_TOLIMIT |
		CMD_ATLIMIT | CMD_SETLIMIT | SUBSTRING | CMD_AMONG | CMD_SET | CMD_UNSET |
		CMD_ROUTINE | grouping_ref | CMD_NON | TRUE | FALSE | '?')
c << operatorPrecedence(
	str_cmd_operand,
	[
		(Suppress(AND), 2, opAssoc.LEFT, and_action),
		(Suppress(OR), 2, opAssoc.LEFT, or_action),
		(Suppress(NOT), 1, opAssoc.RIGHT, not_action),
		(Suppress(TEST), 1, opAssoc.RIGHT, test_action),
		(Suppress(TRY), 1, opAssoc.RIGHT, try_action),
		(Suppress(DO), 1, opAssoc.RIGHT, do_action),
		(Suppress(FAIL), 1, opAssoc.RIGHT, fail_action),
		(Suppress(GOTO), 1, opAssoc.RIGHT, goto_action),
		(Suppress(GOPAST), 1, opAssoc.RIGHT, gopast_action),
		(Suppress(REPEAT), 1, opAssoc.RIGHT, repeat_action),
		(Suppress(REVERSE), 1, opAssoc.RIGHT), # FIXME: Add action
		(Empty(), 2, opAssoc.LEFT, lambda t: make_chain(t[0])), # Concatenation without operator
	]
)

# FIXME: Add ``backwards`` sections

# Routine definition
routine_defs = []
routine_def = Suppress(DEFINE) + routine_ref + Suppress(AS) + c


ROUTINE_TEMPLATE = """
  def r_%(name)s(self, s):
    r = True
%(code)s
    return r
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
		str_literal.copy().setParseAction(lambda t: "set(%s)" % t[0]), delim=oneOf('+ -'))

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

  def __init__(self, s):
    self.chars = list(s)
    self.cursor = 0
    self.limit = len(s)

  def __str__(self):
    return ''.join(self.chars)

  def __len__(self):
    return len(self.chars)

  def assign(self, value):
    self.chars[self.cursor:self.limit] = value
    self.limit = self.cursor + len(value)
    return True

  def insert(self, value):
    self.attach(value)
    self.cursor += len(value)
    self.limit += len(value)
    return True

  def attach(self, value):
    self.chars[self.cursor:self.cursor] = value
    return True

  def set_chars(self, value):
    self.chars = value[:]
    self.cursor = 0
    self.limit = len(value)
    return True

  def get_range(self, start=None, end=None):
    if start is None:
      start = self.cursor
    if end is None:
      end = self.limit
    return self.chars[start:end]

  def set_range(self, values, start, end):
    if start > end or end > self.cursor:
      raise ValueError('Invalid range.')
    self.chars[start:end] = values
    change = len(values) - (end - start)
    self.cursor += change
    self.limit += change
    return True

  def startswith(self, value):
    if self.limit - self.cursor < len(value):
      return False
    value = list(value)
    if self.chars[self.cursor:self.cursor + len(value)] == value:
      self.cursor = self.cursor + len(value)
      return True
    return False

  def hop(self, n):
    if n < 0 or self.limit - self.cursor < n:
      return False
    self.cursor += n
    return True

  def tomark(self, i):
    if self.cursor > i or self.limit < i:
      return False
    self.cursor = i
    return True

  def tolimit(self):
    self.cursor = self.limit
    return True

%(groupings)s

class _Program(object):
  def __init__(self):
    self.left = None
    self.right = None
    %(integers)s
    %(booleans)s
    %(strings)s

  %(routines)s

%(functions)s
"""

FUNCTION_TEMPLATE = """
def %s(s):
  s = _String(s)
  _Program().r_%s(s)
  return str(s)
"""

TEST_FUNCTION_TEMPLATE = """
def %s(s):
  p = _Program()
  s = _String(s)
  p.r_%s(s)
  return s, p
"""

def translate_file(infile, *args, **kwargs):
	"""
	Translate a Snowball file to Python.

	``infile`` is an open readable file containing the Snowball source code. The
	return value is a string containing the translated Python code.
	"""
	return translate_string(infile.read(), *args, **kwargs)

def reset():
	"""
	Reset parser state.
	"""
	global strings, integers, externals, booleans, routines, groupings, grouping_defs, routine_defs, var_index
	strings[:] = []
	integers[:] = []
	externals[:] = []
	routines[:] = []
	groupings[:] = []
	grouping_defs[:] = []
	routine_defs[:] = []
	var_index = 0


def translate_string(code, testing=False):
	"""
	Translate a Snowball code string to Python.

	If ``testing`` is ``True`` then the external Snowball routines return both
	the original ``_String`` object and the ``_Program`` instance that created
	it. This is useful for checking that variables have been computed correctly.
	"""
	reset()
	py_code = program.parseString(code)

	groups = '\n'.join(grouping_defs)
	ints = '\n    '.join('self.i_%s = 0' % s for s in integers)
	bools = '\n    '.join('self.b_%s = False' % s for s in booleans)
	strs = '\n    '.join('self.s_%s = _String("")' % s for s in strings)
	defs = '\n\n  '.join(routine_defs)

	external_funs = []
	template = TEST_FUNCTION_TEMPLATE if testing else FUNCTION_TEMPLATE
	for ext in externals:
		external_funs.append(template % (ext, ext))
	funs = '\n'.join(external_funs)

	return MODULE_TEMPLATE % {
		'groupings':groups,
		'integers':ints,
		'booleans':bools,
		'strings':strs,
		'routines':defs,
		'functions':funs,
	}
