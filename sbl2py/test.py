#!/usr/bin/env python

"""
Module and script for testing sbl2py.
"""

import imp
import os
import tempfile
import traceback
import unittest

import sbl2py


class TestCase(unittest.TestCase):

	# Note: Violates PEP8 to comply with ``unittest.TestCase`` style.

	def assertSnowball(self, code, tests, routine='check'):
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
		pycode = sbl2py.translate_string(code, testing=True)

		def msg(s):
			return s + "\n\nSnowball code:\n\n" + code + "\n\nPython code:\n\n" + pycode

		try:
			module = _module_from_code('sbl2py_testmodule', pycode)
		except SyntaxError as e:
			print msg("Generated code is invalid: %s" % e)
			raise

		fun = getattr(module, routine)

		for test in tests:
			string = test[0]
			expected = test[1]
			s_attrs = test[2] if len(test) > 2 else {}
			p_attrs = test[3] if len(test) > 3 else {}

			output, program = fun(string)
			self.assertEqual(str(output), expected, msg(
					"Wrong output for '%s': Expected '%s', got '%s'." % (string, expected,
					output)))
			for attr, exp_value in s_attrs.iteritems():
				value = getattr(output, attr)
				self.assertEqual(value, exp_value, msg(
						"Wrong value for string attribute '%s': Expected '%s', got '%s'." %
						(attr, exp_value, value)))
			for attr, exp_value in p_attrs.iteritems():
				value = getattr(program, attr)
				self.assertEqual(value, exp_value, msg(
						"Wrong value for program attribute '%s': Expected '%s', got '%s'." %
						(attr, exp_value, value)))


def _module_from_code(name, code):
	"""
	Dynamically create Python module from code string.
	"""
	module = imp.new_module(name)
	exec code in module.__dict__
	return module


def test_file(filename, routine, tests):
	"""
	Translate a Snowball file to Python and test the result.

	``filename`` is the name of the Snowball source file. ``routine`` is the
	name of the Snowball routine to test. ``tests`` is a list of tuples, where
	each tuple consists of the input word and the expected output.
	"""
	with open(filename, 'r') as f:
		code = sbl2py.translate_file(f)

	module_file = tempfile.NamedTemporaryFile(mode='w', suffix='.py',
			delete=False)
	try:
		module_file.write(code)
		module_file.close()
		module = imp.load_source('sbl2py_testmodule', module_file.name)
		test_module(module, routine, tests)
	except:
		traceback.print_exc()
		print ""
		print "An error ocurred, not deleting module", module_file.name
	else:
		os.unlink(module_file.name)


def test_code(code, routine, tests):
	"""
	Translate a Snowball code string to Python and test the result.

	``code`` is a string of Snowball source code. ``routine`` is the name of the
	Snowball routine to test. ``tests`` is a list of tuples, where each tuple
	consists of the input word and the expected output.
	"""
	pycode = sbl2py.translate_code(code)
	module = _module_from_code('sbl2py_testmodule', pycode)
	test_module(module, routine, tests)


def test_module(module, routine, tests):
	"""
	Test a generated Python module.

	``module`` is a Python module generated from Snowball code. ``routine`` is
	the name of the Snowball routine to test. ``tests`` is a list of tuples,
	where each tuple consists of the input word and the expected output.
	"""
	function = getattr(module, routine)
	passed = 0
	failed = 0
	for case, expected in tests:
		result = function(case)
		if result == expected:
			passed += 1
		else:
			failed += 1
			print "'%s': Expected '%s', got '%s'." % (case, expected, result)
	print ""
	print "%d passed, %d failed." % (passed, failed)


if __name__ == '__main__':

	import sys

	if len(sys.argv) < 5 or len(sys.argv) % 2 != 1:
		sys.stderr.write('Syntax: %s FILENAME ROUTINE INPUT1 OUTPUT1 [INPUT2 OUTPUT2 ...]\n' % sys.argv[0])
		sys.exit(1)

	filename = sys.argv[1]
	routine = sys.argv[2]
	inputs = sys.argv[3::2]
	expected = sys.argv[4::2]

	test_file(filename, routine, zip(inputs, expected))
