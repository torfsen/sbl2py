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


def _deinterlace(seq):
	"""
	Deinterlace a sequence into two sequences.
	"""
	return seq[::2], seq[1::2]


class TestCase(unittest.TestCase):

	# Note: Violates PEP8 to comply with ``unittest.TestCase`` style.

	def assertSnowball(self, code, routine, *args):
		"""
		``code`` is automatically prefixed with an externals declaration for the
		given routine name.
		"""
		if not args:
			return
		if len(args) % 2 != 0:
			raise ValueError('Numbers of inputs and expected outputs must match.')
		code = ("externals (%s)\n" % routine) + code
		pycode = sbl2py.translate_code(code)
		module = _module_from_code('sbl2py_testmodule', pycode)
		fun = getattr(module, routine)
		inputs, expected = _deinterlace(args)
		for i, e in zip(inputs, expected):
			o = fun(i)
			self.assertEqual(o, e, "Wrong output for '%s': Expected '%s', got '%s'."
					% (i, e, o))


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
	inputs, expected = _deinterlace(sys.argv[3:])

	test_file(filename, routine, zip(inputs, expected))
