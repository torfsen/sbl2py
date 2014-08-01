#!/usr/bin/env python
# vim:fileencoding=utf8

"""
Abstract syntax tree (AST) and code generation for sbl2py.
"""

import collections
import re

from sbl2py.utils import remove_empty_lines, extract_strings, prefix_lines, annotate


class Environment(object):
	"""
	Code generation environment.

	Encapsulates the options and state of a code generation session.
	"""
	def __init__(self, debug=False):
		"""
		Constructor.

		If ``debug`` is true then the public routines of the exported code return
		a tuple consisting of the ``_String`` wrapper and the ``_Program`` instance
		that was executed.
		"""
		self.debug = debug
		self.direction = 1
		self.module_code = []
		self.class_code = []
		self.init_code = []
		self.among_index = 0
		self.var_index = 0

	def claim_among_index(self):
		self.among_index += 1
		return self.among_index

	def transform_pseudo_code(self, code, tokens):
		"""
		Replace placeholders in pseudo code.

		``s`` is a string containing pseudo Python code which is prepared using the
		following steps:

		- Empty lines are removed

		- Words of the form ``<v\d*>`` are replaced with unique identifiers

		- Words of the form ``<t\d+>`` are replaced with the corresponding item in
			the ``tokens`` list. Indentation is preserved, even among multiple lines.
		"""
		code = remove_empty_lines(code)

		tokens = extract_strings(tokens)
		for v in set(re.findall(r"<v\d*>", code)):
			unique = "var%d" % self.var_index
			self.var_index += 1
			code = code.replace(v, unique)

		def sub(match):
			return prefix_lines(tokens[int(match.group(2))], match.group(1))

		return re.sub(r"( *)<t(\d+)>", sub, code)

# Ideally we would like ``Node`` to be simply a subclass of ``list``. However,
# pyparsing does some automagic to results that are instances of ``list``.
# Since we don't want that we re-implement the desired functionality without
# subclassing ``list``.
class Node(collections.MutableSequence):
	"""
	Base class for nodes in the AST.

	Note that the class hierarchy of the node classes does *not* represent
	syntactical relationships in the corresponding Snowball code. Each node is a
	list, and the AST is represented via nested node lists.
	"""
	label = ''

	def __init__(self):
		self.children = []
		self.parent = None

	def __getitem__(self, index):
		return self.children[index]

	def __setitem__(self, index, value):
		self.children[index] = value
		value.parent = self

	def __delitem__(self, index):
		self.children[index].parent = None
		del self.children[index]

	def __len__(self):
		return len(self.children)

	def insert(self, index, value):
		self.children.insert(index, value)
		value.parent = self

	def generate_children_codes(self, env):
		"""
		Generate code for each child.

		``env`` is an instance of ``Environment``.

		Returns the code blocks generated by the children as a list.
		"""
		return [node.generate_code(env) for node in self]

	def generate_code(self, env):
		"""
		Generate code for this node.

		``env`` is an instance of ``Environment``.
		"""
		raise NotImplementedError('Must be implemented by subclasses.')

	def next_sibling(self):
		"""
		Return next sibling node in AST.
		"""
		siblings = self.parent.children
		try:
			return siblings[siblings.index(self) + 1]
		except IndexError:
			raise ValueError('Node has no next sibling.')

	def next(self):
		"""
		Return next node in AST, in depth-first order.
		"""
		try:
			return self.children[0]
		except IndexError:
			current = self
			while True:
				try:
					return current.next_sibling()
				except ValueError:
					pass
				if not current.parent:
					return None
				current = current.parent

	def to_xml(self):
		"""
		Returns an XML-like string representation of this node and its children.
		"""
		if len(self) == 0:
			return '<%s/>' % self.__class__.__name__
		result = ['<%s>' % self.__class__.__name__]
		for child in self:
			result.append(prefix_lines(child.to_xml(), ' '))
		result.append('</%s>' % self.__class__.__name__)
		return '\n'.join(result)

	def __repr__(self):
		content = ', '.join(repr(child) for child in self)
		return '%s(%s)' % (self.__class__.__name__, content)

	def __nonzero__(self):
		return True  # Even if no child nodes

	def annotate(self, s):
		"""
		Annotate string with class label.
		"""
		if not self.label:
			return s
		return annotate(s, ' ' + self.label, prefix='  ', first='##', middle='#', last='##', single='#')

