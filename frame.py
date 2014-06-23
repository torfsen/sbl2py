
__all__ = ['stem']


class String(object):

	def __init__(self, s):
		self.chars = list(s) # Lists are mutable, strings are not
		self.cursor = 0
		self.limit = len(s)

	def __len__(self):
		return len(self.chars)

	def set(self, chars):
		self.chars[self.cursor:self.limit] = value
		self.limit = self.cursor + len(value)
		return True

	def startswith(self, chars):
		limit = self.cursor + len(chars)
		if limit > self.limit:
			return False
		if self.chars[self.cursor:limit] == chars:
			self.cursor = limit
			return True
		return False

	def hop(self, value):
		if value < 0 or self.limit - self.cursor < value:
			return False
		self.cursor += value
		return True

	def next(self):
		return self.hop(1)

	def tomark(self, value):
		if self.cursor > value or self.limit < value:
			return False
		self.cursor = value
		return True

	def atmark(self, value):
		return self.cursor == value

	def tolimit(self):
		self.cursor = self.limit
		return True

	def atlimit(self):
		return self.cursor == self.limit


class Context(object):
	def __init__(self, s):
		self.string = String(s)
		self.integers = {}
		self.booleans = {}
		self.groupings = {}
		self.strings = {}

	# In Python, assignments are statements. To use them inside expressions
	# we need to wrap them in functions

	def _int_assign(self, name, value):
		self.integers[name] = value
		return True

	def _int_add_assign(self, name, value):
		self.integers[name] += value
		return True

	def _int_mult_assign(self, name, value):
		self.integers[name] *= value
		return True

	def _int_sub_assign(self, name, value):
		self.integers[name] -= value
		return True

	def _int_div_assign(self, name, value):
		self.integers[name] /= value
		return True


	#
	# Begin of dynamically created code
	#

	def prelude(self):
		pass

	def postlude(self):
		pass

	def mark_regions(self):
		pass

	def R1(self):
		pass

	def R2(self):
		pass

	def standard_suffix(self):
		pass

	def stem(self):
		pass


	#
	# End of dynamically created code
	#


#
# Begin of dynamically created code
#

def stem(s):
	c = Context(s)
	c.stem()
	return c.string

#
# End of dynamically created code
#
