#!/usr/bin/env python
# vim:fileencoding=utf8

"""
Tests for ``sbl2py``.
"""

# These tests are intended to be run via the nose framework.

import codecs
import glob
import os.path
import unittest
import sys

from nose.plugins.attrib import attr

_module_dir = os.path.dirname(__file__)
sys.path.append(os.path.abspath(os.path.join(_module_dir, '..', 'src')))
import sbl2py
from sbl2py.utils import add_line_numbers, module_from_code


#######################################################################
# TESTS FOR INDIVIDUAL SNOWBALL FEATURES                              #
#######################################################################

def assert_snowball(code, tests, routine='check'):
	"""
	Test that compiling and executing a piece of Snowball code works.

	``code`` is automatically prefixed with an externals declaration for the
	given routine name.

	``tests`` is a sequence of test cases. Each test case is a sequence which
	contains at least the test input and expected output. The test case may
	also contain dicts of expected attribute values for the attributes of the
	``_String`` and ``_Program`` instances.
	"""
	code = ("externals (%s)\n" % routine) + code

	try:
		pycode = sbl2py.translate_string(code, debug=True)
	except Exception as e:
		print "Could not translate the following Snowball code:\n\n" + add_line_numbers(code)
		raise

	def msg(s):
		return s + "\n\nSnowball code:\n\n" + add_line_numbers(code) + "\n\nPython code:\n\n" + add_line_numbers(pycode)

	try:
		module = module_from_code('sbl2py_testmodule', pycode)
	except SyntaxError as e:
		print msg("Generated code is invalid: %s" % e)
		raise

	fun = getattr(module, routine)

	for test in tests:
		string = test[0]
		expected = test[1]
		s_attrs = test[2] if len(test) > 2 else {}
		p_attrs = test[3] if len(test) > 3 else {}

		try:
			output, program = fun(string)
		except Exception as e:
			print msg("Running routine '%s' failed: %s" % (routine, e))
			raise

		assert unicode(output) == expected, msg(
				"Wrong output for '%s': Expected '%s', got '%s'." % (string, expected,
				output))
		for attr, exp_value in s_attrs.iteritems():
			value = getattr(output, attr)
			assert value == exp_value, msg(
					"Wrong value for string attribute '%s': Expected '%s', got '%s'. Input was '%s', output was '%s'." %
					(attr, exp_value, value, string, output))
		for attr, exp_value in p_attrs.iteritems():
			value = getattr(program, attr)
			assert value == exp_value, msg(
					"Wrong value for program attribute '%s': Expected '%s', got '%s'. Input was '%s', output was '%s'." %
					(attr, exp_value, value, string, output))

def test_starts_with():
	assert_snowball(
		"""
		define check as 'foo'
		""",
		(
			('foo', 'foo', {'cursor':3}),
			('f', 'f', {'cursor':0}),
			('fo', 'fo', {'cursor':0}),
			('bar', 'bar', {'cursor':0}),
			('xfoo', 'xfoo', {'cursor':0}),
			('Foo', 'Foo', {'cursor':0}),
			('', '', {'cursor':0}),
			('fooo', 'fooo', {'cursor':3}),
		)
	)
	assert_snowball(
		"""
		define check as backwards ('bar' 'foo' <+ 'x')
		""",
		(
			('foobar', 'xfoobar'),
			('barbar', 'barbar'),
		)
	)

def test_or():
	assert_snowball(
		"""
		define check as ('foo' or 'Fo' or 'F')
		""",
		(
			('foo', 'foo', {'cursor':3}),
			('Fo', 'Fo', {'cursor':2}),
			('F', 'F', {'cursor':1}),
			('bar', 'bar', {'cursor':0}),
		)
	)

def test_and():
	assert_snowball(
		"""
		define check as ('f' and 'fo' and 'foo')
		""",
		(
			('foo', 'foo', {'cursor':3}),
			('bar', 'bar', {'cursor':0}),
			('fox', 'fox', {'cursor':0}),
		)
	)

def test_not():
	assert_snowball(
		"""
		define check as (not 'foo')
		""",
		(
			('foo', 'foo', {'cursor':3}),
			('fox', 'fox', {'cursor':0}),
		)
	)