class _PseudoCodeNode(Node):
	"""
	A node which generates code by transforming fixed strings of pseudo code.

	Subclasses should store the node's pseudo code in the ``code`` and
	``backwards_code`` attributes, respectively. See
	``Environment.transform_pseudo_code`` for details on the pseudo code format.
	"""
	code = ""
	backwards_code = None

	def generate_code(self, env):
		if env.direction == 1 or self.backwards_code is None:
			code = self.code
		else:
			code = self.backwards_code
		code = env.transform_pseudo_code(code, self.generate_children_codes(env))
		return self.annotate(code)

class NotNode(_PseudoCodeNode):
	label = 'not'
	code = """
<v> = s.cursor
<t0>
if not r:
  s.cursor = <v>
r = not r
"""

class TestNode(_PseudoCodeNode):
	label = 'test'
	code = """
<v> = s.cursor
<t0>
s.cursor = <v>
"""

class TryNode(_PseudoCodeNode):
	label = 'try'
	code = """
<v> = s.cursor
<t0>
if not r:
  r = True
  s.cursor = <v>
"""

class DoNode(_PseudoCodeNode):
	label = 'do'
	code = """
<v> = s.cursor
<t0>
s.cursor = <v>
r = True
"""
	backwards_code = """
<v> = len(s) - s.cursor
<t0>
s.cursor = len(s) - <v>
r = True
"""

class FailNode(_PseudoCodeNode):
	label = 'fail'
	code = """
<t0>
r = False
"""

class GoToNode(_PseudoCodeNode):
	label = 'goto'
	code = """
while True:
  <v> = s.cursor
  <t0>
  if r or s.cursor == s.limit:
    s.cursor = <v>
    break
  s.cursor = <v> + 1
"""
	backwards_code = """
while True:
  <v> = s.cursor
  <t0>
  if r or s.cursor == s.limit:
    s.cursor = <v>
    break
  s.cursor = <v> - 1
"""

class GoPastNode(_PseudoCodeNode):
	label = 'gopast'
	code = """
while True:
  <t0>
  if r or s.cursor == s.limit:
    break
  s.cursor += 1
"""
	backwards_code = """
while True:
  <t0>
  if r or s.cursor == s.limit:
    break
  s.cursor -= 1
"""

class RepeatNode(_PseudoCodeNode):
	label = 'repeat'
	code = """
while True:
  <v> = s.cursor
  <t0>
  if not r:
    s.cursor = <v>
    break
r = True
"""

class LoopNode(_PseudoCodeNode):
	label = 'loop'
	code = """
for <v> in xrange(<t0>):
  <t1>
"""

class AtLeastNode(_PseudoCodeNode):
	label = 'atleast'
	code = """
for <v> in xrange(<t0>):
  <t1>
while True:
  <v> = s.cursor
  <t1>
  if not r:
    s.cursor = <v>
    break
r = True
"""

class BackwardsNode(_PseudoCodeNode):
	label = 'backwards'
	code = """
<v0> = s.cursor
<v1> = len(s) - s.limit
s.direction *= -1
s.cursor, s.limit = s.limit, s.cursor
<t0>
s.direction *= -1
s.cursor = <v0>
s.limit = len(s) - <v1>
"""

	def generate_code(self, env):
		env.direction *= -1
		code = super(BackwardsNode, self).generate_code(env)
		env.direction *= -1
		return code

