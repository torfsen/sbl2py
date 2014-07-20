#!/usr/bin/env python

"""
A Snowball to Python compiler.
"""

import functools
import inspect
import re
import sys
import traceback

from pyparsing import *

from sbl2py.utils import *

ParserElement.enablePackrat()


def parse_action(f):
	"""
	Decorator for pyparsing parse actions to ease debugging.
	
	pyparsing uses trial & error to deduce the number of arguments a parse
	action accepts. Unfortunately any ``TypeError`` raised by a parse action
	confuses that mechanism.

	This decorator replaces the trial & error mechanism with one based on
	reflection. If the decorated function itself raises a ``TypeError`` then
	that exception is re-raised if the wrapper is called with less arguments
	than required. This makes sure that the actual ``TypeError`` bubbles up
	from the call to the parse action (instead of the one caused by pyparsing's
	trial & error).
	"""
	num_args = len(inspect.getargspec(f).args)
	if num_args > 3:
		raise ValueError('Input function must take at most 3 parameters.')

	@functools.wraps(f)
	def action(*args):
		if len(args) < num_args:
			if action.exc_info:
				raise action.exc_info[0], action.exc_info[1], action.exc_info[2]
		action.exc_info = None
		try:
			v = f(*args[:-(num_args + 1):-1])
			return v
		except TypeError as e:
			action.exc_info = sys.exc_info()
			raise
	
	action.exc = None
	return action


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

@parse_action
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
name.setParseAction(parse_action(lambda t: t[0]))


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

	@parse_action
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
	return parse_action(lambda t: prefix + t[0])

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
str_ref_chars.setParseAction(parse_action(lambda t: 'self.s_' + t[0] + '.chars'))


# String definitions

@parse_action
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
sizeof_call.setParseAction(parse_action(lambda t: "len(%s)" % t[0]))
expr_operand = (MAXINT | MININT | CURSOR | LIMIT | SIZE | sizeof_call | int_ref |
		int_literal).setName('operand')
mult_action = parse_action(lambda t: ' '.join(t[0]))
add_action = parse_action(lambda t: '(' + ' '.join(t[0]) + ')')
expr = Forward()
expr << operatorPrecedence(
	expr_operand,
	[
		('-', 1, opAssoc.RIGHT, parse_action(lambda t: ''.join(t[0]))),
		(oneOf('* /'), 2, opAssoc.LEFT, mult_action),
		(oneOf('+ -'), 2, opAssoc.LEFT, add_action)
	]
)
expr.setName('expression')

# Integer commands
def make_int_assign_cmd(op):
	cmd = (Combine(Suppress('$') + int_ref) + Suppress(op) + expr)
	cmd.setParseAction(parse_action(lambda t: '%s %s %s\nr = True' % (t[0], op, t[1])))
	return cmd

int_assign_cmd = MatchFirst(make_int_assign_cmd(op) for op in
		('=', '+=', '*=', '-=', '/='))
int_rel_cmd = Combine(Suppress('$') + int_ref) + oneOf('== > < != >= <=') + expr
int_rel_cmd.setParseAction(parse_action(lambda t: 'r = ' + ' '.join(t)))
int_cmd = int_assign_cmd | int_rel_cmd


# String commands

# Generating code for ``substring ... among`` on the fly (i.e. without
# generating a full AST) requires us to distinguish between those string
# commands that can occur between ``substring`` and ``among`` and those that
# can't.

STR_CMD_A = Forward()  # Any string command that is allowed between ``substring`` and ``among``
STR_CMD_B = Forward()  # Any string command

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


def replace_placeholders(s, tokens):
	"""
	Replace placeholders in pseudo code.

	``s`` is a string containing pseudo Python code which is prepared using the
	following steps:

	- Empty lines are removed

	- Words of the form ``<v\d*>`` are replaced with unique identifiers

	- Words of the form ``<t\d+>`` are replaced with the corresponding item in
	  the ``tokens`` list. Indentation is preserved, even among multiple lines.
	"""
	global var_index

	s = remove_empty_lines(s)

	tokens = extract_strings(tokens)
	for v in set(re.findall(r"<v\d*>", s)):
		unique = "var%d" % var_index
		var_index += 1
		s = s.replace(v, unique)

	def sub(match):
		return prefix_lines(tokens[int(match.group(2))], match.group(1))

	return re.sub(r"( *)<t(\d+)>", sub, s)


