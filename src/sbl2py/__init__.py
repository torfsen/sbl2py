#!/usr/bin/env python

"""
A Snowball to Python compiler.
"""

import sbl2py.ast
import sbl2py.grammar


def translate_file(infile, *args, **kwargs):
	"""
	Translate a Snowball file to Python.

	``infile`` is an open readable file containing the Snowball source code. The
	return value is a string containing the translated Python code.

	See ``translate_string`` for additional arguments.
	"""
	return translate_string(infile.read(), *args, **kwargs)


def translate_string(code, debug=False):
	"""
	Translate a Snowball code string to Python.

	If ``debug`` is ``True`` then the external Snowball routines return both
	the original ``_String`` object and the ``_Program`` instance that created
	it. This is useful for checking that variables have been computed correctly.
	"""
	node = sbl2py.grammar.parse_string(code)
	env = sbl2py.ast.Environment(debug=debug)
	return node.generate_code(env)

