#!/usr/bin/env python
# vim:fileencoding=utf8

# Copyright (c) 2014 Florian Brucker
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Snowball grammar and parser for sbl2py.
"""

import functools
import inspect
import sys
import threading

from pyparsing import *

from sbl2py.ast import *


__all__ = ['parse_string']


# Grammar elements are in all-caps.


ParserElement.enablePackrat()


#
# PARSER STATE
#

state = threading.local()
state.strings = []        # Declared string names
state.integers = []       # Declared integer names
state.externals = []      # Declared externals names
state.booleans = []       # Declared boolean names
state.routines = []       # Declared routine names
state.groupings = []      # Declared grouping names
state.stringescapes = []  # Left and right string escape chars
state.stringdefs = {}     # String replacement definitions

def reset():
    """
    Reset internal parser state.
    """
    state.strings[:] = []
    state.integers[:] = []
    state.externals[:] = []
    state.booleans[:] = []
    state.routines[:] = []
    state.groupings[:] = []
    state.stringescapes[:] = []
    state.stringdefs.clear()


#
# UTILITY FUNCTIONS
#

def parse_action(f):
    """
    Decorator for pyparsing parse actions to ease debugging.

    pyparsing uses trial & error to deduce the number of arguments a
    parse action accepts. Unfortunately any ``TypeError`` raised by a
    parse action confuses that mechanism.

    This decorator replaces the trial & error mechanism with one based
    on reflection. If the decorated function itself raises a
    ``TypeError`` then that exception is re-raised if the wrapper is
    called with less arguments than required. This makes sure that the
    actual ``TypeError`` bubbles up from the call to the parse action
    (instead of the one caused by pyparsing's trial & error).
    """
    num_args = len(inspect.getargspec(f).args)
    if num_args > 3:
        raise ValueError('Input function must take at most 3 parameters.')

    @functools.wraps(f)
    def action(*args):
        if len(args) < num_args:
            if action.exc_info:
                raise (action.exc_info[0], action.exc_info[1],
                       action.exc_info[2])
        action.exc_info = None
        try:
            v = f(*args[:-(num_args + 1):-1])
            return v
        except TypeError as e:
            action.exc_info = sys.exc_info()
            raise

    action.exc = None
    return action


def make_node_action(cls, ungroup=False, init_args=0):
    @parse_action
    def action(tokens):
        if ungroup:
            tokens = tokens[0]
        node = cls(*tokens[:init_args])
        node.extend(tokens[init_args:])
        return node
    return action


def add_node_action(pattern, *args, **kwargs):
    pattern.addParseAction(make_node_action(*args, **kwargs))
    return pattern


def make_binary_op_list_action(operators, classes, ungroup=False):
    """
    Make parse action for lists of binary operators and operands.

    ``operators`` is a list of the operators (as strings) and
    ``classes`` is a list of the corresponding ``Node`` subclasses.
    """
    @parse_action
    def action(tokens):
        if ungroup:
            tokens = tokens[0]
        tokens = list(reversed(tokens))
        left = tokens.pop()
        while tokens:
            token = tokens.pop()
            for op, cls in zip(operators, classes):
                if token == op:
                    node = cls()
                    break
            node.append(left)
            node.append(tokens.pop())
            left = node
        return node

    return action

LPAREN = Suppress('(')
RPAREN = Suppress(')')


#
# KEYWORDS
#

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

KEYWORD = MatchFirst(keywords)


#
# NAMES
#

NAME = ~KEYWORD + Word(alphas, alphanums + '_')
NAME.setParseAction(parse_action(lambda t: t[0]))


#
# DECLARATIONS
#

def make_decl(kw, targets, cls):
    declaration = Suppress(kw) + LPAREN + ZeroOrMore(NAME) + RPAREN

    @parse_action
    def action(tokens):
        for target in targets:
            target.extend(tokens)
        return [cls(t) for t in tokens]

    declaration.setParseAction(action)
    return declaration

DECLARATION = MatchFirst([
    make_decl(STRINGS, [state.strings], StringDeclarationNode),
    make_decl(INTEGERS, [state.integers], IntegerDeclarationNode),
    make_decl(BOOLEANS, [state.booleans], BooleanDeclarationNode),
    make_decl(ROUTINES, [state.routines], RoutineDeclarationNode),
    make_decl(EXTERNALS, [state.externals, state.routines],
              ExternalDeclarationNode),
    make_decl(GROUPINGS, [state.groupings], GroupingDeclarationNode),
])


#
# REFERENCES
#

reference_chars = set(alphanums + '_')

class Reference(Token):
    """
    A reference to a previously declared variable.

    This class works like pyparsing's ``Or`` in combination with
    ``Keyword``. However, the list of candidates can be updated later
    on.
    """

    def __init__(self, declarations):
        """
        Constructor.

        ``declarations`` is a list of previously declared variables.
        Any of them will match if they occur as a separate word (cf.
        ``Keyword``). Matching is done in decreasing length of
        candidates (cf. ``Or``). Later updates of ``declarations``
        are taken into account.
        """
        super(Reference, self).__init__()
        self.declarations = declarations

    def __str__(self):
        return 'Reference(%s)' % self.declarations

    def parseImpl(self, instring, loc, doActions=True):
        candidates = sorted(self.declarations, key=lambda x: len(x),
                            reverse=True)
        for candidate in candidates:
            if instring.startswith(candidate, loc):
                n = len(candidate)
                if (len(instring) == loc + n or instring[loc + n] not in
                        reference_chars):
                    return loc + n, candidate
        raise ParseException("Expected one of " + ", ".join(candidates))


def make_reference(declarations, cls):
    pattern = Reference(declarations)
    pattern.setParseAction(parse_action(lambda t: cls(t[0])))
    return pattern

STR_REF = make_reference(state.strings, StringReferenceNode)
CHARS_REF = make_reference(state.strings, CharsReferenceNode)
GROUPING_REF = make_reference(state.groupings, GroupingReferenceNode)
INT_REF = make_reference(state.integers, IntegerReferenceNode)
BOOLEAN_REF = make_reference(state.booleans, BooleanReferenceNode)
ROUTINE_REF = make_reference(state.routines, RoutineReferenceNode)


#
# STRINGS
#

class StringLiteral(Token):
    """
    String literal that supports dynamically changing escape characters.
    """

    def __init__(self, escape_chars, replacements):
        """
        Constructor.

        ``escape_chars`` is a list containing either two or no
        characters. These characters are the left and right escape
        marker, respectively. You may change the content of the list
        afterwards, the parsing code always uses the latest values.

        ``replacements`` is a dict that maps escape sequences to their
        replacements. Later modifications are taken into account.
        """
        super(StringLiteral, self).__init__()
        self.escape_chars = escape_chars
        self.replacements = replacements

    def __str__(self):
        if self.escape_chars:
            return 'StringLiteral("%s%s")' % tuple(self.escape_chars)
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
        return candidate + 1, unicode(s)



@parse_action
def stringescapes_cmd_action(tokens):
    state.stringescapes[:] = tokens[0] + tokens[1]
    state.stringdefs["'"] = "'"
    state.stringdefs['['] = '['
    return []

@parse_action
def stringdef_cmd_action(tokens):
    key = tokens[0]
    mode = tokens[1]
    value = tokens[2].string
    if mode == 'hex':
        value = u''.join(unichr(int(x, 16)) for x in value.split())
    elif mode == 'decimal':
        value = u''.join(unichr(int(x)) for x in value.split())
    state.stringdefs[key] = value
    return []

STR_LITERAL = StringLiteral(state.stringescapes, state.stringdefs)
STR_LITERAL.setParseAction(parse_action(lambda t: StringLiteralNode(t[0])))

CHAR = Word(printables, exact=1)
STRINGESCAPES_CMD = Suppress(STRINGESCAPES) + CHAR + CHAR
STRINGESCAPES_CMD.setParseAction(stringescapes_cmd_action)

STRINGDEF_CMD = (Suppress(STRINGDEF) + Word(printables) +
                 Optional(HEX | DECIMAL, default=None) + STR_LITERAL)
STRINGDEF_CMD.setParseAction(stringdef_cmd_action)

# A sequence of characters
CHARS = STR_LITERAL | CHARS_REF


#
# INTEGERS
#

@parse_action
def int_literal_action(tokens):
    return IntegerLiteralNode(int(tokens[0]))

INT_LITERAL = Word(nums)
INT_LITERAL.setParseAction(int_literal_action)

INT = INT_REF | INT_LITERAL


#
# ARITHMETIC EXPRESSIONS
#

EXPRESSION_OPERAND = MatchFirst([
    add_node_action(Suppress(MAXINT), MaxIntNode),
    add_node_action(Suppress(MININT), MinIntNode),
    add_node_action(Suppress(CURSOR), CursorNode),
    add_node_action(Suppress(LIMIT), LimitNode),
    add_node_action(Suppress(SIZEOF) + STR_REF, SizeOfNode),
    add_node_action(Suppress(SIZE), SizeNode),
    INT,
])

negation_action =  make_node_action(NegationNode, ungroup=True)
multiplicative_action = make_binary_op_list_action(
        ['*', '/'], [MultiplicationNode, DivisionNode])
additive_action = make_binary_op_list_action(
        ['+', '-'], [AdditionNode, SubtractionNode])

EXPRESSION = operatorPrecedence(
    EXPRESSION_OPERAND,
    [
        (Suppress('-'), 1, opAssoc.RIGHT,negation_action),
        (oneOf('* /'), 2, opAssoc.LEFT, multiplicative_action),
        (oneOf('+ -'), 2, opAssoc.LEFT, additive_action),
    ]
)


#
# INTEGER COMMANDS
#

def make_int_cmd(op, cls):
    VAR = Suppress('$') + INT_REF
    # We're not using ``Combine`` here because ``Combine`` automatically
    # converts the result to a string.
    VAR.leaveWhitespace()
    return add_node_action(VAR + Suppress(op) + EXPRESSION, cls)

INT_CMD = MatchFirst([
    make_int_cmd('+=', IntegerIncrementByNode),
    make_int_cmd('*=', IntegerMultiplyByNode),
    make_int_cmd('-=', IntegerDecrementByNode),
    make_int_cmd('/=', IntegerDivideByNode),
    make_int_cmd('==', IntegerEqualNode),
    make_int_cmd('!=', IntegerUnequalNode),
    make_int_cmd('>=', IntegerGreaterOrEqualNode),
    make_int_cmd('<=', IntegerLessOrEqualNode),
    make_int_cmd('=', IntegerAssignNode),
    make_int_cmd('>', IntegerGreaterNode),
    make_int_cmd('<', IntegerLessNode),
])


#
# STRING COMMANDS
#


STR_CMD = Forward()

UNARY_OPERATOR = (NOT | TEST | TRY | DO | FAIL | GOTO | GOPAST | REPEAT |
                  BACKWARDS | (LOOP + EXPRESSION) | (ATLEAST + EXPRESSION))

not_action = make_node_action(NotNode)
test_action = make_node_action(TestNode)
try_action = make_node_action(TryNode)
do_action = make_node_action(DoNode)
fail_action = make_node_action(FailNode)
goto_action = make_node_action(GoToNode)
gopast_action = make_node_action(GoPastNode)
repeat_action = make_node_action(RepeatNode)
loop_action = make_node_action(LoopNode)
atleast_action = make_node_action(AtLeastNode)
backwards_action = make_node_action(BackwardsNode)

unary_actions = {
    'not':not_action,
    'test':test_action,
    'try':try_action,
    'do':do_action,
    'fail':fail_action,
    'goto':goto_action,
    'gopast':gopast_action,
    'repeat':repeat_action,
    'loop':loop_action,
    'atleast':atleast_action,
    'backwards':backwards_action,
}

@parse_action
def unary_action(tokens):
    return unary_actions[tokens[0][0]](tokens[0][1:])

CMD_INSERT = add_node_action(Suppress(INSERT | '<+') + CHARS, InsertNode)
CMD_ATTACH = add_node_action(Suppress(ATTACH) + CHARS, AttachNode)
CMD_REPLACE_SLICE = add_node_action(Suppress('<-') + CHARS, ReplaceSliceNode)
CMD_EXPORT_SLICE = add_node_action(Suppress('->') + STR_REF, ExportSliceNode)
CMD_HOP = add_node_action(Suppress(HOP) + EXPRESSION, HopNode)
CMD_NEXT = add_node_action(Suppress(NEXT), NextNode)
CMD_SET_LEFT = add_node_action(Suppress('['), SetLeftNode)
CMD_SET_RIGHT = add_node_action(Suppress(']'), SetRightNode)
CMD_SETMARK = add_node_action(Suppress(SETMARK) + INT_REF, SetMarkNode)
CMD_TOMARK = add_node_action(Suppress(TOMARK) + EXPRESSION, ToMarkNode)
CMD_ATMARK = add_node_action(Suppress(ATMARK) + EXPRESSION, AtMarkNode)
CMD_SET = add_node_action(Suppress(SET) + BOOLEAN_REF, SetNode)
CMD_UNSET = add_node_action(Suppress(UNSET) + BOOLEAN_REF, UnsetNode)
CMD_GROUPING = add_node_action(GROUPING_REF.copy(), GroupingNode)
CMD_NON = add_node_action(Suppress(NON + Optional('-')) + GROUPING_REF, NonNode)
CMD_DELETE = add_node_action(Suppress(DELETE), DeleteNode)
CMD_ATLIMIT = add_node_action(Suppress(ATLIMIT), AtLimitNode)
CMD_TOLIMIT = add_node_action(Suppress(TOLIMIT), ToLimitNode)
CMD_STARTSWITH = add_node_action(CHARS.copy(), StartsWithNode)
CMD_ROUTINE = add_node_action(ROUTINE_REF.copy(), RoutineCallNode)
CMD_TRUE = add_node_action(Suppress(TRUE), TrueCommandNode)
CMD_FALSE = add_node_action(Suppress(FALSE), FalseCommandNode)
CMD_BOOLEAN = add_node_action(BOOLEAN_REF.copy(), BooleanCommandNode)
CMD_SUBSTRING = add_node_action(Suppress(SUBSTRING), SubstringNode)
CMD_SETLIMIT = add_node_action(
        Suppress(SETLIMIT) + STR_CMD + Suppress(FOR) + LPAREN + STR_CMD +
        RPAREN, SetLimitNode)
CMD_EMPTY = add_node_action(LPAREN + RPAREN, EmptyCommandNode)

@parse_action
def cmd_among_action(tokens):
    common_cmd, tokens = tokens
    strings = []
    for index, arg in enumerate(tokens):
        for element in arg[0]:
            string = element[0].string
            routine = element[1].name if element[1] else ''
            strings.append((string, routine, index))
    strings.sort(cmp=lambda x, y: len(y[0]) - len(x[0])) # by decreasing length
    commands = [arg[1] for arg in tokens]
    return AmongNode(strings, commands, common_cmd=common_cmd)

AMONG_STR = Group(STR_LITERAL + Optional(ROUTINE_REF, default=None))
AMONG_CMD_ARG = Optional((LPAREN + STR_CMD + RPAREN | CMD_EMPTY), default=None)
AMONG_ARG = Group(Group(OneOrMore(AMONG_STR)) + AMONG_CMD_ARG)
CMD_AMONG = (Suppress(AMONG) + LPAREN + AMONG_CMD_ARG +
        Group(OneOrMore(AMONG_ARG)) + RPAREN)
CMD_AMONG.setParseAction(cmd_among_action)

STR_CMD_OPERAND = (INT_CMD | CMD_STARTSWITH | CMD_SETLIMIT | CMD_INSERT |
                   CMD_ATTACH | CMD_REPLACE_SLICE | CMD_DELETE | CMD_HOP |
                   CMD_NEXT | CMD_SET_LEFT | CMD_SET_RIGHT | CMD_EMPTY |
                   CMD_EXPORT_SLICE | CMD_SETMARK | CMD_TOMARK | CMD_ATMARK |
                   CMD_TOLIMIT | CMD_ATLIMIT | CMD_SET | CMD_UNSET |
                   CMD_SUBSTRING | CMD_AMONG | CMD_ROUTINE | CMD_GROUPING |
                   CMD_NON | CMD_TRUE | CMD_FALSE | CMD_BOOLEAN)

concatenation_action = make_node_action(ConcatenationNode, ungroup=True)
and_or_action = make_binary_op_list_action(
        ['and', 'or'], [AndNode, OrNode], ungroup=True)

STR_CMD << operatorPrecedence(
    STR_CMD_OPERAND,
    [
        (UNARY_OPERATOR, 1, opAssoc.RIGHT, unary_action),
        (AND | OR, 2, opAssoc.LEFT, and_or_action),
        (Empty(), 2, opAssoc.LEFT, concatenation_action),
    ]
)


#
# ROUTINES
#

@parse_action
def routine_def_action(tokens):
    node = RoutineDefinitionNode(tokens[0].name)
    node.append(tokens[1])
    return node

ROUTINE_DEF = Suppress(DEFINE) + ROUTINE_REF + Suppress(AS) + STR_CMD
ROUTINE_DEF.setParseAction(routine_def_action)


#
# GROUPINGS
#

@parse_action
def grouping_def_action(tokens):
    tokens = list(reversed(tokens))
    node = GroupingDefinitionNode(tokens.pop().name)
    if not tokens:
        return node
    elif len(tokens) == 1:
        node.append(tokens.pop())
        return node
    left = tokens.pop()
    while tokens:
        child = SetUnionNode() if tokens.pop() == '+' else SetDifferenceNode()
        child.append(left)
        child.append(tokens.pop())
        left = child
    node.append(child)
    return node

@parse_action
def char_set_action(tokens):
    return CharSetNode(tokens[0].string)

CHAR_SET = STR_LITERAL.copy().addParseAction(char_set_action)
GROUPING_ATOM = GROUPING_REF | CHAR_SET
GROUPING_DEF = (Suppress(DEFINE) + GROUPING_REF + GROUPING_ATOM +
                ZeroOrMore(oneOf('+ -') + GROUPING_ATOM))
GROUPING_DEF.setParseAction(grouping_def_action)


#
# PROGRAM
#

PROGRAM_ATOM = (DECLARATION | ROUTINE_DEF | GROUPING_DEF | STRINGESCAPES_CMD |
                STRINGDEF_CMD)
BACKWARD_SECTION = add_node_action(
        Suppress(BACKWARDMODE) + LPAREN + ZeroOrMore(PROGRAM_ATOM) + RPAREN,
        BackwardModeNode)
PROGRAM = add_node_action(
        ZeroOrMore(PROGRAM_ATOM | BACKWARD_SECTION) + StringEnd(), ProgramNode)
PROGRAM.ignore(cStyleComment | dblSlashComment)


#
# PUBLIC INTERFACE
#

def parse_string(s):
    """
    Parse string containing Snowball code.

    Returns the corresponding AST.
    """
    reset()
    return PROGRAM.parseString(s)[0]