def annotate_code(code, caption=''):
	return annotate(code, caption, single='   # ', first='  ## ', middle='   # ', last='  ## ')

def make_pseudo_code_action(s, caption=''):
	"""
	Create a parse action that produces Python code from pseudo code.
	"""

	@parse_action
	def action(tokens):
		code = replace_placeholders(s, tokens)
		if caption:
			code = annotate_code(code, caption)
		return code

	return action

not_action = make_pseudo_code_action("""
<v> = s.cursor
<t0>
if not r:
  s.cursor = <v>
r = not r
""", 'not')

test_action = make_pseudo_code_action("""
<v> = s.cursor
<t0>
s.cursor = <v>
""", 'test')

try_action = make_pseudo_code_action("""
<v> = s.cursor
<t0>
if not r:
  r = True
  s.cursor = <v>
""", 'try')

do_action = make_pseudo_code_action("""
if s.direction == 1:
  <v> = s.cursor
else:
  <v> = len(s) - s.cursor
<t0>
if s.direction == 1:
  s.cursor = <v>
else:
  s.cursor = len(s) - <v>
r = True
""", 'do')

fail_action = make_pseudo_code_action("""
<t0>
r = False
""", 'fail')

goto_action = make_pseudo_code_action("""
while True:
  <v> = s.cursor
  <t0>
  if r or s.cursor == s.limit:
    s.cursor = <v>
    break
  s.cursor += s.direction
""", 'goto')

gopast_action = make_pseudo_code_action("""
while True:
  <t0>
  if r or s.cursor == s.limit:
    break
  s.cursor += s.direction
""", 'gopast')

repeat_action = make_pseudo_code_action("""
while True:
  <v> = s.cursor
  <t0>
  if not r:
    s.cursor = <v>
    break
r = True
""", 'repeat')

backwards_action = make_pseudo_code_action("""
<v0> = s.cursor
<v1> = len(s) - s.limit
s.direction *= -1
s.cursor, s.limit = s.limit, s.cursor
<t0>
s.direction *= -1
s.cursor = <v0>
s.limit = len(s) - <v1>
""", 'backwards')

loop_action = make_pseudo_code_action("""
for <v> in xrange(<t0>):
  <t1>
""", 'loop')

atleast_action = make_pseudo_code_action("""
for <v> in xrange(<t0>):
  <t1>
while True:
  <v> = s.cursor
  <t1>
  if not r:
    s.cursor = <v>
    break
r = True
""", 'atleast')

CMD_INSERT = str_fun(INSERT | '<+')
CMD_INSERT.setParseAction(make_pseudo_code_action("""
r = s.insert(<t0>)
""", 'insert'))

CMD_ATTACH = str_fun(ATTACH)
CMD_ATTACH.setParseAction(make_pseudo_code_action("""
r = s.attach(<t0>)
""", 'attach'))

CMD_REPLACE_SLICE = str_fun('<-')
CMD_REPLACE_SLICE.setParseAction(make_pseudo_code_action("""
r = s.set_range(self.left, self.right, <t0>)
""", '<-'))

CMD_EXPORT_SLICE = Suppress('->') + str_ref
CMD_EXPORT_SLICE.setParseAction(make_pseudo_code_action("""
r = <t0>.set_chars(s.get_range(self.left, self.right))
""", '->'))

CMD_HOP = Suppress(HOP) + expr
CMD_HOP.setParseAction(make_pseudo_code_action("""
r = s.hop(<t0>)
""", 'hop'))

CMD_NEXT = Suppress(NEXT)
CMD_NEXT.setParseAction(make_pseudo_code_action("""
r = s.hop(1)
""", 'next'))


CMD_SET_LEFT_MARK = Literal('[')
CMD_SET_LEFT_MARK.setParseAction(make_pseudo_code_action("""
self.left = s.cursor
""", '['))

CMD_SET_RIGHT_MARK = Literal(']')
CMD_SET_RIGHT_MARK.setParseAction(make_pseudo_code_action("""
self.right = s.cursor
""", ']'))

