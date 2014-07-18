#!/usr/bin/env python

"""
Tests for ``sbl2py``.
"""

from sbl2py.test import TestCase


class TestSbl2Py(TestCase):

	def test_starts_with(self):
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
		self.assertSnowball(
			"""
			define check as backwards ('bar' 'foo' <+ 'x')
			""",
			(
				('foobar', 'xfoobar'),
				('barbar', 'barbar'),
			)
		)

	def test_or(self):
		self.assertSnowball(
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

	def test_and(self):
		self.assertSnowball(
			"""
			define check as ('f' and 'fo' and 'foo')
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
		self.assertSnowball(
			"""
			define check as backwards ((goto 'x') or 'foo' <+ 'y')
			""",
			(
				('xofoo', 'xyofoo'),
				('ofoo', 'oyfoo'),
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
		self.assertSnowball(
			"""
			define check as backwards ((gopast 'x') or 'foo' <+ 'y')
			""",
			(
				('xofoo', 'yxofoo'),
				('ofoo', 'oyfoo'),
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
		self.assertSnowball(
			"""
			define check as backwards (hop 2 <+ 'x')
			""",
			(
				('foo', 'fxoo'),
				('f', 'f'),
			)
		)
		self.assertSnowball(
			"""
			define check as backwards (hop -2 <+ 'x')
			""",
			(
				('f', 'f'),
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
		self.assertSnowball(
			"""
			define check as backwards (next <+ 'x')
			""",
			(
				('foo', 'foxo'),
				('bar', 'baxr'),
				('', ''),
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
				('foo', 'fuo', {'cursor':2, 'limit':3}),
				('faa', 'fuaa', {'cursor':2, 'limit':4}),
			)
		)
		self.assertSnowball(
			"""
			define check as backwards ('f' [try 'alo'] <- 'xyz')
			""",
			(
				('galof', 'gxyzf'),
				('gf', 'gxyzf'),
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
			strings (s)
			define check as backwards (['foo'] -> s ['bar'] <- s)
			""",
			(
				('barfoo', 'foofoo'),
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
			define check as ('foo' insert 'bar')
			""",
			(
				('fooqux', 'foobarqux', {'cursor':6, 'limit':9}),
			)
		)
		self.assertSnowball(
			"""
			define check as ('foo' <+ 'bar')
			""",
			(
				('fooqux', 'foobarqux', {'cursor':6, 'limit':9}),
			)
		)
		self.assertSnowball(
			"""
			strings (s)
			define check as (['foo'] -> s insert s)
			""",
			(
				('foo', 'foofoo', {'cursor':6, 'limit':6}),
			)
		)
		self.assertSnowball(
			"""
			strings (s)
			define check as (['foo'] -> s <+ s)
			""",
			(
				('foo', 'foofoo', {'cursor':6, 'limit':6}),
			)
		)
		self.assertSnowball(
			"""
			integers (c l)
			define check as backwards ('foo' insert 'bar' $c = cursor $l = limit)
			""",
			(
				('quxfoo', 'quxbarfoo', {}, {'i_c':3, 'i_l':0}),
			)
		)
		self.assertSnowball(
			"""
			integers (c l)
			define check as backwards ('foo' <+ 'bar' $c = cursor $l = limit)
			""",
			(
				('quxfoo', 'quxbarfoo', {}, {'i_c':3, 'i_l':0}),
			)
		)
		self.assertSnowball(
			"""
			strings (s)
			integers (c l)
			define check as backwards (['foo'] -> s insert s $c = cursor $l = limit)
			""",
			(
				('foo', 'foofoo', {}, {'i_c':0, 'i_l':0}),
			)
		)
		self.assertSnowball(
			"""
			strings (s)
			integers (c l)
			define check as backwards (['foo'] -> s <+ s $c = cursor $l = limit)
			""",
			(
				('foo', 'foofoo', {}, {'i_c':0, 'i_l':0}),
			)
		)

	def test_attach(self):
		self.assertSnowball(
			"""
			define check as ('foo' attach 'bar')
			""",
			(
				('fooqux', 'foobarqux', {'cursor':3, 'limit':9}),
			)
		)
		self.assertSnowball(
			"""
			integers (c l)
			define check as backwards ('foo' attach 'bar' $c = cursor $l = limit)
			""",
			(
				('foo', 'barfoo', {}, {'i_c':3, 'i_l':0}),
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
		self.assertSnowball(
			"""
			define check as backwards (try 'foo' tomark 2 <+ 'x')
			""",
			(
				('foo', 'foo'),
				('foofoo', 'foxofoo'),
			)
		)
		self.assertSnowball(
			"""
			define check as backwards (tomark -2 or <+ 'x')
			""",
			(
				('o', 'ox'),
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

	def test_grouping_check(self):
		self.assertSnowball(
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
		self.assertSnowball(
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
		self.assertSnowball(
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
		self.assertSnowball(
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

	def test_comments(self):
		self.assertSnowball(
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

	def test_substring_among(self):
		self.assertSnowball(
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
		self.assertSnowball(
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

	def test_int_cmds(self):
		self.assertSnowball(
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

	def test_bool_cmds(self):
		self.assertSnowball(
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


if __name__ == '__main__':
	import unittest
	unittest.main()
