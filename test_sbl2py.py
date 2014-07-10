#!/usr/bin/env python

"""
Tests for ``sbl2py``.
"""

from sbl2py.test import TestCase


class TestSbl2Py(TestCase):

	def test_startswith(self):
		self.assertSnowball(
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

	def test_or(self):
		self.assertSnowball(
			"""
			define check as ('foo' or 'Fo')
			""",
			(
				('foo', 'foo', {'cursor':3}),
				('Fo', 'Fo', {'cursor':2}),
				('bar', 'bar', {'cursor':0}),
			)
		)

	def test_and(self):
		self.assertSnowball(
			"""
			define check as ('fo' and 'foo')
			""",
			(
				('foo', 'foo', {'cursor':3}),
				('bar', 'bar', {'cursor':0}),
				('fox', 'fox', {'cursor':0}),
			)
		)

	def test_not(self):
		self.assertSnowball(
			"""
			define check as (not 'foo')
			""",
			(
				('foo', 'foo', {'cursor':3}),
				('fox', 'fox', {'cursor':0}),
			)
		)

	def test_try(self):
		self.assertSnowball(
			"""
			define check as (try 'foo' 'bar')
			""",
			(
				('foo', 'foo', {'cursor':3}),
				('bar', 'bar', {'cursor':3}),
				('foobar', 'foobar', {'cursor':6}),
			)
		)

	def test_test(self):
		self.assertSnowball(
			"""
			define check as (test 'foo' 'fo')
			""",
			(
				('foo', 'foo', {'cursor':2}),
				('fox', 'fox', {'cursor':0}),
				('bar', 'bar', {'cursor':0}),
			)
		)

	def test_fail(self):
		self.assertSnowball(
			"""
			define check as ((fail true) or 'foo')
			""",
			(
				('foo', 'foo', {'cursor':3}),
			)
		)

	def test_do(self):
		self.assertSnowball(
			"""
			define check as (do 'foo' 'fo')
			""",
			(
				('foo', 'foo', {'cursor':2}),
				('fo', 'fo', {'cursor':2}),
			)
		)

	def test_goto(self):
		self.assertSnowball(
			"""
			define check as ((goto 'x') or 'foo')
			""",
			(
				('fox', 'fox', {'cursor':2}),
				('foox', 'foox', {'cursor':3}),
				('foobar', 'foobar', {'cursor':3}),
			)
		)

	def test_gopast(self):
		self.assertSnowball(
			"""
			define check as ((gopast 'x') or 'foo')
			""",
			(
				('fox', 'fox', {'cursor':3}),
				('foox', 'foox', {'cursor':4}),
				('foobar', 'foobar', {'cursor':3}),
			)
		)

	def test_repeat(self):
		self.assertSnowball(
				"""
				define check as ((repeat 'x') or 'foo')
				""",
				(
					('xxxfoo', 'xxxfoo', {'cursor':3}),
					('xxa', 'xxa', {'cursor':2}),
					('foo', 'foo', {'cursor':0}),
				)
			)

	def test_loop(self):
		self.assertSnowball(
			"""
			define check as (loop 2 'x')
			""",
			(
				('xxy', 'xxy', {'cursor':2}),
			)
		)

	def test_atleast(self):
		self.assertSnowball(
			"""
			define check as (atleast 2 'x')
			""",
			(
				('xxy', 'xxy', {'cursor':2}),
				('xxxxy', 'xxxxy', {'cursor':4}),
			)
		)

	def test_hop(self):
		self.assertSnowball(
			"""
			define check as (hop 2 or 'f')
			""",
			(
				('foo', 'foo', {'cursor':2}),
				('f', 'f', {'cursor':1}),
			)
		)
		self.assertSnowball(
			"""
			define check as (hop -2 or 'f')
			""",
			(
				('f', 'f', {'cursor':1}),
			)
		)

	def test_next(self):
		self.assertSnowball(
			"""
			define check as next
			""",
			(
				('foo', 'foo', {'cursor':1}),
				('bar', 'bar', {'cursor':1}),
				('', '', {'cursor':0}),
			)
		)

	def test_left(self):
		self.assertSnowball(
			"""
			define check as (try 'f' [)
			""",
			(
				('f', 'f', {}, {'left':1}),
				('g', 'g', {}, {'left':0}),
			)
		)

	def test_right(self):
		self.assertSnowball(
			"""
			define check as (try 'f' ])
			""",
			(
				('f', 'f', {}, {'right':1}),
				('g', 'g', {}, {'right':0}),
			)
		)

	def test_replace_slice(self):
		self.assertSnowball(
			"""
			define check as ('f' [try 'o'] <- 'u')
			""",
			(
				('foo', 'fuo'),
				('faa', 'fuaa'),
			)
		)

	def test_move_slice(self):
		self.assertSnowball(
			"""
			strings (s)
			define check as (['foo'] -> s ['bar'] <- s)
			""",
			(
				('foobar', 'foofoo'),
			)
		)
		self.assertSnowball(
			"""
			define check as (['foo'] <- 'bar')
			""",
			(
				('foobar', 'barbar'),
			)
		)

	def test_delete(self):
		self.assertSnowball(
			"""
			define check as (['foo'] delete)
			""",
			(
				('foo', ''),
				('foobar', 'bar'),
			)
		)

	def test_insert(self):
		self.assertSnowball(
			"""
			define check as (['foo'] insert 'bar')
			""",
			(
				('fooqux', 'foobarqux', {'cursor':6}),
			)
		)
		self.assertSnowball(
			"""
			define check as (['foo'] <+ 'bar')
			""",
			(
				('fooqux', 'foobarqux', {'cursor':6}),
			)
		)
		self.assertSnowball(
			"""
			strings (s)
			define check as (['foo'] -> s insert s)
			""",
			(
				('foo', 'foofoo', {'cursor':6}),
			)
		)
		self.assertSnowball(
			"""
			strings (s)
			define check as (['foo'] -> s <+ s)
			""",
			(
				('foo', 'foofoo', {'cursor':6}),
			)
		)

	def test_attach(self):
		self.assertSnowball(
			"""
			define check as (['foo'] attach 'bar')
			""",
			(
				('fooqux', 'foobarqux', {'cursor':3}),
			)
		)

	def test_setmark(self):
		self.assertSnowball(
			"""
			integers (i)
			define check as (try 'foo' setmark i)
			""",
			(
				('foo', 'foo', {}, {'i_i':3}),
				('bar', 'bar', {}, {'i_i':0}),
			)
		)

	def test_tomark(self):
		self.assertSnowball(
			"""
			define check as (tomark 2 or 'x')
			""",
			(
				('xo', 'xo', {'cursor':2}),
				('x', 'x', {'cursor':1}),
			)
		)
		self.assertSnowball(
			"""
			define check as (tomark -2 or 'x')
			""",
			(
				('o', 'o', {'cursor':0}),
				('x', 'x', {'cursor':1}),
			)
		)

	def test_atmark(self):
		self.assertSnowball(
			"""
			define check as (repeat 'x' atmark 3 'y')
			""",
			(
				('xxxy', 'xxxy', {'cursor':4}),
				('xxy', 'xxy', {'cursor':2}),
			)
		)

	def test_tolimit(self):
		self.assertSnowball(
			"""
			define check as tolimit
			""",
			(
				('foo', 'foo', {'cursor':3}),
				('x', 'x', {'cursor':1}),
			)
		)

	def test_atlimit(self):
		self.assertSnowball(
			"""
			define check as (['foo'] atlimit <- 'bar')
			""",
			(
				('foo', 'bar'),
				('fooo', 'fooo'),
			)
		)

	def test_setlimit(self):
		self.assertSnowball(
			"""
			define check as (setlimit goto 'a' for (gopast 'b' <+ 'c') or 'x')
			""",
			(
				('ba', 'bca', {'limit':3}),
				('ab', 'ab', {'limit':2}),
				('x', 'x', {'cursor':1}),
			)
		)


	def test_routine_call(self):
		self.assertSnowball(
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


if __name__ == '__main__':
	import unittest
	unittest.main()