CMD_SETMARK = Suppress(SETMARK) + int_ref
CMD_SETMARK.setParseAction(make_pseudo_code_action("""
<t0> = s.cursor
r = True
""", 'setmark'))

CMD_TOMARK = Suppress(TOMARK) + expr
CMD_TOMARK.setParseAction(make_pseudo_code_action("""
r = s.to_mark(<t0>)
""", 'tomark'))

CMD_ATMARK = Suppress(ATMARK) + expr
CMD_ATMARK.setParseAction(make_pseudo_code_action("""
r = (s.cursor == <t0>)
""", 'atmark'))


CMD_SET = Suppress(SET) + boolean_ref
CMD_SET.setParseAction(make_pseudo_code_action("""
<t0> = True
r = True
""", 'set'))

CMD_UNSET = Suppress(UNSET) + boolean_ref
CMD_UNSET.setParseAction(make_pseudo_code_action("""
<t0> = False
r = True
""", 'unset'))

CMD_NON = Suppress(NON + Optional('-')) + grouping_ref
CMD_NON.setParseAction(make_pseudo_code_action("""
if s.cursor == s.limit:
  r = False
elif s.direction == 1:
  r = s.chars[s.cursor] not in <t0>
else:
  r = s.chars[s.cursor - 1] not in <t0>
if r:
  s.cursor += s.direction
""", 'non'))

CMD_DELETE = Suppress(DELETE)
CMD_DELETE.setParseAction(make_pseudo_code_action("""
r = s.set_range(self.left, self.right, '')
""", 'delete'))

CMD_ATLIMIT = Suppress(ATLIMIT)
CMD_ATLIMIT.setParseAction(make_pseudo_code_action("""
r = (s.cursor == s.limit)
""", 'atlimit'))

CMD_TOLIMIT = Suppress(TOLIMIT)
CMD_TOLIMIT.setParseAction(make_pseudo_code_action("""
s.cursor = s.limit
r = True
""", 'tolimit'))

CMD_STARTSWITH = string.copy()
CMD_STARTSWITH.setParseAction(make_pseudo_code_action("""
r = s.starts_with(<t0>)
""", 'startswith'))

CMD_ROUTINE = routine_ref.copy()
CMD_ROUTINE.setParseAction(make_pseudo_code_action("""
r = self.r_<t0>(s)
""", 'routine call'))

CMD_GROUPING = grouping_ref.copy()
CMD_GROUPING.setParseAction(make_pseudo_code_action("""
if s.cursor == s.limit:
  r = False
elif s.direction == 1:
  r = s.chars[s.cursor] in _g_<t0>
else:
  r = s.chars[s.cursor - 1] in _g_<t0>
if r:
  s.cursor += s.direction
""", 'grouping'))

CMD_TRUE = Suppress(TRUE)
CMD_TRUE.setParseAction(make_pseudo_code_action("""
r = True
""", 'true'))

CMD_FALSE = Suppress(FALSE)
CMD_FALSE.setParseAction(make_pseudo_code_action("""
r = False
""", 'false'))

CMD_BOOLEAN = boolean_ref.copy()
CMD_BOOLEAN.setParseAction(make_pseudo_code_action("""
r = self.b_<t0>
""", 'boolean reference'))

among_vars = []


def generate_substring_code():
	index = len(among_vars)
	result = """
a%d = None
<v0> = s.cursor
r = False
for <v1>, <v2> in _a_%d:
  if s.starts_with(<v1>):
    a%d = <v2>
    r = True
    break
  else:
    s.cursor = <v0>
""" % (index, index, index)
	return annotate_code(replace_placeholders(result, []), 'substring')


def generate_among_code(tokens):
	global among_vars
	strings = []
	for index, arg in enumerate(tokens):
		strings.extend((string[1:-1], index) for string in arg[0])
	strings.sort(cmp=lambda x, y: len(y[0]) - len(x[0])) # Sort by decreasing length
	commands = (arg[1] if len(arg) > 1 else 'r = True' for arg in tokens)
	among_index = len(among_vars)
	among_vars.append(repr(strings))
	result = []
	for index, command in enumerate(commands):
		result.append('if a%d == %d:\n' % (among_index, index) + prefix_lines(command, '  '))
	return annotate_code('\n'.join(result), 'among')