def test_try():
	assert_snowball(
		"""
		define check as (try 'foo' 'bar')
		""",
		(
			('foo', 'foo', {'cursor':3}),
			('bar', 'bar', {'cursor':3}),
			('foobar', 'foobar', {'cursor':6}),
		)
	)

def test_test():
	assert_snowball(
		"""
		define check as (test 'foo' 'fo')
		""",
		(
			('foo', 'foo', {'cursor':2}),
			('fox', 'fox', {'cursor':0}),
			('bar', 'bar', {'cursor':0}),
		)
	)

def test_fail():
	assert_snowball(
		"""
		define check as ((fail true) or 'foo')
		""",
		(
			('foo', 'foo', {'cursor':3}),
		)
	)

def test_do():
	assert_snowball(
		"""
		define check as (do 'foo' 'fo')
		""",
		(
			('foo', 'foo', {'cursor':2}),
			('fo', 'fo', {'cursor':2}),
		)
	)

def test_goto():
	assert_snowball(
		"""
		define check as ((goto 'x') or 'foo')
		""",
		(
			('fox', 'fox', {'cursor':2}),
			('foox', 'foox', {'cursor':3}),
			('foobar', 'foobar', {'cursor':3}),
		)
	)
	assert_snowball(
		"""
		define check as backwards ((goto 'x') or 'foo' <+ 'y')
		""",
		(
			('xofoo', 'xyofoo'),
			('ofoo', 'oyfoo'),
		)
	)

def test_gopast():
	assert_snowball(
		"""
		define check as ((gopast 'x') or 'foo')
		""",
		(
			('fox', 'fox', {'cursor':3}),
			('foox', 'foox', {'cursor':4}),
			('foobar', 'foobar', {'cursor':3}),
		)
	)
	assert_snowball(
		"""
		define check as backwards ((gopast 'x') or 'foo' <+ 'y')
		""",
		(
			('xofoo', 'yxofoo'),
			('ofoo', 'oyfoo'),
		)
	)

def test_repeat():
	assert_snowball(
			"""
			define check as ((repeat 'x') or 'foo')
			""",
			(
				('xxxfoo', 'xxxfoo', {'cursor':3}),
				('xxa', 'xxa', {'cursor':2}),
				('foo', 'foo', {'cursor':0}),
			)
		)

def test_loop():
	assert_snowball(
		"""
		define check as (loop 2 'x')
		""",
		(
			('xxy', 'xxy', {'cursor':2}),
		)
	)

def test_atleast():
	assert_snowball(
		"""
		define check as (atleast 2 'x')
		""",
		(
			('xxy', 'xxy', {'cursor':2}),
			('xxxxy', 'xxxxy', {'cursor':4}),
		)
	)

def test_hop():
	assert_snowball(
		"""
		define check as (hop 2 or 'f')
		""",
		(
			('foo', 'foo', {'cursor':2}),
			('f', 'f', {'cursor':1}),
		)
	)
	assert_snowball(
		"""
		define check as (hop -2 or 'f')
		""",
		(
			('f', 'f', {'cursor':1}),
		)
	)
	assert_snowball(
		"""
		define check as backwards (hop 2 <+ 'x')
		""",
		(
			('foo', 'fxoo'),
			('f', 'f'),
		)
	)
	assert_snowball(
		"""
		define check as backwards (hop -2 <+ 'x')
		""",
		(
			('f', 'f'),
		)
	)

def test_next():
	assert_snowball(
		"""
		define check as next
		""",
		(
			('foo', 'foo', {'cursor':1}),
			('bar', 'bar', {'cursor':1}),
			('', '', {'cursor':0}),
		)
	)
	assert_snowball(
		"""
		define check as backwards (next <+ 'x')
		""",
		(
			('foo', 'foxo'),
			('bar', 'baxr'),
			('', ''),
		)
	)

def test_left():
	assert_snowball(
		"""
		define check as (try 'f' [)
		""",
		(
			('f', 'f', {}, {'left':1}),
			('g', 'g', {}, {'left':0}),
		)
	)

def test_right():
	assert_snowball(
		"""
		define check as (try 'f' ])
		""",
		(
			('f', 'f', {}, {'right':1}),
			('g', 'g', {}, {'right':0}),
		)
	)