def _generate_substring_code(env, index):
	code = """
a_%d = None
r = False
for <v1>, <v2>, <v3> in _a_%d:
  if s.starts_with(<v1>) and ((not <v2>) or getattr(self, <v2>)(s)):
    a_%d = <v3>
    r = True
    break
""" % (index, index, index)
	return env.transform_pseudo_code(code, [])

def _make_if_chain(blocks):
	"""
	Chain code blocks together, check if ``r`` is true between them.
	"""
	code = [blocks[0]]
	prefix = ''
	for block in blocks[1:]:
		code.append(prefix + 'if r:')
		prefix += '  '
		code.append(prefix_lines(block, prefix))
	return '\n'.join(code)

class SubstringNode(Node):
	label = 'substring'
	def generate_code(self, env):
		among_index = env.claim_among_index()
		current = self.next()
		while not isinstance(current, AmongNode):
			current = current.next()
		current.among_index = among_index
		return self.annotate(_generate_substring_code(env, among_index))

class AmongNode(Node):
	label = 'among'

	def __init__(self, strings, commands, common_cmd=None):
		"""
		Constructor.

		``strings`` is a list of tuples. Each tuple contains a search string, its
		routine name (may be empty) and the string's command index. ``commands`` is
		the corresponding list of command nodes.

		``common_cmd`` can be a command node and represents the extended ``among``
		syntax::

		    among ( (C1) 'foo' (C2) 'bar' (C3))

		Here, ``C1`` is the common command.
		"""
		super(AmongNode, self).__init__()
		self.among_index = None
		self.strings = strings
		self.commands = commands
		self.common_cmd = common_cmd

	def generate_var(self):
		code = []
		for s in self.strings:
			routine = 'r_' + s[1] if s[1] else ''
			code.append("(%r, '%s', %d)" % (s[0], routine, s[2]))
		return '_a_%d = (' % self.among_index + ', '.join(code) + ',)'

	def generate_if_chain(self, env):
		code = []
		for index, command in enumerate(self.commands):
			if command:
				command_code = command.generate_code(env)
			else:
				command_code = 'r = True'
			command_code = prefix_lines(command_code, '  ')
			code.append('if a_%d == %d:\n' % (self.among_index, index) + command_code)
		return '\n'.join(code)

	def generate_code(self, env):
		blocks = []
		if self.among_index is None:
			self.among_index = env.claim_among_index()
			blocks.append(_generate_substring_code(env, self.among_index))
		env.module_code.append(self.generate_var())
		if self.common_cmd:
			blocks.append(self.common_cmd.generate_code(env))
		blocks.append(self.generate_if_chain(env))
		return self.annotate(_make_if_chain(blocks))

	def to_xml(self):
		cmds_xml = '\n'.join(cmd.to_xml() for cmd in self.commands if cmd)
		if cmds_xml:
			return "<AmongNode>\n%s\n</AmongNode>" % prefix_lines(cmds_xml, '  ')
		else:
			return "<AmongNode/>"

class InsertNode(_PseudoCodeNode):
	label = 'insert'
	code = """
r = s.insert(<t0>)
"""

class AttachNode(_PseudoCodeNode):
	label = 'attach'
	code = """
r = s.attach(<t0>)
"""

class ReplaceSliceNode(_PseudoCodeNode):
	label = '<-'
	code = """
r = s.set_range(self.left, self.right, <t0>)
"""

class ExportSliceNode(_PseudoCodeNode):
	label = '->'
	code = """
r = <t0>.set_chars(s.get_range(self.left, self.right))
"""

class HopNode(_PseudoCodeNode):
	label = 'hop'
	code = """
r = s.hop(<t0>)
"""

class NextNode(_PseudoCodeNode):
	label = 'next'
	code = """
r = s.hop(1)
"""

class SetLeftNode(_PseudoCodeNode):
	label = '['
	code = """
self.left = s.cursor
r = True
"""