@parse_action
def make_chain(tokens):
	tokens = extract_strings(tokens)
	if not tokens:
		chain = ''
	elif len(tokens) == 1:
		chain = tokens[0]
	else:
		chain = tokens[0] + "\nif r:\n" + prefix_lines(make_chain(tokens[1:]), '  ')
	return chain

@parse_action
def cmd_substring_among_action(tokens):
	result = []
	result.append(generate_substring_code())
	result.extend(tokens[0])
	result.append(generate_among_code(tokens[1]))
	return make_chain(result)


def make_if_chain_action(use_not):
	not_str = 'not ' if use_not else ''

	@parse_action
	def action(tokens):
		tokens = tokens[0]
		lines = ['<v> = s.cursor', '<t0>']
		prefix = ''
		for t in range(1, len(tokens)):
			lines.append(prefix + 'if ' + not_str +'r:')
			prefix += '  '
			lines.append(prefix + 's.cursor = <v>')
			lines.append(prefix + '<t%d>' % t)
		return replace_placeholders('\n'.join(lines), tokens)

	return action

and_action = make_if_chain_action(False)
or_action = make_if_chain_action(True)


def debug(*args):
	print args

def debug1(arg):
	print arg


unary_actions = {
	'not':not_action,
	'test':test_action,
	'try':try_action,
	'do':do_action,
	'fail':fail_action,
	'goto':goto_action,
	'gopast':gopast_action,
	'repeat':repeat_action,
	'backwards':backwards_action,
	'loop':loop_action,
	'atleast':atleast_action,
}

@parse_action
def unary_action(tokens):
	tokens = extract_strings(tokens)
	return unary_actions[tokens[0]](tokens[1:])


concatenation_action = parse_action(lambda t: make_chain(t[0]))

STR_CMD_OPERAND_A = (int_cmd | CMD_STARTSWITH |
		CMD_INSERT | CMD_ATTACH | CMD_REPLACE_SLICE | CMD_DELETE |
		CMD_HOP | CMD_NEXT | CMD_SET_LEFT_MARK | CMD_SET_RIGHT_MARK |
		CMD_EXPORT_SLICE | CMD_SETMARK | CMD_TOMARK | CMD_ATMARK | CMD_TOLIMIT |
		CMD_ATLIMIT | CMD_SET | CMD_UNSET |
		CMD_ROUTINE | CMD_GROUPING | CMD_NON | CMD_TRUE | CMD_FALSE | CMD_BOOLEAN )

CMD_SUBSTRING_AMONG = Forward()
STR_CMD_OPERAND_B = STR_CMD_OPERAND_A | CMD_SUBSTRING_AMONG

def make_str_cmd_pattern(str_cmd, operands):
	CMD_SETLIMIT = Suppress(SETLIMIT) + str_cmd + Suppress(FOR) + str_cmd
	CMD_SETLIMIT.setParseAction(make_pseudo_code_action("""
<v0> = s.cursor
<v1> = len(s) - s.limit
<t0>
if r:
  s.limit = s.cursor
  s.cursor = <v0>
  <t1>
  s.limit = len(s) - <v1>
	"""))
	str_cmd << operatorPrecedence(
		operands | CMD_SETLIMIT,
		[
			(NOT | TEST | TRY | DO | FAIL | GOTO | GOPAST | REPEAT | BACKWARDS | (LOOP + expr) | (ATLEAST + expr), 1, opAssoc.RIGHT, unary_action),
			(Suppress(AND), 2, opAssoc.LEFT, and_action),
			(Suppress(OR), 2, opAssoc.LEFT, or_action),
			(Empty(), 2, opAssoc.LEFT, concatenation_action), # Concatenation without operator
		]
	)

make_str_cmd_pattern(STR_CMD_A, STR_CMD_OPERAND_A)
make_str_cmd_pattern(STR_CMD_B, STR_CMD_OPERAND_B)

