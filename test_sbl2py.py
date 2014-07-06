#!/usr/bin/env python

"""
Tests for ``sbl2py``.
"""

from sbl2py.test import TestCase


class TestSbl2Py(TestCase):

	def test(self):
		self.assertSnowball(
			"""
			booleans (b)
			define check as (set b)
			""",
			'check',
			'foo', 'foo',
			'bar', 'bar'
		)


if __name__ == '__main__':
	import unittest
	unittest.main()