class SetRightNode(_PseudoCodeNode):
	label = ']'
	code = """
self.right = s.cursor
r = True
"""

class SetMarkNode(_PseudoCodeNode):
	label = 'setmark'
	code = """
<t0> = s.cursor
r = True
"""

class ToMarkNode(_PseudoCodeNode):
	label = 'tomark'
	code = """
r = s.to_mark(<t0>)
"""

class AtMarkNode(_PseudoCodeNode):
	label = 'atmark'
	code = """
r = (s.cursor == <t0>)
"""

class SetNode(_PseudoCodeNode):
	label = 'set'
	code = """
<t0> = True
r = True
"""

class UnsetNode(_PseudoCodeNode):
	label = 'unset'
	code = """
<t0> = False
r = True
"""

class EmptyCommandNode(_PseudoCodeNode):
	code = """
pass
"""

class GroupingNode(_PseudoCodeNode):
	label = 'grouping check'
	code = """
if s.cursor == s.limit:
  r = False
else:
  r = s.chars[s.cursor] in <t0>
if r:
  s.cursor += 1
"""
	backwards_code = """
if s.cursor == s.limit:
  r = False
else:
  r = s.chars[s.cursor - 1] in <t0>
if r:
  s.cursor -= 1
"""

class NonNode(_PseudoCodeNode):
	label = 'negative grouping check'
	code = """
if s.cursor == s.limit:
  r = False
else:
  r = s.chars[s.cursor] not in <t0>
if r:
  s.cursor += 1
"""
	backwards_code = """
if s.cursor == s.limit:
  r = False
else:
  r = s.chars[s.cursor - 1] not in <t0>
if r:
  s.cursor -= 1
"""

class DeleteNode(_PseudoCodeNode):
	label = 'delete'
	code = """
r = s.set_range(self.left, self.right, u'')
"""

class AtLimitNode(_PseudoCodeNode):
	label = 'atlimit'
	code = """
r = (s.cursor == s.limit)
"""

class ToLimitNode(_PseudoCodeNode):
	label = 'tolimit'
	code = """
s.cursor = s.limit
r = True
"""

class StartsWithNode(_PseudoCodeNode):
	label = 'character check'
	code = """
r = s.starts_with(<t0>)
"""

class RoutineCallNode(_PseudoCodeNode):
	label = 'routine call'
	code = """
r = <t0>(s)
"""

class TrueCommandNode(_PseudoCodeNode):
	label = 'true'
	code = """
r = True
"""

class FalseCommandNode(_PseudoCodeNode):
	label = 'false'
	code = """
r = False
"""

class BooleanCommandNode(_PseudoCodeNode):
	label = 'boolean variable check'
	code = """
r = <t0>
"""

class SetLimitNode(_PseudoCodeNode):
	label = 'setlimit'
	code = """
<v0> = s.cursor
<v1> = len(s) - s.limit
<t0>
if r:
  s.limit = s.cursor
  s.cursor = <v0>
  <t1>
  s.limit = len(s) - <v1>
"""

class BackwardModeNode(Node):
	def generate_code(self, env):
		env.direction *= -1
		self.generate_children_codes(env)
		env.direction *= -1
		return ''

class RoutineDefinitionNode(Node):

	def __init__(self, name):
		super(RoutineDefinitionNode, self).__init__()
		self.name = name

	def generate_code(self, env):
		code = ['def r_%s(self, s):' % self.name, '  r = True']
		code.append(prefix_lines(self[0].generate_code(env), '  '))
		code.append('  return r')
		env.class_code.append('\n'.join(code))
		return ''

class CharSetNode(Node):

	def __init__(self, chars):
		super(CharSetNode, self).__init__()
		self.chars = chars

	def generate_code(self, env):
		return "set(%s)" % repr(self.chars)

class SetUnionNode(_PseudoCodeNode):
	code = '(<t0> | <t1>)'