AMONG_ARG = Forward()
CMD_AMONG = Suppress(AMONG + '(') + Group(OneOrMore(AMONG_ARG)) + Suppress(')')
CMD_SUBSTRING_AMONG << Group(Optional(Suppress(SUBSTRING) + ZeroOrMore(STR_CMD_A))) + CMD_AMONG
CMD_SUBSTRING_AMONG.setParseAction(cmd_substring_among_action)
AMONG_ARG << Group(Group(OneOrMore(str_literal)) + Optional(Suppress('(') + STR_CMD_B + Suppress(')')))


# Routine definition
routine_defs = []
routine_def = Suppress(DEFINE) + routine_ref + Suppress(AS) + STR_CMD_B

ROUTINE_TEMPLATE = """
  def r_%(name)s(self, s):
    r = True
%(code)s
    return r
"""

@parse_action
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
		str_literal.copy().setParseAction(parse_action(lambda t: "set(%s)" % t[0])), delim=oneOf('+ -'))

@parse_action
def grouping_def_action(tokens):
	grouping_defs.append(tokens[0] + " = " + " | ".join(tokens[1:]))
	return []

grouping_def.setParseAction(grouping_def_action)

# Program
PROGRAM_ATOM = declaration | routine_def | grouping_def | str_escapes | str_def
BACKWARD_SECTION = Suppress(BACKWARDMODE + "(") + ZeroOrMore(PROGRAM_ATOM) + Suppress(')')
program = ZeroOrMore(PROGRAM_ATOM | BACKWARD_SECTION) + StringEnd()
program.ignore(cStyleComment | dblSlashComment)

MODULE_TEMPLATE = """
class _String(object):

  def __init__(self, s):
    self.chars = list(s)
    self.cursor = 0
    self.limit = len(s)
    self.direction = 1

  def __str__(self):
    return ''.join(self.chars)

  def __len__(self):
    return len(self.chars)

  def get_range(self, start, stop):
    if self.direction == 1:
      return self.chars[start:stop]
    else:
      n = len(self.chars)
      return self.chars[stop:start]

  def set_range(self, start, stop, chars):
    if self.direction == 1:
      self.chars[start:stop] = chars
    else:
      self.chars[stop:start] = chars
    change = self.direction * (len(chars) - (stop - start))
    if self.direction == 1:
      if self.cursor >= stop:
        self.cursor += change
      if self.limit >= stop:
        self.limit += change
    else:
      if self.cursor > start:
        self.cursor += change
      if self.limit > start:
        self.limit += change
    return True

  def insert(self, chars):
    self.chars[self.cursor:self.cursor] = chars
    if self.direction == 1:
      self.cursor += len(chars)
      self.limit += len(chars)
    return True

  def attach(self, chars):
    self.chars[self.cursor:self.cursor] = chars
    if self.direction == 1:
      self.limit += len(chars)
    else:
      self.cursor += len(chars)
    return True

  def set_chars(self, chars):
    self.chars = chars
    if self.direction == 1:
      self.cursor = 0
      self.limit = len(chars)
    else:
      self.cursor = len(chars)
      self.limit = 0
    return True

  def starts_with(self, chars):
    n = len(chars)
    r = self.get_range(self.cursor, self.limit)[::self.direction][:n]
    if not r == list(chars)[::self.direction]:
      return False
    self.cursor += n * self.direction
    return True

  def hop(self, n):
    if n < 0 or len(self.get_range(self.cursor, self.limit)) < n:
      return False
    self.cursor += n * self.direction
    return True

  def to_mark(self, mark):
    if self.direction == 1:
      if self.cursor > mark or self.limit < mark:
        return False
    else:
      if self.cursor < mark or self.limit > mark:
        return False
    self.cursor = mark
    return True

%(groupings)s

%(amongs)s

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
	global strings, integers, externals, booleans, routines, groupings, grouping_defs, routine_defs, var_index, among_vars
	strings[:] = []
	integers[:] = []
	externals[:] = []
	routines[:] = []
	groupings[:] = []
	grouping_defs[:] = []
	routine_defs[:] = []
	var_index = 0
	among_vars[:] = []


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
	amongs = '\n'.join('_a_%d = %s' % (i, c) for i, c in enumerate(among_vars))
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
		'amongs':amongs,
		'integers':ints,
		'booleans':bools,
		'strings':strs,
		'routines':defs,
		'functions':funs,
	}