def test_replace_slice():
	assert_snowball(
		"""
		define check as ('f' [try 'o'] <- 'u')
		""",
		(
			('foo', 'fuo', {'cursor':2, 'limit':3}),
			('faa', 'fuaa', {'cursor':2, 'limit':4}),
		)
	)
	assert_snowball(
		"""
		integers (c l)
		define check as backwards ('f' [try 'alo'] <- 'xy' $c = cursor $l = limit)
		""",
		(
			('galof', 'gxyf', {}, {'i_c':1, 'i_l':0}),
			('gf', 'gxyf', {}, {'i_c':1, 'i_l':0}),
		)
	)

def test_move_slice():
	assert_snowball(
		"""
		strings (s)
		define check as (['foo'] -> s ['bar'] <- s)
		""",
		(
			('foobar', 'foofoo'),
		)
	)
	assert_snowball(
		"""
		strings (s)
		define check as backwards (['foo'] -> s ['bar'] <- s)
		""",
		(
			('barfoo', 'foofoo'),
		)
	)

def test_delete():
	assert_snowball(
		"""
		define check as (['foo'] delete)
		""",
		(
			('foo', ''),
			('foobar', 'bar'),
		)
	)

def test_insert():
	assert_snowball(
		"""
		define check as ('foo' insert 'bar')
		""",
		(
			('fooqux', 'foobarqux', {'cursor':6, 'limit':9}),
		)
	)
	assert_snowball(
		"""
		define check as ('foo' <+ 'bar')
		""",
		(
			('fooqux', 'foobarqux', {'cursor':6, 'limit':9}),
		)
	)
	assert_snowball(
		"""
		strings (s)
		define check as (['foo'] -> s insert s)
		""",
		(
			('foo', 'foofoo', {'cursor':6, 'limit':6}),
		)
	)
	assert_snowball(
		"""
		strings (s)
		define check as (['foo'] -> s <+ s)
		""",
		(
			('foo', 'foofoo', {'cursor':6, 'limit':6}),
		)
	)
	assert_snowball(
		"""
		integers (c l)
		define check as backwards ('foo' insert 'bar' $c = cursor $l = limit)
		""",
		(
			('quxfoo', 'quxbarfoo', {}, {'i_c':3, 'i_l':0}),
		)
	)
	assert_snowball(
		"""
		integers (c l)
		define check as backwards ('foo' <+ 'bar' $c = cursor $l = limit)
		""",
		(
			('quxfoo', 'quxbarfoo', {}, {'i_c':3, 'i_l':0}),
		)
	)
	assert_snowball(
		"""
		strings (s)
		integers (c l)
		define check as backwards (['foo'] -> s insert s $c = cursor $l = limit)
		""",
		(
			('foo', 'foofoo', {}, {'i_c':0, 'i_l':0}),
		)
	)
	assert_snowball(
		"""
		strings (s)
		integers (c l)
		define check as backwards (['foo'] -> s <+ s $c = cursor $l = limit)
		""",
		(
			('foo', 'foofoo', {}, {'i_c':0, 'i_l':0}),
		)
	)

def test_attach():
	assert_snowball(
		"""
		define check as ('foo' attach 'bar')
		""",
		(
			('fooqux', 'foobarqux', {'cursor':3, 'limit':9}),
		)
	)
	assert_snowball(
		"""
		integers (c l)
		define check as backwards ('foo' attach 'bar' $c = cursor $l = limit)
		""",
		(
			('foo', 'barfoo', {}, {'i_c':3, 'i_l':0}),
		)
	)

def test_setmark():
	assert_snowball(
		"""
		integers (i)
		define check as (try 'foo' setmark i)
		""",
		(
			('foo', 'foo', {}, {'i_i':3}),
			('bar', 'bar', {}, {'i_i':0}),
		)
	)

def test_tomark():
	assert_snowball(
		"""
		define check as (tomark 2 or 'x')
		""",
		(
			('xo', 'xo', {'cursor':2}),
			('x', 'x', {'cursor':1}),
		)
	)
	assert_snowball(
		"""
		define check as (tomark -2 or 'x')
		""",
		(
			('o', 'o', {'cursor':0}),
			('x', 'x', {'cursor':1}),
		)
	)
	assert_snowball(
		"""
		define check as backwards (try 'foo' tomark 2 <+ 'x')
		""",
		(
			('foo', 'foo'),
			('foofoo', 'foxofoo'),
		)
	)
	assert_snowball(
		"""
		define check as backwards (tomark -2 or <+ 'x')
		""",
		(
			('o', 'ox'),
		)
	)