class SetDifferenceNode(_PseudoCodeNode):
	code = '(<t0> - <t1>)'

class GroupingDefinitionNode(Node):
	def __init__(self, name):
		super(GroupingDefinitionNode, self).__init__()
		self.name = name

	def generate_code(self, env):
		code = '_g_%s = %s' % (self.name, self[0].generate_code(env))
		env.module_code.append(code)
		return ''

class ConcatenationNode(Node):
	def generate_code(self, env):
		return _make_if_chain(self.generate_children_codes(env))

class _IfChainNode(Node):
	not_str = ''
	def generate_code(self, env):
		lines = ['<v> = s.cursor', '<t0>']
		prefix = ''
		for t in range(1, len(self)):
			lines.append(prefix + 'if ' + self.not_str +'r:')
			prefix += '  '
			lines.append(prefix + 's.cursor = <v>')
			lines.append(prefix + '<t%d>' % t)
		code = '\n'.join(lines)
		code = env.transform_pseudo_code(code, self.generate_children_codes(env))
		return self.annotate(code)

class AndNode(_IfChainNode):
	label = 'and'

class OrNode(_IfChainNode):
	label = 'or'
	not_str = 'not '

class _ReferenceNode(Node):
	prefix = ''
	suffix = ''

	def __init__(self, name):
		super(_ReferenceNode, self).__init__()
		self.name = name

	def generate_code(self, env):
		return self.prefix + self.name + self.suffix

class StringReferenceNode(_ReferenceNode):
	prefix = 'self.s_'

class CharsReferenceNode(_ReferenceNode):
	prefix = 'self.s_'
	suffix = '.chars'

class IntegerReferenceNode(_ReferenceNode):
	prefix = 'self.i_'

class BooleanReferenceNode(_ReferenceNode):
	prefix = 'self.b_'

class RoutineReferenceNode(_ReferenceNode):
	prefix = 'self.r_'

class GroupingReferenceNode(_ReferenceNode):
	prefix = '_g_'

class StringLiteralNode(Node):

	def __init__(self, string):
		super(StringLiteralNode, self).__init__()
		self.string = string

	def generate_code(self, env):
		c = repr(self.string)
		if not c.startswith('u'):
			c = 'u' + c
		return c

class IntegerLiteralNode(Node):

	def __init__(self, integer):
		super(IntegerLiteralNode, self).__init__()
		self.integer = integer

	def generate_code(self, env):
		return str(self.integer)

class MaxIntNode(_PseudoCodeNode):
	code = 'sys.maxint'

class MinIntNode(_PseudoCodeNode):
	code = '(-sys.maxint - 1)'

class CursorNode(_PseudoCodeNode):
	code = 's.cursor'

class LimitNode(_PseudoCodeNode):
	code = 's.limit'

class SizeNode(_PseudoCodeNode):
	code = 'len(s)'

class SizeOfNode(_PseudoCodeNode):
	code = 'len(<t0>)'

class _ArithmeticOperationNode(Node):
	operator = ''
	use_brackets = False

	def generate_code(self, env):
		code = (' ' + self.operator + ' ').join(self.generate_children_codes(env))
		if self.use_brackets:
			code = '(' + code + ')'
		return code

class MultiplicationNode(_ArithmeticOperationNode):
	operator = '*'

class DivisionNode(_ArithmeticOperationNode):
	operator = '/'

class AdditionNode(_ArithmeticOperationNode):
	operator = '+'
	use_brackets = True

class SubtractionNode(_ArithmeticOperationNode):
	operator = '-'
	use_brackets = True

class NegationNode(_PseudoCodeNode):
	code = '(-<t0>)'

class IntegerAssignNode(_PseudoCodeNode):
	code = """
<t0> = <t1>
r = True
"""

class IntegerIncrementByNode(_PseudoCodeNode):
	label = '+='
	code = """
<t0> += <t1>
r = True
"""

