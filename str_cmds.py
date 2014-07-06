#!/usr/bin/env python

# String commands have the additional difficulty that they contain a shared
# state: The string they are operating on, including its cursor and limit.
# Changing that state can not happen in raw expressions and must be wrapped
# in functions.


class String(object):

	def __init__(self, s):
		self.chars = list(s)
		self.cursor = 0
		self.limit = len(s)

	def assign(self, value):
		self.chars[self.cursor:self.limit] = value
		self.limit = self.cursor + len(value)
		return True

	def insert(self, value):
		self.attach(value)
		self.cursor += len(value)
		self.limit += len(value)
		return True

	def attach(self, value):
		self.chars[self.cursor:self.cursor] = value
		return True

	def set_chars(self, value):
		self.chars = value[:]
		self.cursor = 0
		self.limit = len(value)
		return True

	def get_range(self, start=None, end=None):
		if start is None:
			start = self.cursor
		if end is None:
			end = self.limit
		return self.chars[start:end]

	def set_range(self, values, start, end):
		"""
		Set the given sub-range.

		The sub-range must be to the left of the cursor.
		"""
		if start > end or end > self.cursor:
			raise ValueError('Invalid range.')
		self.chars[start:end] = values
		change = len(values) - (end - start)
		self.cursor += change
		self.limit += change
		return True

	def startswith(self, value):
		if self.limit - self.cursor < len(value):
			return False
		value = list(value)
		if self.chars[self.cursor:self.cursor + len(value)] == value:
			self.cursor = self.cursor + len(value)
			return True
		return False

	def hop(self, n):
		if self.limit - self.cursor < n:
			return False
		self.cursor += n
		return True

	def tomark(self, i):
		if self.cursor > i or self.limit < i:
			return False
		self.cursor = i
		return True

	def tolimit(self):
		self.cursor = self.limit
		return True


r = True      # Result of last command
left = None   # Left end of slice
right = None  # Right end of slice

# At the beginning of a string command ("$x ...") store the target string object
# in a local variable to minimize lookups: ``x = self.s_x

# In what follows, variables of the form ``v...`` are dynamic variables, i.e.
# their names are chosen dynamically and uniquely during compile time to avoid
# name clashes.

#
# Setting a value
#

# $x = S
r = x.assign(S)

#
# Basic tests
#

# $x S
r = x.startswith(S)

# $x (C1 C2)
C1
if r:
	C2

# $x C1 or C2
v = x.cursor
C1
if not r:
	x.cursor = v
	C2

# $x C1 and C2
v = x.cursor
C1
if r:
	x.cursor = v
	C2

# $x not C
v = x.cursor
C
if not r:
	x.cursor = v
r = not r

# $x try C
v = x.cursor
C
if not r:
	r = True
	x.cursor = v

# $x test C
v = x.cursor
C
x.cursor = v

# $x fail C
C
r = False

# $x do C
v = x.cursor
C
x.cursor = v
r = True

# $x goto C
while True:
	v = x.cursor
	C
	if r or x.cursor == x.limit:
		x.cursor = v
		break
	x.cursor += 1

# $x gopast C
while True:
	C
	if r or x.cursor == x.limit:
		break
	x.cursor += 1

# $x repeat C
while True:
	v = x.cursor
	C
	if not r:
		x.cursor = v
		r = True
		break

# $x loop AE C
for v in range(AE):
	C

# $x atleast AE C
for v in range(AE):
	C
while True:
	v = x.cursor
	C
	if not r:
		x.cursor = v
		r = True
		break

# $x hop AE
r = x.hop(AE)

# $x next
r = x.hop(1)

#
# Moving text about
#

# $x => y
self.s_y.set_chars(x.get_range())
r = True

# $x [
left = x.cursor  # Does not modify ``r``

# $x ]
right = x.cursor  # Does not modify ``r``

# $x -> y
r = self.s_y.set_chars(x.get_range(left, right))

# $x <- S
r = x.set_range(S, left, right)

# $x delete
r = x.set_range('', left, right)

# $x insert S
r = x.insert(S)

# $x attach S
r = x.attach(S)

#
# Marks
#

# $x setmark j
self.i_j = x.cursor
r = True

# $x tomark AE
r = x.tomark(AE)

# $x atmark AE
r = (x.cursor == AE)

# $x tolimit
r = x.tolimit()

# $x atlimit
r = (x.cursor == x.limit)

#
# Changing ``l``
#

# $x setlimit C1 for C2
v1 = x.cursor
v2 = x.limit
C1
if r:
	x.limit = x.cursor
	x.cursor = v1
	C2
	x.limit = v2

#
# TODO: Backward processing
#

# $x backwards C


# $x reverse C

#
# ``substring`` and ``among``
#

# Although the documentation mentions quite a few shortcuts and special
# features of ``substring``/``among``, the only form that actually seems to be
# used in the code is
#
#  substring
#    ...
#    among( 'S11' 'S12' ... (C1)
#           'S21' 'S22' ... (C2)
#           ...
#
#           'Sn1' 'Sn2' ... (Cn)
#         )
#
# with (Cn) sometimes being left out (defaults to ``true``). ``substring`` is
# also sometimes left out, in which case it defaults to being executed right
# before among. The form without any (Ci) is also used several times, in which
# case the ``among`` part simply does nothing (assuming the actual matching is
# done in ``substring``).

# `substring` is equivalent to

r = False
for v1, v2 in (
	(Sij, i),  # Sorted descendingly by length.
	(Skl, k),
	...
):
	if x.startswith(v1):
		substring_var = v2
		r = True
		break

# and the corresponding among then becomes

if substring_var == 1:
	C1
elif substring_var == 2:
	C2
...

# Since substring/among pairs must match inside the code there is no need to
# maintain different variants of `substring_var`.

#
# Booleans
#

# $x set a
self.b_a = True
r = True

# $x unset a
self.b_a = False
r = True

# $x a
r = self.b_a

#
# Groupings
#

# $x h
if x.cursor == x.limit:
	r = False
else:
	r = x.chars[x.cursor] in self.g_h
	if r:
		x.cursor += 1

# $x non h
if x.cursor == x.limit:
	r = False
else:
	r = x.chars[x.cursor] not in self.g_h
	if r:
		x.cursor += 1