def test_atmark():
	assert_snowball(
		"""
		define check as (repeat 'x' atmark 3 'y')
		""",
		(
			('xxxy', 'xxxy', {'cursor':4}),
			('xxy', 'xxy', {'cursor':2}),
		)
	)

def test_tolimit():
	assert_snowball(
		"""
		define check as tolimit
		""",
		(
			('foo', 'foo', {'cursor':3}),
			('x', 'x', {'cursor':1}),
		)
	)

def test_atlimit():
	assert_snowball(
		"""
		define check as (['foo'] atlimit <- 'bar')
		""",
		(
			('foo', 'bar'),
			('fooo', 'fooo'),
		)
	)

def test_setlimit():
	assert_snowball(
		"""
		define check as (setlimit goto 'a' for (gopast 'b' <+ 'c') or 'x')
		""",
		(
			('ba', 'bca', {'limit':3}),
			('ab', 'ab', {'limit':2}),
			('x', 'x', {'cursor':1}),
		)
	)

def test_routine_call():
	assert_snowball(
		"""
		routines (r)
		define r as 'foo'
		define check as (r <+ 'x')
		""",
		(
			('foo', 'foox'),
			('bar', 'bar'),
		)
	)

def test_grouping_check():
	assert_snowball(
		"""
		groupings (g)
		define g 'f'
		define check as g
		""",
		(
			('f', 'f', {'cursor':1}),
			('g', 'g', {'cursor':0}),
		)
	)
	assert_snowball(
		"""
		groupings (g)
		define g 'f'
		define check as non-g
		""",
		(
			('f', 'f', {'cursor':0}),
			('g', 'g', {'cursor':1}),
		)
	)
	assert_snowball(
		"""
		groupings (g)
		integers (c l)
		define g 'f'
		define check as backwards (try g $c = cursor $l = limit)
		""",
		(
			('f', 'f', {}, {'i_c':0, 'i_l':0}),
			('g', 'g', {}, {'i_c':1, 'i_l':0}),
		)
	)
	assert_snowball(
		"""
		groupings (g)
		integers (c l)
		define g 'f'
		define check as backwards (try non-g $c = cursor $l = limit)
		""",
		(
			('f', 'f', {}, {'i_c':1, 'i_l':0}),
			('g', 'g', {}, {'i_c':0, 'i_l':0}),
		)
	)
	assert_snowball(
		"""
		groupings (x y z)
		define x 'a' + 'b'
		define y x + 'd' - 'b'
		define z y - x
		define check as z
		""",
		(
			('d', 'd', {'cursor':1}),
			('a', 'a', {'cursor':0}),
		)
	)
	assert_snowball(
		"""
		groupings (g)
		define g 'f'
		define check as ('x' (g or <+ 'y'))
		""",
		(
			('x', 'xy'),
			('xf', 'xf'),
		)
	)
	assert_snowball(
		"""
		groupings (g)
		define g 'f'
		define check as backwards ('x' (g or <+ 'y'))
		""",
		(
			('x', 'yx'),
			('fx', 'fx'),
		)
	)

def test_comments():
	assert_snowball(
		"""
		define /* comment */ check as ( // comment
		  /* multi-
		     line
		     comment */ 'a' // comment
		)
		""",
		(
			('a', 'a', {'cursor':1}),
			('b', 'b', {'cursor':0}),
		)
	)