class IntegerMultiplyByNode(_PseudoCodeNode):
	label = '*='
	code = """
<t0> *= <t1>
r = True
"""

class IntegerDecrementByNode(_PseudoCodeNode):
	label = '-='
	code = """
<t0> -= <t1>
r = True
"""

class IntegerDivideByNode(_PseudoCodeNode):
	label = '/='
	code = """
<t0> /= <t1>
r = True
"""

class IntegerEqualNode(_PseudoCodeNode):
	label = '=='
	code = """
r = <t0> == <t1>
"""

class IntegerGreaterNode(_PseudoCodeNode):
	label = '>'
	code = """
r = <t0> > <t1>
"""

class IntegerLessNode(_PseudoCodeNode):
	label = '<'
	code = """
r = <t0> < <t1>
"""

class IntegerUnequalNode(_PseudoCodeNode):
	label = '!='
	code = """
r = <t0> != <t1>
"""

class IntegerGreaterOrEqualNode(_PseudoCodeNode):
	label = '>='
	code = """
r = <t0> >= <t1>
"""

class IntegerLessOrEqualNode(_PseudoCodeNode):
	label = '<='
	code = """
r = <t0> <= <t1>
"""

class _InitDeclarationNode(Node):
	def __init__(self, name):
		super(_InitDeclarationNode, self).__init__()
		self.name = name

	def generate_code(self, env):
		env.init_code.append(self.template % self.name)
		return ''

class IntegerDeclarationNode(_InitDeclarationNode):
	template = 'self.i_%s = 0'

class StringDeclarationNode(_InitDeclarationNode):
	template = "self.s_%s = _String('')"

class BooleanDeclarationNode(_InitDeclarationNode):
	template = 'self.b_%s = True'

class BooleanDeclarationNode(_InitDeclarationNode):
	template = 'self.b_%s = True'

_FUNCTION_TEMPLATE = """
def %s(s):
  s = _String(s)
  _Program().r_%s(s)
  return unicode(s)
"""

_DEBUG_FUNCTION_TEMPLATE = """
def %s(s):
  p = _Program()
  s = _String(s)
  p.r_%s(s)
  return s, p
"""

class ExternalDeclarationNode(Node):
	def __init__(self, name):
		super(ExternalDeclarationNode, self).__init__()
		self.name = name

	def generate_code(self, env):
		template = _FUNCTION_TEMPLATE if not env.debug else _DEBUG_FUNCTION_TEMPLATE
		env.module_code.append(template % (self.name, self.name))
		return ''


class _NoOpDeclarationNode(Node):
	def __init__(self, name):
		super(_NoOpDeclarationNode, self).__init__()
		self.name = ''

	def generate_code(self, env):
		return ''

class RoutineDeclarationNode(_NoOpDeclarationNode):
	pass

class GroupingDeclarationNode(_NoOpDeclarationNode):
	pass


_MODULE_TEMPLATE = """#!/usr/bin/env python
# vim:fileencoding=utf-8

import sys

class _String(object):

  def __init__(self, s):
    self.chars = list(unicode(s))
    self.cursor = 0
    self.limit = len(s)
    self.direction = 1

  def __unicode__(self):
    return u''.join(self.chars)

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

%(module_code)s

class _Program(object):
  def __init__(self):
    self.left = None
    self.right = None
%(init_code)s

%(class_code)s
"""

class ProgramNode(Node):
	"""
	Root node representing a complete Snowball program.
	"""
	def generate_code(self, env):
		self.generate_children_codes(env)
		module_code = '\n'.join(env.module_code)
		init_code = prefix_lines('\n'.join(env.init_code), '    ')
		class_code = prefix_lines('\n\n'.join(env.class_code), '  ')
		return _MODULE_TEMPLATE % {
			'module_code':module_code,
			'init_code':init_code,
			'class_code':class_code,
		}
