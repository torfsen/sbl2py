#!/usr/bin/env python

"""
Tests for ``sbl2py``.
"""

from sbl2py.test import TestCase


class TestSbl2Py(TestCase):

	def test_startswith(self):
		self.assertSnowball(
			"""
			define check as ('foo')
			""",
			(
				('foo', 'foo', {'cursor':3}),
				('f', 'f', {'cursor':0}),
				('fo', 'fo', {'cursor':0}),
				('bar', 'bar', {'cursor':0}),
				('xfoo', 'xfoo', {'cursor':0}),
				('Foo', 'Foo', {'cursor':0}),
				('fooo', 'fooo', {'cursor':3}),
			)
		)


if __name__ == '__main__':
	import unittest
	unittest.main()
