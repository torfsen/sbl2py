#!/usr/bin/env python

"""
Module and script for testing sbl2py.
"""

import imp
import os
import tempfile
import traceback

import sbl2py


def test(filename, routine, tests):
	"""
	Translate a Snowball file to Python and test the result.
	"""
	with open(filename, 'r') as f:
		code = sbl2py.translate_file(f)

	module_file = tempfile.NamedTemporaryFile(mode='w', suffix='.py',
			delete=False)
	try:
		module_file.write(code)
		module_file.close()
		#print "Code is in", module_file.name
		module = imp.load_source('sbl2py_testmodule', module_file.name)
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

	except:
		traceback.print_exc()
		print ""
		print "An error ocurred, not deleting module", module_file.name
	else:
		os.unlink(module_file.name)


if __name__ == '__main__':

	import sys

	if len(sys.argv) < 5 or len(sys.argv) % 2 != 1:
		sys.stderr.write('Syntax: %s FILENAME ROUTINE INPUT1 OUTPUT1 [INPUT2 OUTPUT2 ...]\n')
		sys.exit(1)

	filename = sys.argv[1]
	routine = sys.argv[2]
	inputs = sys.argv[3::2]
	expected = sys.argv[4::2]

	test(filename, routine, zip(inputs, expected))

	
