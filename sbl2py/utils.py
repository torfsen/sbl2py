#!/usr/bin/env python

"""
Various utilities.
"""


def remove_empty_lines(s):
	"""
	Remove empty lines from a string.
	"""
	return '\n'.join(line for line in s.split('\n') if line)


def prefix_lines(s, p):
	"""
	Prefix each line of ``s`` by ``p``.
	"""
	try:
		return p + ('\n' + p).join(s.split('\n'))
	except Exception as e:
		import traceback
		traceback.print_exc()
		import pdb; pdb.set_trace()
		raise


def extract(seq, f):
	"""
	Extract items from a possibly nested sequence.

	All items of the possibly nested sequence ``seq`` for which the callback
	``f`` returns ``True`` are returned in a list.
	"""
	try:
		it = iter(seq)
	except TypeError:
		return []
	items = []
	for item in it:
		if f(item):
			items.append(item)
		else:
			items.extend(extract(item, f))
	return items


def extract_strings(seq):
	"""
	Extract all strings from a possibly nested sequence.
	"""
	return extract(seq, lambda x: isinstance(x, basestring))