def test_substring_among():
	assert_snowball(
		"""
		define check as among ('f' 'foo' 'fo')
		""",
		(
			('f', 'f', {'cursor':1}),
			('fo', 'fo', {'cursor':2}),
			('foo', 'foo', {'cursor':3}),
			('x', 'x', {'cursor':0}),
		)
	)
	assert_snowball(
		"""
		define check as (substring next among ('f' 'bo' (<+ 'x') 'b' 'fo' (<+ 'y')))
		""",
		(
			('fz', 'fzx'),
			('foz', 'fozy'),
			('bz', 'bzy'),
			('boz', 'bozx'),
		)
	)
	assert_snowball(
		"""
		define check as (
		    substring among (
		        'x' (<+ 'X')
		        'y' (
		            among (
		                'z' (<+ 'Z')
		            )
		        )
		    )
		)
		""",
		(
			('x', 'xX'),
			('y', 'y'),
			('yz', 'yzZ'),
		)
	)
	assert_snowball(
		"""
		define check as (test substring among ('x' (<+ 'y')))
		"""
		,
		(
			('x', 'yx'),
		)
	)
	assert_snowball(
		"""
		integers (c l)
		define check as backwards (try among ('f' 'foo' 'fo') $c = cursor $l = limit)
		""",
		(
			('xf', 'xf', {}, {'i_c':1, 'i_l':0}),
			('xfo', 'xfo', {}, {'i_c':1, 'i_l':0}),
			('xfoo', 'xfoo', {}, {'i_c':1, 'i_l':0}),
			('x', 'x', {}, {'i_c': 1, 'i_l':0}),
		)
	)
	assert_snowball(
		"""
		define check as backwards (substring next among ('f' 'bo' (<+ 'x') 'b' 'fo' (<+ 'y')))
		""",
		(
			('zf', 'xzf'),
			('zfo', 'yzfo'),
			('zb', 'yzb'),
			('zbo', 'xzbo'),
		)
	)
	assert_snowball(
		"""
		define check as among( (next) 'a' (<+ 'x') )
		""",
		(
			('a', 'a'),
			('ab', 'abx'),
		)
	)
	assert_snowball(
		"""
		routines (r)
		define r as 'foo'
		define check as among ('x' 'y' r (<+ 'z'))
		""",
		(
			('x', 'xz'),
			('xfoo', 'xzfoo'),
			('y', 'y'),
			('yfoo', 'yfooz'),
		)
	)

def test_int_cmds():
	assert_snowball(
		"""
		integers (i j)
		define check as (
		  $i = 1
		  $j = i
		  $i > 0
		  $j *= 2
		  $j < 3
		  $i >= 1
		  $i += 3
		  $j <= 2
		  $i /= 4
		  $i == 1
		  $j != 1
		  <+ 'x'
		)
		""",
		(
			('', 'x', {}, {'i_i':1, 'i_j':2}),
		)
	)

def test_bool_cmds():
	assert_snowball(
		"""
		booleans (i j)
		define check as (
		  set i
			unset j
			i
			not j
			<+ 'x'
		)
		""",
		(
			('', 'x'),
		)
	)


def test_stringdefs():
	assert_snowball(
		"""
		stringescapes {}
		stringdef a" hex 'E4'
		define check as '{a"}'
		""",
		(
			(u'ä', u'ä', {'cursor':1}),
			('a', 'a', {'cursor':0}),
		)
	)


#######################################################################
# TESTS USING SNOWBALL STEMMERS                                       #
#######################################################################

def check_with_files(source_filename, input_filename, output_filename, routine='stem'):
	"""
	Translate a Snowball source file and check it using test cases from files.
	"""
	with codecs.open(source_filename, 'r', 'utf8') as f:
		sbl_code = f.read()
	py_code = sbl2py.translate_string(sbl_code)
	module = module_from_code('sbl2py_test_module', py_code)
	r = getattr(module, routine)
	with codecs.open(input_filename, 'r', 'utf8') as f:
		inputs = f.read().splitlines()
	with codecs.open(output_filename, 'r', 'utf8') as f:
		expected = f.read().splitlines()
	for inp, exp in zip(inputs, expected):
		try:
			outp = r(inp)
		except Exception as e:
			print "Could not transform %s: %s" % (repr(inp), e)
			raise
		assert outp == exp, 'Wrong output for "%s": Expected "%s", got "%s".' % (inp, exp, outp)


@attr('slow')
def test_stemmers():
	filenames = glob.glob(os.path.join(_module_dir, '*.sbl'))
	for filename in filenames:
		base = os.path.splitext(filename)[0]
		test = lambda: check_with_files(filename, base + '_in.txt', base + '_out.txt')
		test.description = os.path.basename(filename)
		yield test
